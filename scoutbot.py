import os
import json
import yaml
import warnings

from langchain.chains import RetrievalQA
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from get_embedding_function import get_embedding_function
from langchain.memory import ConversationBufferMemory

# Ignore Warnings
warnings.filterwarnings("ignore")

def load_config(file_path):
    #***Load Config from a JSON file***
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
                print("Exiting...")
                exit()

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

def initialize_vector_stores(paths):
    """Initialize ChromaDB instances."""
    vector_stores = []
    for path in paths:
        vector_stores.append(Chroma(
            persist_directory=path,
            embedding_function=embedding_function
        ))
    return vector_stores

def main_loop():
    """Run the interactive loop."""
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

# Load configuration
config = load_config('config.json')
database_paths = config.get('database_paths', {})

# Main program execution
databases_selected = select_database(database_paths)
embedding_function = get_embedding_function()
vector_stores = initialize_vector_stores(databases_selected)
retrievers = [store.as_retriever() for store in vector_stores]
combined_retriever = retrievers[0]

if len(retrievers) > 1:
    for retriever in retrievers[1:]:
        # Assuming combine is a valid method, else use an alternative approach
        combined_retriever = combined_retriever.combine(retriever)

llm = ChatOllama(model="phi3:mini", temperature=0)
memory = ConversationBufferMemory(memory_key="chat history", return_messages=True)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff", # Can be changed depending on needs
    retriever=combined_retriever,
    input_key="query",
    return_source_documents=True
)

main_loop()
