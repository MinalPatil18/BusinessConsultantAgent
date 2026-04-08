import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -----------------------------
# LOAD ALL FILES FROM /data
# -----------------------------
texts = []

data_path = "data"

for file in os.listdir(data_path):
    if file.endswith(".txt"):
        with open(os.path.join(data_path, file), "r", encoding="utf-8") as f:
            texts.append(f.read())

# Merge all content
full_text = "\n\n".join(texts)

# -----------------------------
# SMART CHUNKING
# -----------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

docs = text_splitter.create_documents([full_text])

# -----------------------------
# EMBEDDINGS
# -----------------------------
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# -----------------------------
# VECTOR STORE
# -----------------------------
db = FAISS.from_documents(docs, embedding)
db.save_local("vector_store")

print("✅ Vector DB created from multiple files!")