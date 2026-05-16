# backend/seed_knowledge.py
# -------------------------------------------------------
# One-time script to seed the marketing knowledge base
# into ChromaDB.
#
# Run this ONCE from the backend/ folder:
#   python seed_knowledge.py
#
# What it does:
#   1. Reads knowledge/marketing_knowledge.md
#   2. Splits it into chunks using ## headers as boundaries
#   3. Embeds each chunk with OpenAI text-embedding-3-small
#   4. Stores everything in ChromaDB collection "marketing_knowledge"
#
# Re-run it any time you update the .md file.
# It deletes and recreates the collection each time
# so you never get duplicate or stale chunks.
# -------------------------------------------------------

import os
import sys
import chromadb

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter

from config import OPENAI_API_KEY


# -------------------------------------------------------
# PATHS — both relative to backend/ folder
# -------------------------------------------------------

# Same ChromaDB folder your pipeline.py already uses
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

# Knowledge files live in backend/knowledge/
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

# Collection name in ChromaDB
COLLECTION_NAME = "marketing_knowledge"


# -------------------------------------------------------
# HELPER — load and validate a .md file
# -------------------------------------------------------
def load_markdown_file(filename: str) -> str:
    filepath = os.path.join(KNOWLEDGE_DIR, filename)
    print(f"[seed] Loading file: {filepath}")

    if not os.path.exists(filepath):
        print(f"[seed] ❌ File not found: {filepath}")
        print(f"[seed] Make sure the file exists at backend/knowledge/{filename}")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        print(f"[seed] ❌ File is empty: {filepath}")
        sys.exit(1)

    print(f"[seed] ✅ File loaded: {len(content)} characters")
    return content


# -------------------------------------------------------
# HELPER — split markdown into chunks by ## headers
#
# MarkdownHeaderTextSplitter splits at header boundaries.
# Each chunk gets metadata: {"Header 1": "...", "Header 2": "..."}
# This means when the agent retrieves a chunk, it also
# knows which section it came from — useful for debugging
# and for future filtering.
#
# Example output chunk:
#   content:  "Send the night before release at 18:00..."
#   metadata: {"Header 2": "Radio Submission — Full Protocol"}
# -------------------------------------------------------
def split_markdown(content: str) -> list:
    print(f"[seed] Splitting markdown by headers...")

    # Split on both H1 (#) and H2 (##) headers
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
    ]

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,  # Keep the header text inside the chunk content
    )

    chunks = splitter.split_text(content)

    # Filter out empty or very short chunks (e.g. the title block)
    chunks = [c for c in chunks if len(c.page_content.strip()) > 50]

    print(f"[seed] Created {len(chunks)} chunks after filtering")

    # Print a preview of each chunk so you can verify the split
    for i, chunk in enumerate(chunks):
        header = chunk.metadata.get("Header 2") or chunk.metadata.get("Header 1") or "No header"
        preview = chunk.page_content[:80].replace("\n", " ")
        print(f"[seed]   Chunk {i+1:02d} | {header[:40]:<40} | {preview}...")

    return chunks


# -------------------------------------------------------
# MAIN — seed one knowledge file into ChromaDB
# -------------------------------------------------------
def seed_knowledge_file(filename: str, collection_name: str):
    print(f"\n[seed] ══════════════════════════════════════")
    print(f"[seed] Seeding: {filename} → {collection_name}")
    print(f"[seed] ══════════════════════════════════════\n")

    # Step 1: Load the markdown file
    content = load_markdown_file(filename)

    # Step 2: Split into chunks
    chunks = split_markdown(content)

    if not chunks:
        print(f"[seed] ❌ No chunks created. Check the markdown formatting.")
        sys.exit(1)

    # Step 3: Extract text and metadata separately for ChromaDB
    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    # Step 4: Set up OpenAI embeddings
    # Same model as pipeline.py — consistency matters
    print(f"\n[seed] Initialising OpenAI embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    # Step 5: Connect to ChromaDB and delete existing collection
    # This prevents duplicate chunks if you re-run after updating the .md
    print(f"[seed] Connecting to ChromaDB at: {CHROMA_DB_PATH}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    existing = [c.name for c in chroma_client.list_collections()]
    if collection_name in existing:
        print(f"[seed] Collection '{collection_name}' exists — deleting and recreating...")
        chroma_client.delete_collection(name=collection_name)
    else:
        print(f"[seed] Collection '{collection_name}' does not exist — creating fresh...")

    # Step 6: Embed and store
    print(f"[seed] Embedding {len(texts)} chunks and storing in ChromaDB...")
    print(f"[seed] This takes about 10-20 seconds...")

    vector_store = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        collection_name=collection_name,
        persist_directory=CHROMA_DB_PATH,
    )

    print(f"\n[seed] ✅ Done! {len(texts)} chunks stored in '{collection_name}'")
    return len(texts)


# -------------------------------------------------------
# VERIFICATION — do a quick test search after seeding
# Confirms the collection is queryable before you wire
# it into the agent
# -------------------------------------------------------
def verify_collection(collection_name: str):
    print(f"\n[seed] ── Verification search ──")
    print(f"[seed] Running test query: 'when should I send radio emails?'")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )

    results = vector_store.similarity_search(
        query="when should I send radio emails?",
        k=2
    )

    if not results:
        print(f"[seed] ❌ Verification failed — no results returned")
        return

    print(f"[seed] ✅ Verification passed — {len(results)} results returned")
    for i, doc in enumerate(results):
        header = doc.metadata.get("Header 2") or doc.metadata.get("Header 1") or "No header"
        preview = doc.page_content[:120].replace("\n", " ")
        print(f"\n[seed]   Result {i+1}: [{header}]")
        print(f"[seed]   {preview}...")


# -------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------
if __name__ == "__main__":
    print("\n🌱 Music AI — Knowledge Base Seeder")
    print("=====================================\n")

    # Seed marketing knowledge
    # To add more files later:
    #   seed_knowledge_file("platform_tutorials.md", "platform_tutorials")
    #   seed_knowledge_file("media_contacts.md", "media_contacts")

    chunks_created = seed_knowledge_file(
        filename="marketing_knowledge.md",
        collection_name=COLLECTION_NAME,
    )

    # Run a quick verification search
    verify_collection(COLLECTION_NAME)

    print(f"\n✅ Seeding complete!")
    print(f"   Collection : {COLLECTION_NAME}")
    print(f"   Chunks     : {chunks_created}")
    print(f"   ChromaDB   : {CHROMA_DB_PATH}")
    print(f"\nNext step: add search_marketing_knowledge tool to agent.py")
    print(f"Then test with: 'when should I send radio emails?'\n")
