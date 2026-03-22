"""
RAG tool — retrieves Punjab-specific crop/fertilizer/scheme knowledge.
Uses ChromaDB + HuggingFace embeddings (fully offline).
Rebuild index by deleting .chroma_db/ folder.
"""
import os
from pathlib import Path
from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / ".chroma_db"

_vectorstore = None


def _load_vectorstore():
    global _vectorstore
    if _vectorstore:
        return _vectorstore

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    if CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir()):
        _vectorstore = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
            collection_name="punjab_agri",
        )
    else:
        if not DATA_DIR.exists() or not any(DATA_DIR.glob("**/*.txt")):
            return None

        loader = DirectoryLoader(
            str(DATA_DIR), glob="**/*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True,
        )
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600, chunk_overlap=80,
            separators=["\n\n", "\n", ".", " "],
        )
        chunks = splitter.split_documents(docs)
        print(f"[RAG] Indexing {len(chunks)} chunks from {len(docs)} documents...")
        _vectorstore = Chroma.from_documents(
            chunks, embeddings,
            persist_directory=str(CHROMA_DIR),
            collection_name="punjab_agri",
        )
        print("[RAG] Index built.")

    return _vectorstore


@tool
def rag_tool(query: str) -> str:
    """
    Search the Punjab agriculture knowledge base for context about crops, fertilizers,
    sowing schedules, irrigation, government schemes, pest management, and farming practices.
    Call this to get local Punjab-specific context, then combine with your own knowledge to answer.
    If the knowledge base has no results, answer from your own expertise.
    """
    try:
        vs = _load_vectorstore()
        if vs is None:
            return "Knowledge base is empty. Add .txt files to the data/ directory."

        docs = vs.similarity_search(query, k=4)
        if not docs:
            return "No specific information found in the knowledge base. Answer from your own agricultural expertise about Punjab farming."

        results = []
        for i, doc in enumerate(docs, 1):
            source = Path(doc.metadata.get("source", "unknown")).name
            results.append(f"[{source}]\n{doc.page_content.strip()}")

        return "\n\n---\n\n".join(results)

    except Exception as e:
        return f"Knowledge base unavailable ({e}). Answer from your own agricultural expertise."
