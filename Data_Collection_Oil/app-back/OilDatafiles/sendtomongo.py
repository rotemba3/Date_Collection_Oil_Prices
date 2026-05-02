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

db = client["DataCollectionOil"]
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
# INSERT NEW DATES + UPDATE EXISTING PRICES
# ==============================

inserted_count = 0
updated_count = 0
skipped_count = 0

price_fields = [
    "oil_price",
    "oil_price_yesterday",
    "gas_price"
]

for record in records:
    record_date = record.get("date")

    if record_date is None:
        skipped_count += 1
        continue

    existing = collection.find_one({"date": record_date})

    if existing:
        update_fields = {}

        for field in price_fields:
            if field in record:
                update_fields[field] = record.get(field)

        if update_fields:
            collection.update_many(
                {"date": record_date},
                {"$set": update_fields}
            )
            updated_count += 1
        else:
            skipped_count += 1

    else:
        collection.insert_one(record)
        inserted_count += 1

# ==============================
# VERIFY
# ==============================

print(f"Inserted new records: {inserted_count}")
print(f"Updated existing date records: {updated_count}")
print(f"Skipped records: {skipped_count}")

print("Total documents:", collection.count_documents({}))
print("Sample:")
print(collection.find_one())