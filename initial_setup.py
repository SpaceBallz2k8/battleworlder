import sqlite3
import pandas as pd


# Path to the database file
db_path = "roster.db"

# Connect to the database (it will create a new file if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create `roster` table
cursor.execute('''
CREATE TABLE roster (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    character_id TEXT,
    level INTEGER,
    power INTEGER,
    stars INTEGER,
    red_stars INTEGER,
    gear_tier INTEGER,
    basic INTEGER,
    special INTEGER,
    ultimate INTEGER,
    passive INTEGER,
    iso_class TEXT,
    guild_id INTEGER
);
''')

# Create `aliases` table
cursor.execute('''
CREATE TABLE aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id TEXT,
    clean_name TEXT
);
''')

# Create requirements table
cursor.execute('''
CREATE TABLE IF NOT EXISTS requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_name TEXT NOT NULL,
        day INTEGER NOT NULL,
        mission INTEGER NOT NULL,
        type TEXT NOT NULL,
        level INTEGER NOT NULL
    );
''')


print("Database and tables created successfully.")
conn.commit()


# File path to your alias CSV
csv_path = "names_map.csv"

# Read the CSV into a DataFrame
df = pd.read_csv(csv_path)

# Insert data into the aliases table
for _, row in df.iterrows():
    cursor.execute("INSERT INTO aliases (clean_name, character_id) VALUES (?, ?)", (row['clean_name'], row['character_id']))

conn.commit()

print("Data inserted into aliases table successfully.")

csv_path = "req.csv"

# Load CSV data into a DataFrame
df = pd.read_csv(csv_path)
# Insert data into the requirements table
for _, row in df.iterrows():
    cursor.execute('''
        INSERT INTO requirements (character_name, day, mission, type, level)
        VALUES (?, ?, ?, ?, ?)
    ''', (row['CharacterName'], row['Day'], row['Mission'], row['Type'], row['Level']))

conn.commit()
conn.close()

print("Data from req.csv inserted successfully.")
    
