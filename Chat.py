#Created by IamSpotted. This script incorporates chat memory so that you can have a conversation with contect.
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

#Set Chroma Path
CHROMA_PATH = "/home/spotted/scout/database"

#Load Embeddings
embedding_function = get_embedding_function()

#Initialize ChromaDB
vector_store = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embedding_function
)

#Setup retriever
retriever = vector_store.as_retriever()

#Initialize Ollama LLM
llm = ChatOllama(model="phi3:mini", temperature=0)

#Initialize Memory
memory = ConversationBufferMemory(memory_key="chat history", return_messages=True)

#Create RetrievalQA Chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff", #Can be changed depending on needs
    retriever=retriever,
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


      
