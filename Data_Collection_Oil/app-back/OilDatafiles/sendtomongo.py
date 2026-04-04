import pandas as pd
from pymongo import MongoClient
import math

# ==============================
# FILE PATH
# ==============================

csv_file = r"C:\Users\97254\Desktop\twitter-scraper-author-data-main\Date_Collection_Oil_Prices\Data_Collection_Oil\app-back\OilDatafiles\tweets_oil_gas_combined.csv"

# ==============================
# MONGODB ATLAS CONNECTION
# ==============================

client = MongoClient("mongodb+srv://rotemba3_db_user:12345@dataoilscollect.bje8esi.mongodb.net/")

db = client["DataCollectionOil"]   # you can change name if you want
collection = db["modeltrainig"]

# ==============================
# LOAD CSV
# ==============================

df = pd.read_csv(csv_file, encoding="utf-8-sig")

# clean NaN → None (Mongo friendly)
df = df.where(pd.notnull(df), None)

def clean_record(record):
    cleaned = {}
    for k, v in record.items():
        if isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned

records = [clean_record(r) for r in df.to_dict(orient="records")]

# ==============================
# OPTIONAL: CLEAR OLD DATA
# ==============================

collection.delete_many({})   # ⚠️ deletes everything in collection

# ==============================
# INSERT
# ==============================

if records:
    result = collection.insert_many(records)
    print(f"Inserted {len(result.inserted_ids)} documents into 'modeltrainig'")
else:
    print("No records to insert")

# ==============================
# VERIFY
# ==============================

print("Total documents:", collection.count_documents({}))
print("Sample:")
print(collection.find_one())