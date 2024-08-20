import os
import json
import warnings
from datetime import datetime

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
    return f"{day}{time}UTC{month}{year}"

def main_loop():
    """Run the interactive chatbot loop."""
    # Ensure you have `qa_chain` and `memory` defined or imported
    


 # Replace with actual import

    print("Welcome to ScoutAI. Type 'exit' to quit.")
    while True:
        try:
            # Get user input
            user_input = input("You: ")

            # Generate and append the timestamp to the left of user input
            user_timestamp = get_formatted_timestamp()
            print(f"[{user_timestamp}] You: {user_input}")

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

def chatbot_loop():
    """Run the interactive chatbot loop."""
    config = load_config('config.json')
    database_paths = config.get('database_paths', {})

    # Get selected databases
    databases_selected = select_database(database_paths)
    print(f"Selected databases: {databases_selected}")

    if databases_selected is None:
        return


    # Start chatbot interaction
    main_loop()

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
            chatbot_loop()
        elif choice == "0":
            print("Exiting...")
            exit()
        else:
            print("Invalid selection. Please try again.")

if __name__ == "__main__":
    main_menu()