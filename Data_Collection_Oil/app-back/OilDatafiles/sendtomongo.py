import os
import math
import pandas as pd
from pymongo import MongoClient, UpdateOne

# ==============================
# FILE PATH
# ==============================

# CHANGED: relative to this file's location instead of a hardcoded Windows
# path. Keep this file in the same folder as combine_data.py so this
# lines up with what that script writes.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_file = os.path.join(BASE_DIR, "tweets_oil_gas_combined.csv")

# ==============================
# MONGODB ATLAS CONNECTION
# ==============================
# CHANGED: reads your existing MONGO_URI secret/env var instead of a
# hardcoded connection string. Use whatever name your GitHub secret already
# has — if it's not literally "MONGO_URI", either rename the secret or
# change the string below to match.

print("Connecting to MongoDB...")
client     = MongoClient(os.environ["MONGO_URI"])
db         = client["DataCollectionOil"]
collection = db["modeltrainig"]
print("Connected.")

# ==============================
# LOAD CSV
# ==============================

print("Loading CSV...")
df = pd.read_csv(csv_file, encoding="utf-8-sig")
df = df.where(pd.notnull(df), None)
print(f"Loaded {len(df)} rows from CSV.")

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
# LOAD ALL EXISTING KEYS FROM MONGO IN ONE QUERY
# Much faster than one find_one per row
# ==============================

print("Loading existing keys from MongoDB...")
existing_docs = collection.find({}, {"date": 1, "publisher": 1, "text": 1, "_id": 0})

existing_keys = set()
for doc in existing_docs:
    key = (
        str(doc.get("date", "")),
        str(doc.get("publisher", "")),
        str(doc.get("text", ""))
    )
    existing_keys.add(key)

print(f"Found {len(existing_keys)} existing documents in MongoDB.")

# ==============================
# BUILD BULK OPERATIONS
# ==============================

price_fields = [
    "oil_price", "oil_open", "oil_high", "oil_low",
    "oil_volume", "oil_change_percent", "oil_price_yesterday", "gas_price"
]

inserts = []
updates = []
skipped = 0

BATCH_SIZE = 500

print(f"Processing {len(records)} records...")

for i, record in enumerate(records):
    if i % 500 == 0:
        print(f"  Processing {i}/{len(records)}...")

    record_date      = record.get("date")
    record_publisher = record.get("publisher")
    record_text      = record.get("text")

    if record_date is None:
        skipped += 1
        continue

    key = (str(record_date), str(record_publisher), str(record_text))

    if key in existing_keys:
        update_fields = {
            field: record.get(field)
            for field in price_fields
            if field in record
        }
        if update_fields:
            updates.append(UpdateOne(
                {"date": record_date, "publisher": record_publisher, "text": record_text},
                {"$set": update_fields}
            ))
    else:
        inserts.append(record)
        existing_keys.add(key)  # prevent duplicates within batch

# ==============================
# EXECUTE IN BATCHES
# ==============================

inserted_count = 0
updated_count  = 0

if inserts:
    print(f"\nInserting {len(inserts)} new records in batches of {BATCH_SIZE}...")
    for i in range(0, len(inserts), BATCH_SIZE):
        batch = inserts[i:i + BATCH_SIZE]
        collection.insert_many(batch, ordered=False)
        inserted_count += len(batch)
        print(f"  Inserted {min(i + BATCH_SIZE, len(inserts))}/{len(inserts)}")
else:
    print("\nNo new records to insert.")

if updates:
    print(f"\nUpdating {len(updates)} existing records in batches of {BATCH_SIZE}...")
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i + BATCH_SIZE]
        result = collection.bulk_write(batch, ordered=False)
        updated_count += result.modified_count
        print(f"  Updated {min(i + BATCH_SIZE, len(updates))}/{len(updates)}")
else:
    print("\nNo records to update.")

# ==============================
# VERIFY
# ==============================

print("\n==============================")
print("DONE")
print("==============================")
print(f"Inserted new records:       {inserted_count}")
print(f"Updated existing records:   {updated_count}")
print(f"Skipped (no date):          {skipped}")