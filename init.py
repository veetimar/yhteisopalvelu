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
                   time TEXT NOT NULL
               )
               """)
    db.execute("""
               CREATE TABLE Users (
                   id INTEGER PRIMARY KEY,
                   username TEXT NOT NULL UNIQUE,
                   pwhash TEXT NOT NULL
               )
               """)
    db.execute("""
               CREATE TABLE Posts (
                   id INTEGER PRIMARY KEY,
                   content TEXT NOT NULL,
                   class TEXT NOT NULL,
                   time TEXT NOT NULL,
                   user_id INTEGER REFERENCES Users ON DELETE CASCADE
               )
               """)
    db.execute("""
               CREATE TABLE Comments (
                   id INTEGER PRIMARY KEY,
                   content TEXT NOT NULL,
                   time TEXT NOT NULL,
                   user_id INTEGER NOT NULL REFERENCES Users ON DELETE CASCADE,
                   post_id INTEGER NOT NULL REFERENCES Posts ON DELETE CASCADE
               )
               """)
    db.close()

__create_config()
__create_database()
