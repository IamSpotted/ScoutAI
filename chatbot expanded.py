import os
import json
import warnings
import random
import shutil
import asyncio
import logging
import validators
import aiofiles
import aiohttp
import shlex
import secrets
import time
import tempfile
import pkg_resources
from tqdm import tqdm  # Progress bar library
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from urllib.parse import urlparse, urljoin
from get_embedding_function import get_embedding_function
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm as async_tqdm
from pathlib import Path

from sqlalchemy import create_engine, bindparam
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
from logging_models import PdfDownloadLog, CompletedPagesLog, Base

# Custom exception classes
class SecurityError(Exception):
    pass

class NetworkError(Exception):
    pass

class AuthorizationError(Exception):
    pass

class RateLimitError(Exception):
    pass

# Ignore Warnings
warnings.filterwarnings("ignore")

# Global Variables
qa_chain = None
memory = None

# Configure logging with secure settings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='security.log'
)

# Suppress sensitive logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Safe counter for concurrency
class SafeCounter:
    def __init__(self, initial=0):
        self.count = initial
        self.lock = asyncio.Lock()
    
    async def increment(self):
        async with self.lock:
            self.count += 1
            return self.count
    
    async def get(self):
        async with self.lock:
            return self.count
    
    async def remaining(self, max_value):
        async with self.lock:
            return max(0, max_value - self.count)

# Rate limiter implementation
class RateLimiter:
    def __init__(self, rate, per_second):
        self.tokens = rate
        self.rate = rate
        self.per_second = per_second
        self.last_check = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_check
            self.last_check = now
            self.tokens += elapsed * (self.rate / self.per_second)
            self.tokens = min(self.tokens, self.rate)
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * (self.per_second / self.rate)
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1

def verify_dependencies():
    """Verify that installed dependencies match required versions."""
    required = {
        'aiohttp': '>=3.8.0',
        'playwright': '>=1.20.0',
        'langchain': '>=0.0.200',
        'validators': '>=0.20.0',
        'tqdm': '>=4.60.0',
        'sqlalchemy': '>=1.4.0',
        'aiofiles': '>=0.8.0',
    }
    
    try:
        for package, version in required.items():
            pkg_resources.require(f"{package}{version}")
    except pkg_resources.VersionConflict as e:
        logging.error(f"Dependency version mismatch: {e}")
        raise SecurityError(f"Invalid dependency version: {e}")

def load_config(file_path):
    """Load configuration from a JSON file or create one if it does not exist."""
    default_config = {
        "database_paths": {}  # Define any default values here
    }
    
    try:
        if not os.path.isfile(file_path):
            # If the file does not exist, create it with the default config
            print(f"Configuration file '{file_path}' not found. Creating a new one with default settings.")
            save_config(file_path, default_config)
            return default_config
        
        with open(file_path, 'r') as file:
            config = json.load(file)
        return config
    except FileNotFoundError:
        print(f"Error: The configuration file '{file_path}' was not found.")
        # Create a new config file if not found
        print(f"Creating a new configuration file '{file_path}' with default settings.")
        save_config(file_path, default_config)
        return default_config
    except json.JSONDecodeError:
        logging.error("Configuration file is not a valid JSON.")
        print("Error: Configuration file is not a valid JSON.")
        return default_config
    except Exception as e:
        logging.error(f"Error loading configuration: {type(e).__name__}")
        print(f"Error loading configuration. Using default settings.")
        return default_config

def save_config(file_path, config):
    """Save configuration to a JSON file securely."""
    # Create a secure temporary file
    temp_file = create_secure_temp_file()
    
    try:
        with open(temp_file.name, 'w') as file:
            json.dump(config, file, indent=4)
        
        # Move the temporary file to the destination (atomic operation)
        os.replace(temp_file.name, file_path)
    except Exception as e:
        logging.error(f"Error saving configuration: {type(e).__name__}")
        secure_delete_file(temp_file.name)
        raise

