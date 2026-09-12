# backend/seed_knowledge.py
# -------------------------------------------------------
# Script to seed marketing knowledge files into Pinecone.
#
# Run from the backend/ folder:
#   python seed_knowledge.py
#
# What it does:
# 1. Reads one or more knowledge/*.md files
# 2. Splits each into chunks using "##" headers as boundaries
# 3. If a chunk has a metadata comment block like:
#      <!--
#      chunk_type: strategy
#      genre: indie
#      -->
#    that block is parsed into real Pinecone metadata and stripped
#    from the text before embedding. Chunks with a metadata block
#    are also automatically protected from length-based re-splitting,
#    same as the existing "template/formula" protection below.
# 4. Embeds each chunk with OpenAI text-embedding-3-small
# 5. Stores everything in Pinecone under namespace "marketing_knowledge"
#
# IMPORTANT — deletion is now scoped per source file, not per namespace.
# Re-seeding one file (e.g. the Concert file) only deletes and replaces
# that file's own vectors — it never touches another file's vectors in
# the same shared namespace. This replaces the old behavior, which
# deleted the ENTIRE namespace on every run — safe only when a single
# file shared the namespace, unsafe now that multiple files do.
#
# Standing format rule for any future project-type knowledge file:
# use "##" only for chunk boundaries, never "###". Sub-structure inside
# a chunk should be bold text/bullets, not a header. This lets one
# splitting pipeline handle every file without special-casing.
# -------------------------------------------------------

import os
import re
import sys

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from config import OPENAI_API_KEY
from pipeline import get_pinecone_index

# -------------------------------------------------------
# PATHS — both relative to backend/ folder
# -------------------------------------------------------
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "music-ai-chat")
NAMESPACE = "marketing_knowledge"

# -------------------------------------------------------
# SOURCES TO SEED — add new project-type files here.
# source_key must be unique across all sources: it prefixes each
# chunk's Pinecone ID, which is what makes per-source deletion safe.
# -------------------------------------------------------
SOURCES = [
    {"filename": "marketing_knowledge.md", "source_key": "marketing_dist"},
    {"filename": "marketing_knowledge_concert.md", "source_key": "concert"},
]

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
# HELPER — parse a chunk's metadata comment block, if present
# -------------------------------------------------------
def parse_chunk_metadata(text: str) -> tuple:
    """
    Looks for a metadata comment block like:
        <!--
        chunk_type: strategy
        genre: indie
        artist_size: mid,established
        -->
    Returns (clean_text, metadata_dict):
      - clean_text: original text with the comment block removed
      - metadata_dict: parsed key/value pairs. Comma-separated values
        become a list of strings (Pinecone supports string-list metadata,
        needed later for $in-style filtering). Single values stay plain
        strings. Returns ({}, text unchanged) if no comment block found.
    """
    try:
        match = re.search(r"<!--(.*?)-->", text, re.DOTALL)
        if not match:
            return text, {}

        metadata = {}
        for line in match.group(1).strip().splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            values = [v.strip() for v in value.split(",") if v.strip()]
            if values:
                metadata[key] = values if len(values) > 1 else values[0]

        clean_text = (text[:match.start()] + text[match.end():]).strip()
        return clean_text, metadata

    except Exception as e:
        print(f"[seed] ⚠️  Could not parse metadata block, keeping chunk as plain text: {e}")
        return text, {}

# -------------------------------------------------------
# HELPER — split markdown into chunks by ## headers
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

    # Tuned for dense music distribution rules — flexible enough for templates
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=150,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    final_chunks = []
    for chunk in chunks:
        content_lower = chunk.page_content.lower()

        # PROTECTION: if the chunk contains a template, formula, layout,
        # OR a metadata comment block (our structured-chunk convention),
        # do NOT split it even if it exceeds 600 characters. A metadata
        # block signals a deliberately whole, single-retrieval unit.
        is_protected = (
            any(w in content_lower for w in ["template", "layout:", "formula", "option "])
            or "<!--" in chunk.page_content
        )

        if is_protected:
            final_chunks.append(chunk)
        elif len(chunk.page_content) > 700:
            split_chunks = recursive_splitter.split_documents([chunk])
            final_chunks.extend(split_chunks)
        else:
            final_chunks.append(chunk)

    # Filter out empty or very short chunks (e.g. the title block)
    chunks = [c for c in final_chunks if len(c.page_content.strip()) > 50]

    print(f"[seed] Created {len(chunks)} chunks after filtering")
    for i, chunk in enumerate(chunks):
        header = chunk.metadata.get("section") or chunk.metadata.get("subsection") or "No header"
        preview = chunk.page_content[:80].replace("\n", " ")
        print(f"[seed] Chunk {i+1:02d} | {header[:40]:<40} | {preview}...")

    return chunks

