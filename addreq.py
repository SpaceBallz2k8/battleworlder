import sqlite3
import pandas as pd

# Path to your SQLite database
db_path = "roster.db"

# Path to your CSV file
csv_path = "req.csv"


def create_requirements_table():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # SQL to create the requirements table
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS requirements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_name TEXT NOT NULL,
        day INTEGER NOT NULL,
        mission INTEGER NOT NULL,
        type TEXT NOT NULL,
        level INTEGER NOT NULL
    );
    '''
    cursor.execute(create_table_sql)
    conn.commit()
    conn.close()
    print("Requirements table created successfully.")


def load_data_into_requirements():
    # Load CSV data into a DataFrame
    df = pd.read_csv(csv_path)

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert data into the requirements table
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO requirements (character_name, day, mission, type, level)
            VALUES (?, ?, ?, ?, ?)
        ''', (row['CharacterName'], row['Day'], row['Mission'], row['Type'], row['Level']))

    conn.commit()
    conn.close()
    print("Data from req.csv inserted successfully.")


# Run the functions
create_requirements_table()
load_data_into_requirements()
