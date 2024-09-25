import streamlit as st
from chromadb import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma as ChromaVectorStore
from langchain.llms import Ollama
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.document_loaders import PyPDFDirectoryLoader

# Streamlit UI for database selection and chatbot interaction
st.title("ScoutAI Chatbot")

# Initialize Ollama client and embedding function
client = Ollama(model="phi3:mini")  # Using Ollama for LLM
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # Your embeddings model

# Handle session state for database paths and messages
if "database_paths" not in st.session_state:
    st.session_state["database_paths"] = {}  # Dict of DB options
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory()

# Function to handle interrupt
def handle_interrupt():
    """Handle keyboard interrupt with confirmation."""
    print("\nKeyboardInterrupt detected. Are you sure you want to exit? (y/n)")
    confirm = input().strip().lower()
    return confirm in ["y", "yes"]

# Function to select a database
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

# Initialize vector stores
def initialize_vector_stores(paths):
    """Initialize ChromaDB instances."""
    vector_stores = []
    for path in paths:
        vector_stores.append(Chroma(
            persist_directory=path,
            embedding_function=embedding_model.embed_documents
        ))
    return vector_stores

# Load documents
def load_documents(directory_path):
    """Load documents from the specified directory."""
    loader = PyPDFDirectoryLoader(directory_path)
    documents = loader.load()
    return documents

# Main interaction logic
def main_loop():
    """Run the chatbot in a loop."""
    st.write("Welcome to ScoutAI. Type your message below.")
    
    # Database selection UI
    selected_databases = select_database(st.session_state["database_paths"])
    vector_stores = initialize_vector_stores(selected_databases)
    
    # Combine vector stores into a single retriever
    retriever = ChromaVectorStore.from_vectorstores(vector_stores)
    
    # Create RAG chain using Ollama LLM and retriever
    qa_chain = ConversationalRetrievalChain(
        retriever=retriever.as_retriever(),
        llm=client,
        memory=st.session_state.memory
    )
    
    # Chat input
    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process user input and get the response
        result = qa_chain({"query": prompt})
        response = result["result"]
        source_docs = result.get("source_documents", [])
        
        with st.chat_message("assistant"):
            st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

        # If there are source documents, show them as references
        if source_docs:
            st.markdown("**References:**")
            for doc in source_docs:
                file_name = os.path.basename(doc.metadata['source'])
                st.markdown(f"- {file_name}")

# Call the main loop function to start the chatbot
main_loop()