def create_secure_temp_file():
    """Create a secure temporary file with proper permissions."""
    return tempfile.NamedTemporaryFile(mode='w+', delete=False)

def secure_delete_file(file_path):
    """Securely delete a file by overwriting its contents before removal."""
    try:
        if os.path.exists(file_path):
            # Overwrite with random data before deletion
            file_size = os.path.getsize(file_path)
            with open(file_path, 'wb') as f:
                f.write(secrets.token_bytes(file_size))
            os.remove(file_path)
    except Exception as e:
        logging.error(f"Error securely deleting file {file_path}: {type(e).__name__}")

def sanitize_path(user_input: str, base_dir: str = None) -> str:
    """Sanitize user-provided paths to prevent path traversal attacks."""
    if not user_input:
        raise ValueError("Path cannot be empty")
        
    if base_dir is None:
        base_dir = os.getenv("SAFE_BASE_DIR", os.path.expanduser("~"))
    
    # Normalize paths
    base_path = Path(os.path.abspath(os.path.expanduser(base_dir)))
    
    # Handle relative paths
    if not os.path.isabs(user_input):
        user_path = base_path / user_input
    else:
        user_path = Path(os.path.abspath(os.path.expanduser(user_input)))
    
    # Verify the path is within the base directory
    try:
        user_path.relative_to(base_path)
    except ValueError:
        logging.warning(f"Path traversal attempt blocked: '{user_path}'")
        raise SecurityError(f"Path traversal blocked: '{user_path}'")
    
    # Check for symlinks in the path
    path_parts = user_path.relative_to(base_path).parts
    current = base_path
    for part in path_parts:
        current = current / part
        if current.is_symlink():
            logging.warning(f"Symbolic link detected and blocked: {current}")
            raise SecurityError(f"Symbolic links are not allowed: {current}")
    
    return str(user_path)

def get_safe_path(user_input, base_dir=None):
    """Wrapper for sanitize_path to ensure consistent usage."""
    return sanitize_path(user_input, base_dir)

def validate_positive_int(value, name):
    """Validate that a value is a positive integer."""
    try:
        int_value = int(value)
        if int_value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return int_value
    except ValueError:
        raise ValueError(f"{name} must be a valid integer")

def validate_positive_float(value, name):
    """Validate that a value is a positive float."""
    try:
        float_value = float(value)
        if float_value <= 0:
            raise ValueError(f"{name} must be a positive number")
        return float_value
    except ValueError:
        raise ValueError(f"{name} must be a valid number")

def validate_url(url: str, allowed_domains: list = None, require_https: bool = True) -> str:
    """Validate URL with enhanced security checks."""
    # Basic validation
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    # Use validators library for basic URL validation
    if not validators.url(url):
        raise ValueError("Invalid URL format")
    
    parsed = urlparse(url)
    
    # HTTPS validation
    if require_https and parsed.scheme != "https":
        raise SecurityError("HTTPS is required for security")
    
    # Domain validation
    if allowed_domains and parsed.netloc not in allowed_domains:
        logging.warning(f"Attempt to access non-allowed domain: {parsed.netloc}")
        raise SecurityError(f"Domain not allowed: {parsed.netloc}")
    
    # Avoid certain URL patterns
    if any(c in url for c in ['<', '>', '"', "'", '`', ';']):
        raise SecurityError("URL contains potentially dangerous characters")
    
    return url

def handle_interrupt():
    """Handle keyboard interrupt with confirmation."""
    print("\nKeyboardInterrupt detected. Are you sure you want to exit? (y/n)")
    try:
        confirm = input().strip().lower()
        return confirm in ["y", "yes"]
    except Exception:
        return True  # Default to exit on any error

