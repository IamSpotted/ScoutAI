import os
import json
import warnings
import asyncio
import random
import shututil
import logging
from tqdm import tqdm  # Progress bar library
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from get_embedding_function import get_embedding_function
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm
import aiofiles
import aiohttp
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from logging_models import PdfDownloadLog, CompletedPagesLog, Base

# Ignore Warnings
warnings.filterwarnings("ignore")

# Global Variables
qa_chain = None
memory = None
"""
def load_config(file_path):
    #Load configuration from a JSON file.
    try:
        with open(file_path, 'r') as file:
            config = json.load(file)
        return config
    except FileNotFoundError:
        print(f"Error: The configuration file '{file_path}' was not found.")
        exit()
    except json.JSONDecodeError:
        print("Error: Configuration file is not a valid JSON.")
        exit()
"""

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
        print("Error: Configuration file is not a valid JSON.")
        exit()

def save_config(file_path, config):
    """Save configuration to a JSON file."""
    with open(file_path, 'w') as file:
        json.dump(config, file, indent=4)

def handle_interrupt():
    """Handle keyboard interrupt with confirmation."""
    print("\nKeyboardInterrupt detected. Are you sure you want to exit? (y/n)")
    confirm = input().strip().lower()
    return confirm in ["y", "yes"]

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
                return None
                print("Returning to main menu...")
                
            
            selected_ids = db_choice.split(',')
            valid_selection = True
            databases_selected = []

            for db_id in selected_ids:
                db_id = db_id.strip()
                if db_id in database_paths:
                    databases_selected.append(database_paths[db_id]["path"])
                else:
                    print(f"Invalid Selection '{db_id}'.")
                    valid_selection = False

            if valid_selection and databases_selected:
                return databases_selected
            else:
                print("Please make a valid selection.")
        
        except KeyboardInterrupt:
            if handle_interrupt():
                exit()

def initialize_vector_stores(paths):
    """Initialize ChromaDB instances."""
    vector_stores = []
    for path in paths:
        vector_stores.append(Chroma(
            persist_directory=path,
            embedding_function=get_embedding_function()
        ))
    return vector_stores

def load_documents(directory_path):
    """Load documents from the specified directory."""
     
    # Initialize the document loader
    loader = PyPDFDirectoryLoader(directory_path)
    
    # Load documents
    documents = loader.load()
    
    return documents

