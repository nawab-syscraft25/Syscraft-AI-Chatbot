from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import ServerlessSpec
import textwrap
import os

# Load MiniLM embedding model
embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Pinecone init (v5 SDK)
pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "company-descriptions"
DIM = 384  # MiniLM embeddings have 384 dimensions

# Create index if it does not exist
if INDEX_NAME not in [index.name for index in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIM,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",      # or "gcp"
            region="us-east-1"   # must match your project
        )
    )

index = pc.Index(INDEX_NAME)

from langchain.text_splitter import RecursiveCharacterTextSplitter

def update_company_vectors(description: str, company_id="default_company"):
    """Update company description vectors in Pinecone using MiniLM + RecursiveCharacterTextSplitter"""
    try:
        index.delete(filter={"company_id": company_id})
        print(f"🗑️ Old vectors deleted for {company_id}")
    except Exception as e:
        if "Namespace not found" in str(e) or "404" in str(e):
            print(f"No old vectors to delete for {company_id}")
        else:
            print(f"⚠️ Unexpected error while deleting old vectors: {e}")

    # Use RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,   # small overlap to preserve context
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = splitter.split_text(description)

    vectors = []
    for i, chunk in enumerate(chunks):
        embedding = embedder.encode(chunk).tolist()
        vectors.append({
            "id": f"{company_id}_{i}",
            "values": embedding,
            "metadata": {"company_id": company_id, "text": chunk}
        })

    index.upsert(vectors)
    print(f"✅ Company vectors updated for {company_id}")


def search_company_info(query: str, company_id="default_company", top_k=5):
    query_embedding = embedder.encode(query).tolist()
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        filter={"company_id": company_id},
        include_metadata=True
    )
    return results

# result = search_company_info("What syscraft do")
# print(result)