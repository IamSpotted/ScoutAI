import os
import warnings
from langchain.chains import RetrievalQA
from langchain_community.llms import HuggingFacePipeline
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from get_embedding_function import get_embedding_function


#Ignore Warnings
#warnings.filterwarnings("ignore")

#Set Chroma Path
CHROMA_PATH = "/home/cavllm/ScoutAI/database"

#Load Embeddings
embedding_function = get_embedding_function()

#Initialize ChromaDB
vector_store = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embedding_function
)

#Setup retriever
retriever = vector_store.as_retriever()

#Intialize HuggingFace model
chat = HuggingFacePipeline(model="sentence-transformers/all-MiniLM-L6-v2", task="text_generation")

#Setup RetrievalQA Chain
qa = RetrievalQA.from_chain_type(
    llm=chat,
    chain_type="stuff",
    retriever=retriever
)
