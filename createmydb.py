import sqlite3

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
    alias_name TEXT
);
''')

print("Database and tables created successfully.")

# Commit changes and close connection
conn.commit()
conn.close()
