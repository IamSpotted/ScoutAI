import os
import warnings
from langchain.chains import RetrievalQA
from langchain_community.llms import HuggingFacePipeline
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from get_embedding_function import get_embedding_function
from langchain.memory import ConversationBufferMemory

#Ignore Warnings
warnings.filterwarnings("ignore")

#Database Paths
CHROMA_PATH = {
    "1": {"name": "Scout", "path": "/home/spotted/scout/database"},
    "2": {"name": "Example", "path": "/Path/to/database2"}
}

#Database selection loop
while True:
    #Display database options
    print("Please select a database (enter numbers separated by commas):")
    for key, info in CHROMA_PATH.items():
        print(f"{key}: {info['name']}")

    print("a: query all databases")
    print("0: Exit")

    db_choice = input("Enter your selection: ")

    if db_choice == "0":
        print("Exiting...")
        exit()

    if db_choice == "a":
        databases_selected = [info["path"] for info in CHROMA_PATH.values()]
        break

    selected_ids = db_choice.split(',')
    valid_selection = True
    databases_selected = []

    for db_id in selected_ids:
        db_id = db_id.strip()
        if db_id in CHROMA_PATH:
            databases_selected.append(CHROMA_PATH[db_id])["path"]
        else:
            print(f"Invalid Selection '{db_id}.")
            valid_selection = False

    if valid_selection and databases_selected:
        break
    else:
        print("Please make a valid selection.")


#Initialize ChromaDB Instances
def initialize_vector_stores(paths):
    vector_stores = []
    for path in paths:
        vector_stores.append(Chroma(
            persist_directory=path,
            embedding_function=embedding_function
        ))
    return vector_stores

#Load Embeddings
embedding_function = get_embedding_function()

#Initialize ChromaDB Instances
vector_stores = initialize_vector_stores(databases_selected)

#Setup retrievers
retrievers = [store.as_retriever() for store in vector_stores]
combined_retriever = retrievers[0]

if len(retrievers) > 1:
    for retriever in retrievers[1:]:
        combined_retriever = combined_retriever.combine(retriever)

#Initialize Ollama LLM
llm = ChatOllama(model="phi3:mini", temperature=0)

#Initialize Memory
memory = ConversationBufferMemory(memory_key="chat history", return_messages=True)

#Create RetrievalQA Chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff", #Can be changed depending on needs
    retriever=combined_retriever,
    input_key="query",
    return_source_documents=True
)


#Interactive Loop
print("Welcome to ScoutAI. Type 'exit' to quit.")
while True:
    #Get user input
    user_input = input("You:")

    #Check if user wants to exit
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("Goodbye!")
        break

    #Process user input
    result = qa_chain({"query": user_input})
    response = result["result"]
    source_docs = result.get("source_documents", [])

    #Save to Memory
    memory.save_context({"query": user_input}, {"result": response})

    #Print ScoutAI response
    print(f"ScoutAI: {response}")

    if source_docs:
        print("References:")
        for doc in source_docs:
            file_name = os.path.basename(doc.metadata['source'])
            print(f"- {file_name}")


      