from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from astrapy import DataAPIClient
from astrapy.constants import VectorMetric
from langchain_astradb import AstraDBVectorStore
import os
import pandas as pd
from dotenv import load_dotenv


collection_name = "restaurant_reviews"

# load csv
df = pd.read_csv("realistic_restaurant_reviews.csv")
embeddings = OllamaEmbeddings(model="mxbai-embed-large:latest")

# load .ENV
load_dotenv()
astraDB_token = os.getenv("ASTRADB_TOKEN")
astraDB_endpoint = os.getenv("ASTRADB_END_POINT")

# Initialize client
client = DataAPIClient(astraDB_token)
db = client.get_database(astraDB_endpoint)

# Verify connection
try:
    info = db.info.name
    print(f"Connected to database: {info}")
except Exception as e:
    print(f"Database not found or connection failed: {e}")

# prepare data to vectorise
documents = []
ids = []
for i,row in df.iterrows():
    document = Document(
        page_content=row["Title"]+" "+row["Review"],
        metadata={"Date":row["Date"],
                  "Rating":row["Rating"]},
        id=str(i)
    )
    ids.append(str(i))
    documents.append(document)

# Verify if the collection exist of not
if collection_name not in db.list_collection_names():
    # Create Collection
    vector_store = AstraDBVectorStore(
        collection_name=collection_name,
        embedding=embeddings,
        api_endpoint=astraDB_endpoint,
        token=astraDB_token,     
    )
    print("collection build successfully")

    # Insert a documents
    vector_store.add_documents(documents=documents, ids=ids)


# Perform Vector retrieval
retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={'k':5}
)




