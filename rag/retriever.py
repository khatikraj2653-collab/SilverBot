import os
import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@st.cache_resource(show_spinner=False)
def _build_vectorstore():
    """Builds the FAISS vectorstore from the silver causal chain doc.
    Cached across reruns so embeddings + index load only once per server."""
    doc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silver_causal_chain.md")
    with open(doc_path, "r", encoding="utf-8") as f:
        text = f.read()

    headers_to_split_on = [("##", "section")]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = splitter.split_text(text)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return FAISS.from_documents(chunks, embeddings)


def retrieve_factor_context(query: str, k: int = 2) -> str:
    try:
        vectorstore = _build_vectorstore()
        retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": k, "fetch_k": 6})
        docs = retriever.invoke(query)
        return "\n".join([d.page_content for d in docs])
    except Exception as e:
        return f"RAG context unavailable ({str(e)})"