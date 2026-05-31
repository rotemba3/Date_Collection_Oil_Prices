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

db         = client["DataCollectionOil"]
collection = db["modeltrainig"]

# ==============================
# LOAD CSV
# ==============================

df = pd.read_csv(csv_file, encoding="utf-8-sig")
df = df.where(pd.notnull(df), None)

# ==============================
# CLEAN RECORDS
# ==============================

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
# INSERT / UPDATE LOGIC
# Each row is uniquely identified by (date + publisher + text).
# - New unique rows → insert
# - Existing rows → update price fields only
# This way multiple tweets on the same date are all stored separately.
# ==============================

inserted_count = 0
updated_count  = 0
skipped_count  = 0

price_fields = [
    "oil_price",
    "oil_open",
    "oil_high",
    "oil_low",
    "oil_volume",
    "oil_change_percent",
    "oil_price_yesterday",
    "gas_price"
]

for record in records:
    record_date      = record.get("date")
    record_publisher = record.get("publisher")
    record_text      = record.get("text")

    if record_date is None:
        skipped_count += 1
        continue

    # Unique key: date + publisher + text
    existing = collection.find_one({
        "date":      record_date,
        "publisher": record_publisher,
        "text":      record_text
    })

    if existing:
        # Row already exists — only update price fields
        update_fields = {
            field: record.get(field)
            for field in price_fields
            if field in record
        }

        if update_fields:
            collection.update_one(
                {"_id": existing["_id"]},
                {"$set": update_fields}
            )
            updated_count += 1
        else:
            skipped_count += 1

    else:
        # New row — insert it
        collection.insert_one(record)
        inserted_count += 1

# ==============================
# VERIFY
# ==============================

print(f"Inserted new records: {inserted_count}")
print(f"Updated existing records: {updated_count}")
print(f"Skipped records: {skipped_count}")
print(f"Total documents in MongoDB: {collection.count_documents({})}")
print("Sample:")
print(collection.find_one())