def select_database(database_paths):
    """Prompt user to select a database."""
    while True:
        try:
            # Display database options
            print("Please select a database (enter numbers separated by commas):")
            for key, info in database_paths.items():
                print(f"{key}: {info['name']}")

            print("0: Back to main menu")

            db_choice = input("Enter your selection: ")

            if db_choice == "0":
                print("Returning to main menu...")
                return None

            selected_ids = db_choice.split(',')
            valid_selection = True
            databases_selected = []

            for db_id in selected_ids:
                db_id = db_id.strip()
                if db_id in database_paths:
                    # Sanitize the path before adding
                    safe_path = get_safe_path(database_paths[db_id]["path"])
                    databases_selected.append(safe_path)
                else:
                    print(f"Invalid Selection '{db_id}'.")
                    valid_selection = False

            if valid_selection and databases_selected:
                return databases_selected
            else:
                print("Please make a valid selection.")
        
        except SecurityError as e:
            logging.error(f"Security error in database selection: {e}")
            print(f"Security error: {e}")
        except KeyboardInterrupt:
            if handle_interrupt():
                exit()
        except Exception as e:
            logging.error(f"Error in database selection: {type(e).__name__}")
            print("An error occurred. Please try again.")

def initialize_vector_stores(paths):
    """Initialize ChromaDB instances securely."""
    vector_stores = []
    for path in paths:
        try:
            # Validate path again for extra security
            safe_path = get_safe_path(path)
            vector_stores.append(Chroma(
                persist_directory=safe_path,
                embedding_function=get_embedding_function()
            ))
        except Exception as e:
            logging.error(f"Error initializing vector store: {type(e).__name__}")
            print(f"Error initializing database at {path}. Skipping.")
    return vector_stores

def load_documents(directory_path):
    """Load documents from the specified directory securely."""
    try:
        # Sanitize the directory path
        safe_dir = get_safe_path(directory_path)
        
        # Check if directory exists
        if not os.path.isdir(safe_dir):
            raise ValueError(f"Directory does not exist: {safe_dir}")
        
        # Initialize the document loader
        loader = PyPDFDirectoryLoader(safe_dir)
        
        # Load documents
        documents = loader.load()
        
        return documents
    except SecurityError as e:
        logging.error(f"Security error loading documents: {e}")
        raise
    except Exception as e:
        logging.error(f"Error loading documents: {type(e).__name__}")
        raise ValueError(f"Error loading documents: {e}")

def ensure_directory_exists(path):
    """Create directory if it does not exist, with security checks."""
    try:
        # Sanitize the path
        safe_path = get_safe_path(path)
        
        if not os.path.exists(safe_path):
            os.makedirs(safe_path, mode=0o750)  # More restrictive permissions
        
        return safe_path
    except SecurityError as e:
        logging.error(f"Security error ensuring directory: {e}")
        raise
    except Exception as e:
        logging.error(f"Error ensuring directory: {type(e).__name__}")
        raise ValueError(f"Error creating directory: {e}")

def split_documents(documents, chunk_size, chunk_overlap):
    """Split documents into chunks securely."""
    try:
        # Validate parameters
        chunk_size = validate_positive_int(chunk_size, "Chunk size")
        chunk_overlap = validate_positive_int(chunk_overlap, "Chunk overlap")
        
        # Initialize text splitter with specified chunk size and overlap
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        split_docs = []
        for doc in documents:
            split_docs.extend(text_splitter.split_documents([doc]))
        
        return split_docs
    except ValueError as e:
        logging.error(f"Validation error in document splitting: {e}")
        raise
    except Exception as e:
        logging.error(f"Error splitting documents: {type(e).__name__}")
        raise ValueError(f"Error processing documents: {e}")

def reprocess_and_update(chunks, db_path, chunk_size, chunk_overlap):
    """Reprocess documents and update the database securely."""
    try:
        # Sanitize the database path
        safe_db_path = get_safe_path(db_path)
        
        # Initialize ChromaDB instance for the database
        vector_store = Chroma(
            persist_directory=safe_db_path,
            embedding_function=get_embedding_function()
        )

        # Add new chunks to the vector store
        print("Adding new documents to the database...")
        with tqdm(total=len(chunks), desc="Progress (Adding Documents)", unit="chunk") as pbar:
            vector_store.add_documents(chunks)
            pbar.update(len(chunks))

        # Save the updated vector store
        print("Saving the updated database...")
        vector_store.persist()

        print(f"Database at '{safe_db_path}' has been updated successfully.")
    except SecurityError as e:
        logging.error(f"Security error updating database: {e}")
        raise
    except Exception as e:
        logging.error(f"Error updating database: {type(e).__name__}")
        raise ValueError(f"Error updating database: {e}")

