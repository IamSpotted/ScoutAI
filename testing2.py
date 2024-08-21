import os
import json
import warnings
from datetime import datetime
from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from get_embedding_function import get_embedding_function
from langchain.memory import ConversationBufferMemory

# Ignore Warnings
warnings.filterwarnings("ignore")

def load_config(file_path):
    """Load Config from a JSON file."""
    with open(file_path, 'r') as file:
        config = json.load(file)
    return config

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

            print("a: query all databases")
            print("0: Exit")

            db_choice = input("Enter your selection: ")

            if db_choice == "0":
                print("Returning to main menu")
                return None

            if db_choice == "a":
                databases_selected = [info["path"] for info in database_paths.values()]
                return databases_selected

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

def database_management_menu():
    """Display the database management options."""
    while True:
        print("\nDatabase Management:")
        print("1: Create a new database")
        print("2: Update an existing database")
        print("3: Delete a database")
        print("0: Go back to main menu")
        
        choice = input("Select an option: ")
        
        if choice == "1":
            print("Creating a new database...")
            # Add your logic to create a database
        elif choice == "2":
            print("Updating an existing database...")
            # Add your logic to update a database
        elif choice == "3":
            print("Deleting a database...")
            # Add your logic to delete a database
        elif choice == "0":
            break
        else:
            print("Invalid selection. Please try again.")

def get_formatted_timestamp():
    """Get the current timestamp formatted as Day/Time(UTC)/Month/Year."""
    now = datetime.utcnow()
    day = now.strftime('%d')
    time = now.strftime('%H%M')
    month = now.strftime('%b').upper()
    year = now.strftime('%y')
    return f"{day}{time}Z{month}{year}"

def main_loop(qa_chain, memory):
    """Run the interactive chatbot loop."""
    print("Welcome to ScoutAI. Type 'exit' to quit.")
    while True:
        try:
            # Generate and append the timestamp to the left of user input
            user_timestamp = get_formatted_timestamp()
            user_input = input(f"[{user_timestamp}] You: ")

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
            bot_timestamp = get_formatted_timestamp()
            print(f"[{bot_timestamp}] ScoutAI: {response}")

            if source_docs:
                print("References:")
                for doc in source_docs:
                    file_name = os.path.basename(doc.metadata['source'])
                    print(f"- {file_name}")

        except KeyboardInterrupt:
            if handle_interrupt():
                print("Goodbye!")
                break

def chatbot_loop(config):
    """Run the interactive chatbot loop."""
    database_paths = config.get('database_paths', {})

    # Get selected databases
    databases_selected = select_database(database_paths)
    print(f"Selected databases: {databases_selected}")

    if databases_selected is None:
        return

    # Initialize your QA chain and memory
    embedding_function = get_embedding_function()
    chroma_db = Chroma(embedding_function=embedding_function)
    memory = ConversationBufferMemory()
    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOllama(model="phi3:mini", temperature=0),
        retriever=chroma_db.as_retriever(),
        chain_type="stuff"
    )

    # Start chatbot interaction
    main_loop(qa_chain, memory)

def main_menu():
    """Main menu with two options: Database Management and Chatbot."""
    while True:
        print("\nMain Menu:")
        print("1: Database Management")
        print("2: Chatbot")
        print("0: Exit")
        
        choice = input("Select an option: ")
        
        if choice == "1":
            database_management_menu()
        elif choice == "2":
            config = load_config('config.json')
            chatbot_loop(config)
        elif choice == "0":
            print("Exiting...")
            exit()
        else:
            print("Invalid selection. Please try again.")

if __name__ == "__main__":
    main_menu()