def ensure_directory_exists(path):
    """Create directory if it does not exist."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        os.makedirs(path)

def split_documents(documents, chunk_size, chunk_overlap):
    """Split documents into chunks based on chunk size and overlap."""
    # Initialize text splitter with specified chunk size and overlap
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    split_docs = []
    for doc in documents:
        split_docs.extend(text_splitter.split_documents([doc]))
    
    return split_docs

def reprocess_and_update(chunks, db_path, chunk_size, chunk_overlap):
    """Reprocess documents and update the database with new chunks."""
    from langchain.vectorstores import Chroma

    # Initialize ChromaDB instance for the database
    vector_store = Chroma(
        persist_directory=db_path,
        embedding_function=get_embedding_function()  # Ensure embedding_function is available in this scope
    )

    # Add new chunks to the vector store
    print("Adding new documents to the database...")
    with tqdm(total=len(chunks), desc="Progress (Adding Documents)", unit="chunk") as pbar:
        vector_store.add_documents(chunks)
        pbar.update(len(chunks))

    # Save the updated vector store
    print("Saving the updated database...")
    vector_store.persist()

    print(f"Database at '{db_path}' has been updated successfully.")

def main_loop():
    """Run the interactive loop."""
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
                    file_name = os.path.basename(doc.metadata['source'])
                    print(f"- {file_name}")

        except KeyboardInterrupt:
            if handle_interrupt():
                print("Goodbye!")
                break

def add_database(database_paths):
    """Add a new database and create it using the existing script logic with a progress bar."""
    new_id = input("Enter a unique ID for the new database: ").strip()
    if new_id in database_paths:
        print("Database ID already exists. Please choose a different ID.")
        return

    new_name = input("Enter a name for the new database: ").strip()
    new_path = os.path.expanduser(input("Enter the path for the new database: ").strip())

    ensure_directory_exists(new_path)

    # Prompt for chunk size, overlap, and data directory
    chunk_size = int(input("Enter chunk size for the new database: ").strip())
    overlap = int(input("Enter overlap size for the new database: ").strip())
    data_directory = os.path.expanduser(input("Enter the path of the directory containing the data to be added to the database: ").strip())

    # Ensure the data directory exists
    if not os.path.isdir(data_directory):
        print("The specified data directory does not exist.")
        return

    # Save the new database information to the config
    database_paths[new_id] = {"name": new_name, "path": new_path}
    save_config('config.json', {"database_paths": database_paths})
    print("Database added successfully.")

    # Create the new database using the existing script logic
    from langchain.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.embeddings import OpenAIEmbeddings  # or whatever embedding function you're using

    # Initialize document loader
    loader = PyPDFDirectoryLoader(data_directory)
    documents = loader.load()

    # Split documents using the chunk size and overlap provided
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    
    # Create a progress bar for splitting documents
    print("Splitting documents...")
    split_docs = []
    for doc in tqdm(documents, desc="Progress", unit="doc"):
        split_docs.extend(text_splitter.split_documents([doc]))

    # Initialize embedding function
    embedding_function = get_embedding_function()  # Ensure this matches your implementation

   # Progress bar for creating vector store and adding documents
    print("Creating vector store and adding documents...")
    with tqdm(total=len(split_docs), desc="Progress (Vector Store)", unit="doc") as pbar:
        vector_store = Chroma(
            persist_directory=new_path,
            embedding_function=embedding_function
        )
        for doc in split_docs:
            vector_store.add_documents([doc])
            pbar.update(1)

    # Save the database and show progress
    print("Saving the database...")
    with tqdm(total=100, desc="Progress (Saving Database)", unit="%") as pbar:
        vector_store.persist()
        for _ in range(100):
            pbar.update(1)

    print(f"Database created and stored at {new_path}.")

def update_database(database_paths):
    """Update an existing database."""
    db_id = input("Enter the ID of the database to update: ").strip()
    if db_id not in database_paths:
        print("Database ID not found.")
        return

    db_entry = database_paths[db_id]
    db_path = db_entry["path"]

    data_directory = os.path.expanduser(input("Enter the path of the directory containing the new data: ").strip())
    
    if not os.path.isdir(data_directory):
        print("The specified data directory does not exist.")
        return

    # Initialize document loader
    loader = PyPDFDirectoryLoader(data_directory)
    documents = loader.load()

    # Load and split documents
    documents = load_documents(data_directory)
    existing_chunk_size = 800  # Default value, or load from config if needed
    existing_chunk_overlap = 100  # Default value, or load from config if needed
    
    # Prompt for new settings if needed
    change_settings = input("Do you want to change chunk size and overlap? (y/n): ").strip().lower()
    if change_settings == 'y':
        try:
            chunk_size = int(input(f"Enter the new chunk size (default {existing_chunk_size}): ") or existing_chunk_size)
            chunk_overlap = int(input(f"Enter the new chunk overlap (default {existing_chunk_overlap}): ") or existing_chunk_overlap)
        except ValueError:
            print("Invalid input. Please enter numeric values.")
            return
    else:
        chunk_size = existing_chunk_size
        chunk_overlap = existing_chunk_overlap

    chunks = split_documents(documents, chunk_size, chunk_overlap)
    
    # Reprocess and update
    reprocess_and_update(chunks, db_path, chunk_size, chunk_overlap)

def delete_database(database_paths):
    """Delete one or more databases."""
    import shutil

    if not database_paths:
        print("No databases available to delete.")
        return

    # Display current databases
    print("\nAvailable Databases for Deletion:")
    for db_id, info in database_paths.items():
        print(f"{db_id}: {info['name']} ({info['path']})")

    # Get user input for deletion
    db_ids = input("Enter the ID(s) of the database(s) to delete, separated by commas: ").split(',')
    db_ids = [db_id.strip() for db_id in db_ids]

    # Validate selected IDs
    valid_ids = [db_id for db_id in db_ids if db_id in database_paths]
    if not valid_ids:
        print("No valid database IDs provided.")
        return

    # Ask for confirmation
    print("\nYou have selected the following databases for deletion:")
    for db_id in valid_ids:
        print(f"- {db_id}: {database_paths[db_id]['name']}")

    confirm = input("Are you sure you want to delete these databases? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Deletion canceled.")
        return

    # Perform deletion
    for db_id in valid_ids:
        db_path = os.path.expanduser(database_paths[db_id]["path"])

        # Ensure all database connections are closed before deletion
        # Close database connections here (if any)

        if os.path.exists(db_path):
            # Recursively delete the entire directory and its contents
            try:
                shutil.rmtree(db_path)
                print(f"Deleted database directory at '{db_path}'.")
            except Exception as e:
                print(f"Error deleting '{db_path}': {e}")

        # Remove database entry from configuration
        del database_paths[db_id]

    # Save updated configuration
    save_config('config.json', {"database_paths": database_paths})
    print("Selected databases have been deleted.")

def database_management():
    """Handle database management tasks."""
    database_paths = load_config('config.json').get('database_paths', {})
    
    while True:
        try:
            print("\nDatabase Management Menu:")
            print("1: Add database")
            print("2: Update database")
            print("3: Delete database")
            print("0: Back to main menu")

            choice = input("Enter your choice: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                add_database(database_paths)
            elif choice == "2":
                update_database(database_paths)
            elif choice == "3":
                delete_database(database_paths)
            else:
                print("Invalid choice. Please try again.")
        
        except KeyboardInterrupt:
            if handle_interrupt():
                break


# Suppress SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


# Pre-configured User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/91.0.864.48"
]

# Shared state for tracking downloads
download_count_lock = asyncio.Lock()
download_count = 0
max_downloads = 0  # Will be set by main()

async def download_pdf(pdf_url, download_dir, user_agent, min_delay, max_delay, temp_file, batch_file, pdf_log_file):
    global download_count
    async with download_count_lock:
        if download_count >= max_downloads:
            return
        download_count += 1

    headers = {'User-Agent': user_agent}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(pdf_url, headers=headers) as response:
                filename = pdf_url.split('/')[-1]
                file_path = os.path.join(download_dir, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                total_size = int(response.headers.get('content-length', 0))
                progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc=filename)

                async with aiofiles.open(file_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await f.write(chunk)
                        progress_bar.update(len(chunk))

                progress_bar.close()
                print(f"Downloaded: {file_path}")

                # Log the successful download
                async with aiofiles.open(temp_file, 'a') as log:
                    await log.write(f"Successfully downloaded: {pdf_url}\n")

                async with aiofiles.open(batch_file, 'a') as batch:
                    await batch.write(f"{pdf_url}\n")

                async with aiofiles.open(pdf_log_file, 'a') as log:
                    await log.write(f"Successfully downloaded: {pdf_url}\n")

        except Exception as e:
            print(f"Error downloading PDF: {e}")

    # Rate limiting
    rate_limit_delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(rate_limit_delay)

async def scrape_for_pdfs(url, download_dir, concurrent_pages, concurrent_downloads, max_downloads_param, min_delay, max_delay, max_requests_per_minute, user_agent, visited_urls, pdf_log_file, completed_page_log_file, temp_file, batch_file, semaphore, session):  # **Added session parameter**
    global max_downloads
    max_downloads = max_downloads_param  # Set the global max_downloads

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def navigate_and_scrape(url):
            async with download_count_lock:
                if download_count >= max_downloads:
                    return

            page = await browser.new_page(user_agent=user_agent)
            try:
                # Navigate to the page
                await page.goto(url, timeout=60000)  # 60 seconds timeout

                # Scraping for PDF links
                pdf_links = await page.evaluate('''Array.from(document.querySelectorAll('a[href$=".pdf"]')).map(a => a.href)''')
                pdf_links = list(set(pdf_links))  # Remove duplicates

                # Filter based on remaining max_downloads
                async with download_count_lock:
                    remaining_downloads = max_downloads - download_count
                if len(pdf_links) > remaining_downloads:
                    pdf_links = pdf_links[:remaining_downloads]

                # Download PDFs while avoiding duplicates based on the temp file
                async def download_with_semaphore(pdf_url):
                    async with semaphore:
                        async with aiofiles.open(temp_file, 'r') as temp_f:
                            existing_urls = await temp_f.read()
                        if pdf_url not in existing_urls:
                            await download_pdf(pdf_url, download_dir, user_agent, min_delay, max_delay, temp_file, batch_file, pdf_log_file)

                # Process PDFs
                await asyncio.gather(*[download_with_semaphore(pdf_url) for pdf_url in pdf_links])

                # Stop further scraping if the max download count is reached
                async with download_count_lock:
                    if download_count >= max_downloads:
                        return

                # Mark page as completed in the database
                page_log_entry = CompletedPagesLog(url=url, status="Completed")
                session.add(page_log_entry)
                session.commit()

                # Mark page as completed in the log file
                async with aiofiles.open(completed_page_log_file, 'a') as completed_log:
                    await completed_log.write(f"Completed: {url}\n")

                # Get all internal links on the page
                all_links = await page.evaluate('''Array.from(document.querySelectorAll('a[href]')).map(a => a.href)''')
                for link in all_links:
                    parsed_link = urlparse(link)
                    if parsed_link.netloc == urlparse(url).netloc and link not in visited_urls:
                        visited_urls.add(link)
                        await navigate_and_scrape(link)

            except Exception as e:
                print(f"Error navigating to {url}: {e}")

            finally:
                await page.close()

        # Start scraping from the initial URL
        await navigate_and_scrape(url)

        await browser.close()

async def main_menu():
    """Display the main menu and handle user selection."""
    try:
        config = load_config("config.json")
        database_paths = config.get("database_paths", {})

        while True:
            print("\nMain Menu")
            print("1: Chatbot")
            print("2: Database Management")
            print("3: Download PDFs")
            print("0: Exit")

            choice = input("Select an option: ").strip()

            if choice == "1":
                selected_paths = select_database(database_paths)
                if selected_paths:
                    vector_stores = initialize_vector_stores(selected_paths)
                    qa_chain = RetrievalQA.from_chain_type(
                        llm=ChatOllama(model="llama2"),
                        chain_type="stuff",
                        retriever=vector_stores[0].as_retriever(),
                        memory=memory,
                        return_source_documents=True
                    )
                    main_loop()
            elif choice == "2":
                print("\nDatabase Management")
                print("1: Add Database")
                print("2: Update Database")
                print("3: Delete Database")
                print("0: Back to Main Menu")

                db_choice = input("Select an option: ").strip()
                if db_choice == "1":
                    add_database(database_paths)
                elif db_choice == "2":
                    update_database(database_paths)
                elif db_choice == "3":
                    delete_database(database_paths)
                elif db_choice == "0":
                    continue
                else:
                    print("Invalid selection.")
            elif choice == "3":
                await main()
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Invalid selection.")
    
    except KeyboardInterrupt:
        if handle_interrupt():
            print("Exiting...")
            exit()

async def main():
    # Setup database session
    db_path = os.path.expanduser('~/chatbot/logging/logging_db.sqlite')
    DATABASE_URL = f'sqlite:///{db_path}'
    engine = create_engine(DATABASE_URL, echo=True)
    SessionLocal = sessionmaker(bind=engine)

    # Create the tables if they don't exist
    Base.metadata.create_all(bind=engine)

    url = input("Enter the URL: ")
    download_dir = os.path.expanduser(input("Enter the download directory: "))
    pdf_log_file = os.path.expanduser(input("Enter the PDF log file path (relative to download directory): "))
    completed_page_log_file = os.path.expanduser(input("Enter the completed pages log file path (relative to download directory): "))

    # Ensure the directory for logs and downloads exists
    os.makedirs(download_dir, exist_ok=True)

    # Construct absolute paths for log files
    pdf_log_file = os.path.join(download_dir, pdf_log_file)
    completed_page_log_file = os.path.join(download_dir, completed_page_log_file)

    # Ensure log files are created if they don't exist
    os.makedirs(os.path.dirname(pdf_log_file), exist_ok=True)
    os.makedirs(os.path.dirname(completed_page_log_file), exist_ok=True)

    # **Initialize database session**
    session = SessionLocal()

    # Fetch URLs from the database
    temp_file_path = os.path.join(download_dir, 'temp_urls.txt')
    batch_file_path = os.path.join(download_dir, 'batch_urls.txt')

    async with aiofiles.open(temp_file_path, 'w') as temp_file:
        # Fetch completed pages
        completed_pages = session.query(CompletedPagesLog).filter(CompletedPagesLog.url.like(f"%{urlparse(url).netloc}%")).all()
        for page in completed_pages:
            await temp_file.write(f"{page.url}\n")
        
        # Fetch downloaded PDFs
        downloaded_pdfs = session.query(PdfDownloadLog).filter(PdfDownloadLog.url.like(f"%{urlparse(url).netloc}%")).all()
        for pdf in downloaded_pdfs:
            await temp_file.write(f"{pdf.url}\n")

    # Check if URL ends with .pdf
    if url.lower().endswith('.pdf'):
        print(f"Detected single PDF download: {url}")
        user_agent = input("Enter a User-Agent string (leave empty for random): ")
        if not user_agent:
            user_agent = random.choice(USER_AGENTS)
        await download_pdf(url, download_dir, user_agent, 0, 0, temp_file_path, batch_file_path, pdf_log_file)  # No delay for single file
        # Add single PDF to batch file
        async with aiofiles.open(batch_file_path, 'a') as batch_file:
            await batch_file.write(f"{url}\n")
    else:
        concurrent_pages = int(input("Enter the number of concurrent pages to navigate: "))
        concurrent_downloads = int(input("Enter the number of concurrent downloads: "))
        max_downloads_param = int(input("Enter the maximum number of downloads: "))
        min_delay = float(input("Enter the minimum delay (in seconds): "))
        max_delay = float(input("Enter the maximum delay (in seconds): "))
        max_requests_per_minute = int(input("Enter the maximum requests per minute: "))
        user_agent = input("Enter a User-Agent string (leave empty for random): ")
        if not user_agent:
            user_agent = random.choice(USER_AGENTS)

        visited_urls = set()
        # **Pass the session object to scrape_for_pdfs**
        await scrape_for_pdfs(url, download_dir, concurrent_pages, concurrent_downloads, max_downloads_param, min_delay, max_delay, max_requests_per_minute, user_agent, visited_urls, pdf_log_file, completed_page_log_file, temp_file_path, batch_file_path, asyncio.Semaphore(concurrent_downloads), session)  # **Added session parameter**

    # Clean up files after processing
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
    if os.path.exists(batch_file_path):
        os.remove(batch_file_path)

if __name__ == "__main__":
    asyncio.run(main_menu())
