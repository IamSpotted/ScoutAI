import os
import json
import warnings
from tqdm import tqdm  # Progress bar library
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from get_embedding_function import get_embedding_function
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Ignore Warnings
warnings.filterwarnings("ignore")

# Global Variables
qa_chain = None
memory = None

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
    from langchain.embeddings import HuggingFaceEmbeddings  # or whatever embedding function you're using

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

def main_menu():
    """Display the main menu and handle user choices."""
    global qa_chain  # Declare qa_chain as global

    config = load_config('config.json')
    database_paths = config.get("database_paths", {})

    while True:
        print("Main Menu:")
        print("1: Database Management")
        print("2: Chatbot")
        print("0: Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            print("Database Management Menu:")
            print("1: Add Database")
            print("2: Delete Database")
            print("3: Update Database")
            print("0: Return to Main Menu")

            db_choice = input("Enter your choice: ").strip()

            if db_choice == "1":
                add_database(database_paths)
            elif db_choice == "2":
                delete_database(database_paths)
            elif db_choice == "3":
                update_database(database_paths)
            elif db_choice == "0":
                continue
            else:
                print("Invalid choice.")
        elif choice == "2":
            databases_selected = select_database(database_paths)
            if not databases_selected:
                print("No databases selected. Returning to menu...")
                continue

            vector_stores = initialize_vector_stores(databases_selected)
            retrievers = [store.as_retriever() for store in vector_stores]

            # Combine retrievers if more than one
            combined_retriever = retrievers[0] if retrievers else None
            if len(retrievers) > 1:
                from langchain.chains import MultiRetrievalQAChain
                combined_retriever = MultiRetrievalQAChain(retrievers)

            llm = ChatOllama(model="phi3:mini", temperature=0)  # Provide the model parameter
            memory = ConversationBufferMemory(memory_key="chat history", return_messages=True)

            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",  # Can be changed depending on needs
                retriever=combined_retriever,
                input_key="query",
                return_source_documents=True
            )

            main_loop()
        elif choice == "0":
            print("Exiting...")
            exit()
        else:
            print("Invalid choice.")

# Run the main menu
main_menu()
