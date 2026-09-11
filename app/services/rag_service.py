"""
RAG Service — chunks.jsonl (data/chunks.jsonl) ko embeddings bana kar
ChromaDB (vector database) mein store karta hai, aur retrieval provide
karta hai.

IMPORTANT: Ye service data/chunks.jsonl se data leta hai — jo hamari
image-scraping pipeline (bulk_download.py -> organize_papers.py ->
extract_all.py -> chunk_papers.py) ka output hai. Ye ab
data/processed/*.json (ocr_service.py, jo PDFs ke liye tha) use NAHI karti,
kyunke humare past papers PDFs nahi, scraped images hain, aur chunk_papers.py
already question-level chunking kar chuki hai.

Usage:
    python rag_service.py  # populates the vector DB from data/chunks.jsonl

Fir query karne ke liye retrieve_relevant_chunks() function use karein.
"""

import os
import json
import chromadb
from chromadb.utils import embedding_functions

# Free, local embedding model — koi API cost nahi
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "past_papers"
CHUNKS_FILE = "data/chunks.jsonl"

# Which board this data came from — hardcoded since Phase 0 only scraped
# Lahore Board (per spec's "pick ONE board" guidance for MVP).
BOARD = "lahore"


def get_collection():
    """ChromaDB collection banata ya existing return karta hai."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )
    return collection


def normalize_grade(grade: str) -> str:
    """
    API se aane wale grade values ("9", "10", "fsc1", "fsc2", "ics1", "ics2",
    "11", "12", "9th", ...) ko us format mein convert karta hai jo
    chunk_papers.py ne store kiya tha: "9th", "10th", "11th", "12th".

    FSc Part 1 aur ICS Part 1 dono "11th" class ke papers use karte hain
    (Physics/Chem/Math/Bio/CS/English/Urdu/Islamiat sab 11th ke papers
    hain — FSc/ICS sirf subject-selection mein farq dalte hain, past-paper
    content mein nahi). Isi tarah Part 2 -> "12th".
    """
    g = grade.strip().lower()
    mapping = {
        "9": "9th", "9th": "9th",
        "10": "10th", "10th": "10th",
        "11": "11th", "11th": "11th", "fsc1": "11th", "ics1": "11th",
        "12": "12th", "12th": "12th", "fsc2": "12th", "ics2": "12th",
    }
    return mapping.get(g, g)


def normalize_subject(subject: str) -> str:
    """API se aane wale subject naam ko folder-naming se match karta hai
    (jaise 'Computer Science' -> 'computer-science')."""
    return subject.strip().lower().replace("_", "-").replace(" ", "-")


def populate_vector_db():
    """
    data/chunks.jsonl (chunk_papers.py ka output) padhta hai aur har
    chunk ko uske metadata (grade, subject, year, group, medium, type)
    ke sath vector DB mein daalta hai.
    """
    if not os.path.exists(CHUNKS_FILE):
        print(f"File not found: {CHUNKS_FILE}")
        print("Pehle chunk_papers.py chalayein (jo extract_all.py ke baad chalti hai).")
        return

    collection = get_collection()

    total_chunks = 0
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            chunk = json.loads(line)
            text = chunk.get("text", "")
            if not text:
                continue

            collection.add(
                documents=[text],
                metadatas=[{
                    "source": chunk.get("source_filename", "unknown"),
                    "year": chunk.get("year", "unknown"),
                    "grade": normalize_grade(chunk.get("grade", "unknown")),
                    "subject": normalize_subject(chunk.get("subject", "unknown")),
                    "group": chunk.get("group", "unknown"),
                    "medium": chunk.get("medium", "unknown"),
                    "type": chunk.get("type", "unknown"),
                    "board": BOARD,
                }],
                ids=[chunk.get("chunk_id", f"chunk_{total_chunks}")],
            )
            total_chunks += 1

            if total_chunks % 500 == 0:
                print(f"  {total_chunks} chunks added so far...")

    print(f"\nVector DB mein {total_chunks} chunks add ho gaye.")


def retrieve_relevant_chunks(query: str, grade: str, subject: str, n_results: int = 5) -> list:
    """
    Student ke question ke liye sabse relevant past-paper chunks nikalta hai,
    grade aur subject se filter karke.

    Returns: list of {"text", "source", "year", "group", "medium", "type"}
    """
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where={"$and": [
            {"grade": normalize_grade(grade)},
            {"subject": normalize_subject(subject)},
        ]},
    )

    chunks = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    for doc, meta in zip(docs, metas):
        chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "year": meta.get("year", "unknown"),
            "group": meta.get("group", "unknown"),
            "medium": meta.get("medium", "unknown"),
            "type": meta.get("type", "unknown"),
        })
    return chunks


if __name__ == "__main__":
    populate_vector_db()