import sqlite3, os

if os.path.exists("database.db"):
    os.remove("database.db")

db = sqlite3.connect("database.db")