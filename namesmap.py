import sqlite3
import pandas as pd

# File path to your CSV
csv_path = "names_map.csv"

# Read the CSV into a DataFrame
df = pd.read_csv(csv_path)

# Connect to SQLite database
conn = sqlite3.connect("roster.db")
cursor = conn.cursor()

# Insert data into the aliases table
for _, row in df.iterrows():
    cursor.execute("INSERT INTO aliases (clean_name, character_id) VALUES (?, ?)", (row['clean_name'], row['character_id']))

conn.commit()
conn.close()

print("Data inserted into aliases table successfully.")
