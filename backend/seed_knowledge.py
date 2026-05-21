# backend/seed_knowledge.py
# -------------------------------------------------------
# One-time script to seed the marketing knowledge base
# into Pinecone.
#
# Run this ONCE from the backend/ folder:
#   python seed_knowledge.py
#
# What it does:
#   1. Reads knowledge/marketing_knowledge.md
#   2. Splits it into chunks using ## headers as boundaries
#   3. Embeds each chunk with OpenAI text-embedding-3-small
#   4. Stores everything in Pinecone under namespace "marketing_knowledge"
#
# Re-run it any time you update the .md file.
# It deletes and recreates the namespace each time
# so you never get duplicate or stale chunks.
# -------------------------------------------------------

import os
import sys

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter

from config import OPENAI_API_KEY
from pipeline import get_pinecone_index


# -------------------------------------------------------
# PATHS — both relative to backend/ folder
# -------------------------------------------------------

# Knowledge files live in backend/knowledge/
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

# Pinecone config
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")

# Namespace in Pinecone
NAMESPACE = "marketing_knowledge"


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
# -------------------------------------------------------
def split_markdown(content: str) -> list:
    print(f"[seed] Splitting markdown by headers...")

    headers_to_split_on = [
    ("##", "section"),
    ("###", "subsection"),
]

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    chunks = splitter.split_text(content)

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Tuned for dense music distribution rules to prevent semantic dilution
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    final_chunks = []

    for chunk in chunks:
        # Lowered threshold to guarantee clean chunks matching the 600 limit
        if len(chunk.page_content) > 600:
            split_chunks = recursive_splitter.split_documents([chunk])
            final_chunks.extend(split_chunks)
        else:
            final_chunks.append(chunk)

    chunks = final_chunks

   from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Tuned for dense music rules but flexible enough for templates
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    final_chunks = []

    for chunk in chunks:
        content = chunk.page_content.lower()
        
        # PROTECTION LAW: If the chunk contains a template, formula, or layout, 
        # DO NOT split it even if it exceeds 600 characters.
        if any(w in content for w in ["template", "layout:", "formula", "option "]):
            final_chunks.append(chunk)
        # Otherwise, if it's normal text and too long, split it cleanly
        elif len(chunk.page_content) > 700:
            split_chunks = recursive_splitter.split_documents([chunk])
            final_chunks.extend(split_chunks)
        else:
            final_chunks.append(chunk)

    chunks = final_chunks 
    # Filter out empty or very short chunks (e.g. the title block)
    chunks = [c for c in chunks if len(c.page_content.strip()) > 50]

    print(f"[seed] Created {len(chunks)} chunks after filtering")

    for i, chunk in enumerate(chunks):
        header = chunk.metadata.get("Header 2") or chunk.metadata.get("Header 1") or "No header"
        preview = chunk.page_content[:80].replace("\n", " ")
        print(f"[seed]   Chunk {i+1:02d} | {header[:40]:<40} | {preview}...")

    return chunks


# -------------------------------------------------------
# MAIN — seed one knowledge file into Pinecone
# -------------------------------------------------------
def seed_knowledge_file(filename: str, namespace: str):
    print(f"\n[seed] ══════════════════════════════════════")
    print(f"[seed] Seeding: {filename} → namespace '{namespace}'")
    print(f"[seed] ══════════════════════════════════════\n")

    # Step 1: Load the markdown file
    content = load_markdown_file(filename)

    # Step 2: Split into chunks
    chunks = split_markdown(content)

    if not chunks:
        print(f"[seed] ❌ No chunks created. Check the markdown formatting.")
        sys.exit(1)

    # Step 3: Extract text and metadata separately
    texts = [chunk.page_content for chunk in chunks]
    
    metadatas = []

    for i, chunk in enumerate(chunks):
        # Extract keywords for dynamic agent routing via metadata filters
        content_str = chunk.page_content.lower()
        content_type = "general_strategy"
        if any(w in content_str for w in ["day", "window", "timeline", "weeks"]):
            content_type = "distribution_rule"
        elif any(w in content_str for w in ["isrc", "upc", "metadata", "rights"]):
            content_type = "technical_metadata"

        metadatas.append({
            "section": chunk.metadata.get("section", "general"),
            "subsection": chunk.metadata.get("subsection", "general"),
            "source": "marketing_knowledge",
            "chunk_index": i,
            "content_type": content_type
        })

    # Step 4: Set up OpenAI embeddings
    print(f"\n[seed] Initialising OpenAI embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    # Step 5: Clear existing vectors for this namespace
    print(f"[seed] Clearing existing vectors in namespace '{namespace}'...")
    index = get_pinecone_index()
    try:
        index.delete(delete_all=True, namespace=namespace)
        print(f"[seed] Existing vectors cleared.")
    except Exception:
        print(f"[seed] Namespace did not exist yet — creating fresh.")

    # Step 6: Embed and store in Pinecone
    print(f"[seed] Embedding {len(texts)} chunks and storing in Pinecone...")
    print(f"[seed] This takes about 10-20 seconds...")

    vector_store = PineconeVectorStore(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=namespace,
    )

    # Prefixed to avoid ID collisions if other marketing vectors are added later
    ids = [f"marketing_dist_{i}" for i in range(len(texts))]

    vector_store.add_texts(
    texts=texts,
    metadatas=metadatas,
    ids=ids,
    )

    print(f"\n[seed] ✅ Done! {len(texts)} chunks stored in namespace '{namespace}'")
    return len(texts)


# -------------------------------------------------------
# VERIFICATION — do a quick test search after seeding
# -------------------------------------------------------
def verify_collection(namespace: str):
    print(f"\n[seed] ── Verification search ──")
    print(f"[seed] Running test query: 'when should I send radio emails?'")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    vector_store = PineconeVectorStore(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=namespace,
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
        namespace=NAMESPACE,
    )

    # Run a quick verification search
    verify_collection(NAMESPACE)

    print(f"\n✅ Seeding complete!")
    print(f"   Namespace  : {NAMESPACE}")
    print(f"   Chunks     : {chunks_created}")
    print(f"   Pinecone   : {PINECONE_INDEX_NAME}")
    print(f"\nNext step: run the app and test with: 'when should I send radio emails?'\n")