def authenticate_user(username, password_hash):
    """Simple authentication mechanism - this should be expanded."""
    # This is a placeholder for a proper authentication system
    # In a real system, you would verify against a secure database
    if not username or not password_hash:
        return False
    
    # Implement proper authentication logic here
    # For example, compare with securely stored credentials
    
    # For demo purposes only:
    return username == "admin" and password_hash == "demo_hash"

def authorize_operation(user_id, operation_type):
    """Simple authorization check - this should be expanded."""
    # This is a placeholder for a proper authorization system
    # In a real system, you would check against user roles and permissions
    
    # Implement proper authorization logic here
    # For example, check if user has permission for the operation
    
    # For demo purposes only:
    allowed_operations = ["read", "update"]
    if operation_type not in allowed_operations:
        return False
    
    return True

def main_loop():
    """Run the interactive loop with security controls."""
    global qa_chain, memory  # Declare qa_chain as global

    memory = ConversationBufferMemory()

    print("Welcome to ScoutAI. Type 'exit' to quit.")
    while True:
        try:
            # Get user input
            user_input = input("You: ")

            # Check if user wants to exit
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break

            # Basic input validation
            if not user_input.strip():
                print("Please enter a valid query.")
                continue
                
            # Process user input
            result = qa_chain({"query": user_input})
            response = result["result"]
            source_docs = result.get("source_documents", [])

            # Save to Memory
            memory.save_context({"query": user_input}, {"result": response})

            # Print ScoutAI response
            print(f"ScoutAI: {response}")

            if source_docs:
                print("References:")
                for doc in source_docs:
                    file_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                    print(f"- {file_name}")

        except KeyboardInterrupt:
            if handle_interrupt():
                print("Goodbye!")
                break
        except Exception as e:
            logging.error(f"Error in main loop: {type(e).__name__}")
            print("An error occurred. Please try again.")

def add_database(database_paths):
    """Add a new database securely."""
    try:
        new_id = input("Enter a unique ID for the new database: ").strip()
        if not new_id:
            print("Database ID cannot be empty.")
            return
            
        if new_id in database_paths:
            print("Database ID already exists. Please choose a different ID.")
            return

        new_name = input("Enter a name for the new database: ").strip()
        if not new_name:
            print("Database name cannot be empty.")
            return
            
        # Get path input and sanitize it
        db_path_input = input("Enter the path for the new database: ").strip()
        new_path = ensure_directory_exists(db_path_input)

        # Prompt for chunk size, overlap, and data directory
        try:
            chunk_size = validate_positive_int(input("Enter chunk size for the new database: ").strip(), "Chunk size")
            overlap = validate_positive_int(input("Enter overlap size for the new database: ").strip(), "Overlap size")
        except ValueError as e:
            print(f"Input error: {e}")
            return
            
        # Get data directory input and sanitize it
        data_dir_input = input("Enter the path of the directory containing the data to be added to the database: ").strip()
        data_directory = get_safe_path(data_dir_input)

        # Ensure the data directory exists
        if not os.path.isdir(data_directory):
            print(f"The directory '{data_directory}' does not exist.")
            return

        # Load documents
        documents = load_documents(data_directory)
        
        # Split documents
        chunks = split_documents(documents, chunk_size, overlap)

        # Create and update the database
        print("Creating and updating the database...")
        with tqdm(total=100, desc="Progress", unit="%") as pbar:
            reprocess_and_update(chunks, new_path, chunk_size, overlap)
            pbar.update(100)

        # Update configuration
        database_paths[new_id] = {"name": new_name, "path": new_path}
        save_config("config.json", {"database_paths": database_paths})

        print(f"New database '{new_name}' added successfully with ID '{new_id}'.")
    except SecurityError as e:
        logging.error(f"Security error adding database: {e}")
        print(f"Security error: {e}")
    except Exception as e:
        logging.error(f"Error adding database: {type(e).__name__}")
        print(f"An error occurred while adding the database: {e}")

