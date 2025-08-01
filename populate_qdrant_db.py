from qdrant_client import QdrantClient
from openai import OpenAI
from dotenv import load_dotenv
from utils import add_text, generate_transaction, parse_email
import random
import uuid
import pandas as pd

load_dotenv()

client = OpenAI()
qdrant = QdrantClient("http://localhost:6333")

# Create collection if not exists
collection_name = "documents_and_transactions"

qdrant.delete_collection(collection_name=collection_name)

if not qdrant.collection_exists(collection_name):
    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config={"size": 3072, "distance": "Cosine"},  # adjust to your embedding size
    )


# Add bribery policy doc to Qdrant
add_text("bribery_policy_doc.txt", client, qdrant, collection_name, type="document")
add_text("bribery_def_doc.txt", client, qdrant, collection_name, type="document")

# Generate and add to Qdrant
for _ in range(100):
    transaction = generate_transaction()
    text = f"{transaction['sender']} paid {transaction['receiver']} ${transaction['amount']} for {transaction['description']}"

    embedding = client.embeddings.create(input=[text], model="text-embedding-3-large").data[0].embedding

    qdrant.upsert(
        collection_name=collection_name,
        points=[
            {
                "id": str(uuid.uuid4()),
                "vector": embedding,
                "payload": {"type": "transaction", **transaction, "text": text},
            }
        ],
    )

# Add 5 suspicious transactions to Qdrant
for _ in range(5):
    transaction = generate_transaction(
        senders=["Charlie"], receivers=["Maxwell"], label="suspicious", amount_range=(10000, 50000)
    )
    text = f"{transaction['sender']} paid {transaction['receiver']} ${transaction['amount']} for {transaction['description']}"

    embedding = client.embeddings.create(input=[text], model="text-embedding-3-large").data[0].embedding

    qdrant.upsert(
        collection_name=collection_name,
        points=[
            {
                "id": str(uuid.uuid4()),
                "vector": embedding,
                "payload": {"type": "transaction", **transaction, "text": text},
            }
        ],
    )

# Add emails to qdrant
all_emails = pd.read_csv("personal_financial_all_nohit_100.csv")

for row_idx, row in all_emails.iterrows():
    email = row["message"]
    email_data = parse_email(email)  # Parse the email content

    embedding = client.embeddings.create(input=email, model="text-embedding-3-large").data[0].embedding
    qdrant.upsert(
        collection_name=collection_name,
        points=[
            {
                "id": str(uuid.uuid4()),
                "vector": embedding,
                "payload": {
                    "type": "email",
                    "text": email_data["body"],
                    "sender": email_data["sender"],
                    "receiver": email_data["receiver"],
                    "subject": email_data["subject"],
                    "timestamp": email_data["timestamp"],
                },
            }
        ],
    )

# Add bribery emails to Qdrant
add_text("bribery_email_1.txt", client, qdrant, collection_name, type="email", kwargs={"sender": "Maxwell", "receiver": "Charlie"})
add_text("bribery_email_2.txt", client, qdrant, collection_name, type="email", kwargs={"sender": "Charlie", "receiver": "Maxwell"})
