# database/models.py
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017"
DB_NAME   = "electricity_tracker"

def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def init_db():
    db = get_db()

    # electricity_prices collection
    try:
        db.create_collection("electricity_prices")
    except CollectionInvalid:
        pass
    db.electricity_prices.create_index(
        [("country", ASCENDING), ("timestamp", DESCENDING)],
        unique=True,
        name="idx_prices_country_ts"
    )
    db.electricity_prices.create_index(
        [("timestamp", DESCENDING)],
        name="idx_prices_ts"
    )

    # generation_mix collection
    try:
        db.create_collection("generation_mix")
    except CollectionInvalid:
        pass
    db.generation_mix.create_index(
        [("country", ASCENDING), ("timestamp", DESCENDING)],
        unique=True,
        name="idx_gen_country_ts"
    )

    # electricity_load collection
    try:
        db.create_collection("electricity_load")
    except CollectionInvalid:
        pass
    db.electricity_load.create_index(
        [("country", ASCENDING), ("timestamp", DESCENDING)],
        unique=True,
        name="idx_load_country_ts"
    )

    print("MongoDB collections and indexes created.")

if __name__ == "__main__":
    init_db()