from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from astrapy import DataAPIClient
from langchain_astradb import AstraDBVectorStore
import os
import pandas as pd
from dotenv import load_dotenv
import json

# ------------------------------ CHECK THIS BEFORE RUNNING BOT -----------------------------------------
addMore = False #Change to True if want to add more data to collection
collection_name = "chatHistory"

# load csv
# df = pd.read_csv("CSV files\\realistic_restaurant_reviews.csv")

# declare embedding model
embeddings = OllamaEmbeddings(model="mxbai-embed-large:latest")

# load .ENV
load_dotenv()
astraDB_token = os.getenv("ASTRADB_TOKEN")
astraDB_endpoint = os.getenv("ASTRADB_END_POINT")

# Initialize client --------------------------------------------------------------------------
try:
    client = DataAPIClient(astraDB_token)
    print("Client connected")
except Exception as e:
    print(f"Client failed to connect: {e}")
try:
    db = client.get_database(astraDB_endpoint)
    print("db connected")
except Exception as e:
    print(f"db failed to connect: {e}")


# Attempt to list collections as a connectivity check------------------------------------------
try:
    collections = db.list_collection_names()
    print("Successfully connected! Collections found:", collections)
except Exception as e:
    print(f"Connection failed: {e}")


# Connect or Build collection---------------------------------------------------------------------
vector_store = AstraDBVectorStore(
    collection_name=collection_name,
    embedding=embeddings,
    api_endpoint=astraDB_endpoint,
    token=astraDB_token,     
)
print(f"Collection Connected : {collection_name} ")


# prepare data to vectorise (can be customized)-------------------------------------------------
documents = []
ids = []
i=0
try:
    while True:
        with open(f"json\\document{i}.json", "r") as f:       #DID NOT WORK!!
            document = json.load(f) # load (data type dict)
            doc = Document( # Reconstruck to Document
                page_content=document["page_content"],
                metadata=document["metadata"]
            )
            ids.append(str(i))
            documents.append(doc)
            i+=1
        # document = Document(
        #     page_content=row["Title"]+" "+row["Review"],
        #     metadata={"Date":row["Date"],
        #               "Rating":row["Rating"]},
        #     id=str(i)
        # )
except:
    print("Data preparation complete")


# Insert a documents -------------------------------------------------------------------------
if (addMore == True):
    vector_store.add_documents(documents=documents, ids=ids)


try:
    # Perform Vector retrieval
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={'k':5}
    )
except Exception as e:
    print(f"Failed to connect to collection: {e}")
    retriever = None




