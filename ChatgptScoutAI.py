import os
import warnings
from langchain.chains import RetrievalQA
from langchain.llms import HuggingFacePipeline
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings


#Ignore Warnings
warnings.filterwarnings("ignore")

#Set Chroma Path
CHROMA_PATH = "/home/cavllm/ScoutAI/database"

#Load Embeddings
embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

#Initialize ChromaDB
vector_store = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embedding_function
)

#Setup retriever
retriever = vector_store.as_retriever()

#Intialize HuggingFace model
chat = HuggingFacePipeline(model="Ollama/phi3:mini", task="text_generation")

#Setup RetrievalQA Chain
qa = RetrievalQA.from_chain_type(
    llm=chat,
    chain_type="stuff",
    retriever=retriever
)