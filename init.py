import sqlite3, os, secrets

def __create_config():
    with open("config.py", "w") as file:
        file.write(f"SECRET_KEY = \"{secrets.token_hex(16)}\"\n")

def __create_database():
    if os.path.exists("database.db"):
        os.remove("database.db")
    db = sqlite3.connect("database.db")
    db.execute("""
            CREATE TABLE Visits (
                id INTEGER PRIMARY KEY,
                time TEXT
            )
            """)
    db.execute("""
            CREATE TABLE Users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                passwd TEXT
            )
            """)
    db.close()

__create_config()
__create_database()
