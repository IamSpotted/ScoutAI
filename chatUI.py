import os
import warnings
import time

import mesop as me
from langchain.chains import RetrievalQA
from langchain_community.llms import HuggingFacePipeline
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from get_embedding_function import get_embedding_function
from langchain.memory import ConversationBufferMemory

# Ignore Warnings
warnings.filterwarnings("ignore")

# Database Paths
CHROMA_PATH = {
    "1": "/home/spotted/scout/database",
    "2": "/Path/to/database2"
}

# Mesop State Class
@me.stateclass
class State:
    input: str = ""
    output: str = ""
    in_progress: bool = False
    source_docs: list = []

# Page Component
@me.page(path="/starter_kit")
def page():
    initialize_db()  # Initialize DB on page load
    with me.box(
        style=me.Style(
            background="#fff",
            min_height="calc(100% - 48px)",
            padding=me.Padding(bottom=16),
        )
    ):
        with me.box(
            style=me.Style(
                width="min(720px, 100%)",
                margin=me.Margin.symmetric(horizontal="auto"),
                padding=me.Padding.symmetric(horizontal=16),
            )
        ):
            header_text()
            chat_input()
            output_display()
    footer()

def initialize_db():
    state = me.state(State)
    state.vector_stores = initialize_vector_stores(["/home/spotted/scout/database"])
    state.retrievers = [store.as_retriever() for store in state.vector_stores]
    state.combined_retriever = state.retrievers[0]

    if len(state.retrievers) > 1:
        for retriever in state.retrievers[1:]:
            state.combined_retriever = state.combined_retriever.combine(retriever)

    state.llm = ChatOllama(model="phi3:mini", temperature=0)
    state.memory = ConversationBufferMemory(memory_key="chat history", return_messages=True)
    state.qa_chain = RetrievalQA.from_chain_type(
        llm=state.llm,
        chain_type="stuff",
        retriever=state.combined_retriever,
        input_key="query",
        return_source_documents=True
    )

# Database Initialization
def initialize_vector_stores(paths):
    embedding_function = get_embedding_function()
    vector_stores = []
    for path in paths:
        vector_stores.append(Chroma(
            persist_directory=path,
            embedding_function=embedding_function
        ))
    return vector_stores

# Header Component
def header_text():
    with me.box(
        style=me.Style(
            padding=me.Padding(top=64, bottom=36),
        )
    ):
        me.text(
            "ScoutAI Mesop Integration",
            style=me.Style(
                font_size=36,
                font_weight=700,
                background="linear-gradient(90deg, #4285F4, #AA5CDB, #DB4437) text",
                color="transparent",
            ),
        )

# Chat Input Component
def chat_input():
    state = me.state(State)
    with me.box(
        style=me.Style(
            padding=me.Padding.all(8),
            background="white",
            display="flex",
            width="100%",
            border=me.Border.all(me.BorderSide(width=0, style="solid", color="black")),
            border_radius=12,
            box_shadow="0 10px 20px #0000000a, 0 2px 6px #0000000a, 0 0 1px #0000000a",
        )
    ):
        with me.box(style=me.Style(flex_grow=1)):
            me.native_textarea(
                value=state.input,
                autosize=True,
                min_rows=4,
                placeholder="Enter your query",
                style=me.Style(
                    padding=me.Padding(top=16, left=16),
                    background="white",
                    outline="none",
                    width="100%",
                    overflow_y="auto",
                    border=me.Border.all(me.BorderSide(style="none")),
                ),
                on_blur=textarea_on_blur,
            )
        with me.content_button(type="icon", on_click=click_send):
            me.icon("send")

def textarea_on_blur(e: me.InputBlurEvent):
    state = me.state(State)
    state.input = e.value

# Send Button Click Handler
def click_send(e: me.ClickEvent):
    state = me.state(State)
    if not state.input:
        return
    state.in_progress = True
    input_text = state.input
    state.input = ""
    yield

    result = state.qa_chain({"query": input_text})
    state.output = result["result"]
    state.source_docs = result.get("source_documents", [])
    state.in_progress = False
    yield

# Output Display Component
def output_display():
    state = me.state(State)
    if state.output or state.in_progress:
        with me.box(
            style=me.Style(
                background="#F0F4F9",
                padding=me.Padding.all(16),
                border_radius=16,
                margin=me.Margin(top=36),
            )
        ):
            if state.output:
                me.markdown(state.output)
            if state.in_progress:
                with me.box(style=me.Style(margin=me.Margin(top=16))):
                    me.progress_spinner()
            if state.source_docs:
                me.text("References:")
                for doc in state.source_docs:
                    file_name = os.path.basename(doc.metadata['source'])
                    me.text(f"- {file_name}")

# Footer Component
def footer():
    with me.box(
        style=me.Style(
            position="sticky",
            bottom=0,
            padding=me.Padding.symmetric(vertical=16, horizontal=16),
            width="100%",
            background="#F0F4F9",
            font_size=14,
        )
    ):
        me.html(
            "Made with <a href='https://google.github.io/mesop/'>Mesop</a>",
        )
