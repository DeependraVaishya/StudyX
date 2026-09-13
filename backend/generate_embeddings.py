from pymongo import MongoClient
from sentence_transformers import SentenceTransformer


# MongoDB
client = MongoClient("mongodb://127.0.0.1:27017/")
db = client["studyx"]

chunks_collection = db["material_chunks"]


# Embedding Model
model = SentenceTransformer("all-MiniLM-L6-v2")


print("Embedding model loaded...")


# Saare chunks
chunks = chunks_collection.find({
    "embedding": {"$exists": False}
})


count = 0


for chunk in chunks:

    text = chunk["text"]

    # Text ko vector mein convert
    embedding = model.encode(text).tolist()

    # MongoDB mein save
    chunks_collection.update_one(
        {
            "_id": chunk["_id"]
        },
        {
            "$set": {
                "embedding": embedding,
                "embedding_model": "all-MiniLM-L6-v2"
            }
        }
    )

    count += 1

    print(
        f"Embedded chunk {count}: "
        f"{chunk['filename']} "
        f"(chunk {chunk['chunk_index']})"
    )


print()
print(f"Done! {count} chunks embedded successfully.")