def update_database(database_paths):
    """Update an existing database securely."""
    try:
        selected_paths = select_database(database_paths)
        if not selected_paths:
            return

        for db_path in selected_paths:
            # Prompt for chunk size, overlap, and data directory
            try:
                chunk_size = validate_positive_int(input("Enter chunk size for the updated database: ").strip(), "Chunk size")
                overlap = validate_positive_int(input("Enter overlap size for the updated database: ").strip(), "Overlap size")
            except ValueError as e:
                print(f"Input error: {e}")
                continue
                
            # Get data directory input and sanitize it
            data_dir_input = input("Enter the path of the directory containing the new data to be added to the database: ").strip()
            data_directory = get_safe_path(data_dir_input)

            # Ensure the data directory exists
            if not os.path.isdir(data_directory):
                print(f"The directory '{data_directory}' does not exist.")
                continue

            # Load documents
            documents = load_documents(data_directory)
            
            # Split documents
            chunks = split_documents(documents, chunk_size, overlap)

            # Update the database
            print(f"Updating the database at '{db_path}'...")
            with tqdm(total=100, desc="Progress", unit="%") as pbar:
                reprocess_and_update(chunks, db_path, chunk_size, overlap)
                pbar.update(100)

            print("Database updated successfully.")
    except SecurityError as e:
        logging.error(f"Security error updating database: {e}")
        print(f"Security error: {e}")
    except Exception as e:
        logging.error(f"Error updating database: {type(e).__name__}")
        print(f"An error occurred while updating the database: {e}")

def delete_database(database_paths):
    """Delete one or more databases securely."""
    try:
        if not database_paths:
            print("No databases available to delete.")
            return

        # Display current databases
        print("\nAvailable Databases for Deletion:")
        for db_id, info in database_paths.items():
            print(f"{db_id}: {info['name']} ({info['path']})")

        # Get user input for deletion
        selected_ids = input("Enter the IDs of the databases to delete (comma-separated), or '0' to cancel: ")

        if selected_ids == "0":
            print("Deletion cancelled.")
            return

        selected_ids = selected_ids.split(',')

        for db_id in selected_ids:
            db_id = db_id.strip()
            if db_id in database_paths:
                db_info = database_paths[db_id]
                confirm = input(f"Are you sure you want to delete '{db_info['name']}'? This action is irreversible. (y/n): ").strip().lower()
                if confirm == "y":
                    # Sanitize path before deletion
                    safe_path = get_safe_path(db_info['path'])
                    shutil.rmtree(safe_path)
                    del database_paths[db_id]
                    print(f"Database '{db_info['name']}' deleted.")
                else:
                    print(f"Skipped deletion of '{db_info['name']}'.")
            else:
                print(f"Invalid database ID: {db_id}. Skipping.")

        # Save updated configuration
        save_config("config.json", {"database_paths": database_paths})
        print("Deletion process completed.")
    except SecurityError as e:
        logging.error(f"Security error deleting database: {e}")
        print(f"Security error: {e}")
    except Exception as e:
        logging.error(f"Error deleting database: {type(e).__name__}")
        print(f"An error occurred while deleting the database: {e}")

# Pre-configured User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/91.0.864.48"
]

# Initialize download counter
download_counter = SafeCounter(0)

