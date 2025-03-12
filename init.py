import sqlite3, os

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