# -------------------------------------------------------
# HELPER — delete only this source's own vectors, not the whole namespace
# -------------------------------------------------------
def delete_source_vectors(index, namespace: str, source_key: str):
    prefix = f"{source_key}_"
    print(f"[seed] Clearing existing vectors for source '{source_key}' (prefix '{prefix}')...")

    try:
        ids_to_delete = []
        for id_batch in index.list(prefix=prefix, namespace=namespace):
            ids_to_delete.extend(id_batch)

        if ids_to_delete:
            index.delete(ids=ids_to_delete, namespace=namespace)
            print(f"[seed] Cleared {len(ids_to_delete)} existing vectors for '{source_key}'.")
        else:
            print(f"[seed] No existing vectors found for '{source_key}' — nothing to clear.")

    except Exception as e:
        print(f"[seed] ⚠️  Could not list/delete existing vectors for '{source_key}': {e}")
        print(f"[seed] Proceeding anyway — new vectors will overwrite matching IDs, "
              f"but stale extra IDs from a shrinking file won't be removed this run.")

# -------------------------------------------------------
# MAIN — seed one knowledge file into Pinecone
# -------------------------------------------------------
def seed_knowledge_file(filename: str, namespace: str, source_key: str):
    print(f"\n[seed] ══════════════════════════════════════")
    print(f"[seed] Seeding: {filename} → namespace '{namespace}' (source '{source_key}')")
    print(f"[seed] ══════════════════════════════════════\n")

    # Step 1: Load the markdown file
    content = load_markdown_file(filename)

    # Step 2: Split into chunks
    chunks = split_markdown(content)
    if not chunks:
        print(f"[seed] ❌ No chunks created. Check the markdown formatting.")
        sys.exit(1)

    # Step 3: Extract text + metadata (including parsed comment-block metadata)
    texts = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        clean_text, extra_meta = parse_chunk_metadata(chunk.page_content)
        texts.append(clean_text)

        content_str = clean_text.lower()
        content_type = "general_strategy"
        if any(w in content_str for w in ["day", "window", "timeline", "weeks"]):
            content_type = "distribution_rule"
        elif any(w in content_str for w in ["isrc", "upc", "metadata", "rights"]):
            content_type = "technical_metadata"

        meta = {
            "section": chunk.metadata.get("section", "general"),
            "subsection": chunk.metadata.get("subsection", "general"),
            "source": source_key,
            "chunk_index": i,
            "content_type": content_type,
        }
        meta.update(extra_meta)  # chunk_type, genre, artist_size, budget, goal, city_type, phase, etc.
        metadatas.append(meta)

    # Step 4: Set up OpenAI embeddings
    print(f"\n[seed] Initialising OpenAI embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    # Step 5: Clear only this source's existing vectors (not the whole namespace)
    index = get_pinecone_index()
    delete_source_vectors(index, namespace, source_key)

    # Step 6: Embed and store in Pinecone
    print(f"[seed] Embedding {len(texts)} chunks and storing in Pinecone...")
    print(f"[seed] This takes about 10-20 seconds...")

    vector_store = PineconeVectorStore(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=namespace,
    )

    ids = [f"{source_key}_{i}" for i in range(len(texts))]

    vector_store.add_texts(
        texts=texts,
        metadatas=metadatas,
        ids=ids,
    )

    print(f"\n[seed] ✅ Done! {len(texts)} chunks stored in namespace '{namespace}' under source '{source_key}'")
    return len(texts)

# -------------------------------------------------------
# VERIFICATION — quick test search after seeding
# -------------------------------------------------------
def verify_collection(namespace: str, query: str):
    print(f"\n[seed] ── Verification search ──")
    print(f"[seed] Running test query: '{query}'")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

    vector_store = PineconeVectorStore(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=namespace,
    )

    results = vector_store.similarity_search(query=query, k=2)

    if not results:
        print(f"[seed] ❌ Verification failed — no results returned")
        return

    print(f"[seed] ✅ Verification passed — {len(results)} results returned")
    for i, doc in enumerate(results):
        header = doc.metadata.get("section") or doc.metadata.get("subsection") or "No header"
        preview = doc.page_content[:120].replace("\n", " ")
        print(f"\n[seed] Result {i+1}: [{header}]")
        print(f"[seed] metadata: {doc.metadata}")
        print(f"[seed] {preview}...")

# -------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------
if __name__ == "__main__":
    print("\n🌱 Music AI — Knowledge Base Seeder")
    print("=====================================\n")

    total_chunks = 0
    for source in SOURCES:
        total_chunks += seed_knowledge_file(
            filename=source["filename"],
            namespace=NAMESPACE,
            source_key=source["source_key"],
        )

    verify_collection(NAMESPACE, query="when should I send radio emails?")
    verify_collection(NAMESPACE, query="FOMO ticket rollout for an indie band")

    print(f"\n✅ Seeding complete!")
    print(f"   Namespace     : {NAMESPACE}")
    print(f"   Total chunks  : {total_chunks}")
    print(f"   Pinecone      : {PINECONE_INDEX_NAME}")
    print(f"\nNext step: run the app and test with a concert-related question.\n")