async def download_pdf(pdf_url, download_dir, user_agent, rate_limiter, temp_file, batch_file, pdf_log_file, max_downloads):
    """Download a PDF file securely."""
    try:
        # Validate URL
        pdf_url = validate_url(pdf_url)
        
        # Check if we've reached the download limit
        current_count = await download_counter.get()
        if current_count >= max_downloads:
            return
        
        # Increment counter
        await download_counter.increment()
        
        # Rate limiting
        await rate_limiter.acquire()

        headers = {'User-Agent': user_agent}
        
        # Use timeout and secure connection settings
        timeout = aiohttp.ClientTimeout(total=60)
        conn = aiohttp.TCPConnector(ssl=True)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
            try:
                async with session.get(pdf_url, headers=headers) as response:
                    # Check response status
                    if response.status != 200:
                        logging.warning(f"Failed to download PDF: {pdf_url}, status: {response.status}")
                        return
                    
                    # Verify content type
                    content_type = response.headers.get('content-type', '')
                    if 'application/pdf' not in content_type.lower():
                        logging.warning(f"Content is not PDF: {pdf_url}, content-type: {content_type}")
                        return
                        
                    # Generate a safe filename
                    filename = os.path.basename(urlparse(pdf_url).path)
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
                    
                    # Create a safe path for the file
                    file_path = os.path.join(download_dir, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    total_size = int(response.headers.get('content-length', 0))
                    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc=filename)

                    # Create temporary file for atomic write
                    temp_download = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                    
                    try:
                        async with aiofiles.open(temp_download.name, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                await f.write(chunk)
                                progress_bar.update(len(chunk))

                        progress_bar.close()
                        
                        # Move the temporary file to the destination (atomic operation)
                        shutil.move(temp_download.name, file_path)
                        
                        print(f"Downloaded: {file_path}")

                        # Log the successful download
                        async with aiofiles.open(temp_file, 'a') as log:
                            await log.write(f"Successfully downloaded: {pdf_url}\n")

                        async with aiofiles.open(batch_file, 'a') as batch:
                            await batch.write(f"{pdf_url}\n")

                        async with aiofiles.open(pdf_log_file, 'a') as log:
                            await log.write(f"Successfully downloaded: {pdf_url}\n")
                    
                    except Exception as e:
                        # Clean up temporary file in case of error
                        secure_delete_file(temp_download.name)
                        raise e

            except aiohttp.ClientError as e:
                logging.error(f"Network error downloading PDF: {type(e).__name__}")
                raise NetworkError(f"Failed to download PDF: {e}") from e
                
    except SecurityError as e:
        logging.error(f"Security error downloading PDF: {e}")
    except NetworkError as e:
        logging.error(f"Network error: {e}")
    except Exception as e:
        logging.error(f"Error downloading PDF: {type(e).__name__}")

async def scrape_for_pdfs(url, download_dir, concurrent_pages, concurrent_downloads, max_downloads_param, min_delay, max_delay, max_requests_per_minute, user_agent, visited_urls, pdf_log_file, completed_page_log_file, temp_file, batch_file, session):
    """Scrape a website for PDF files securely."""
    try:
        # Validate inputs
        url = validate_url(url)
        download_dir = get_safe_path(download_dir)
        pdf_log_file = get_safe_path(pdf_log_file)
        completed_page_log_file = get_safe_path(completed_page_log_file)
        temp_file = get_safe_path(temp_file)
        batch_file = get_safe_path(batch_file)
        
        # Create rate limiter
        rate_per_minute = max(1, min(max_requests_per_minute, 60))  # Ensure valid rate
        rate_limiter = RateLimiter(rate_per_minute, 60.0)
        
        # Create semaphore for concurrent downloads
        semaphore = asyncio.Semaphore(concurrent_downloads)
        
        # Reset download counter
        global download_counter
        download_counter = SafeCounter(0)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    # Removed "--disable-web-security",
                    "--timeout=30000"
                ]
            )
            
            async def navigate_and_scrape(url):
                # Check if we've reached the download limit
                remaining = await download_counter.remaining(max_downloads_param)
                if remaining <= 0:
                    return

                # Apply rate limiting
                await rate_limiter.acquire()
                
                # Check if URL has already been visited
                if url in visited_urls:
