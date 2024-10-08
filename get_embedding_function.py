#Based off of Pixegami and modified to Use HuggingFace instead of Ollama and Bedrock embeddings
from langchain_huggingface import HuggingFaceEmbeddings



def get_embedding_function():
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    hf = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs

    )
    return hf
