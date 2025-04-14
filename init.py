import secrets
import os

import database

def __create_config():
    with open("config.py", "w") as file:
        file.write(f"SECRET_KEY = \"{secrets.token_hex(16)}\"\n")

def __create_database():
    if os.path.exists("database.db"):
        os.remove("database.db")
    with database.dbase as db:
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
                       time TEXT NOT NULL,
                       class_id INTEGER NOT NULL REFERENCES Classes ON DELETE RESTRICT,
                       user_id INTEGER NOT NULL REFERENCES Users ON DELETE CASCADE
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
        db.execute("""
                   CREATE TABLE Classes (
                       id INTEGER PRIMARY KEY,
                       name TEXT NOT NULL
                   )
                   """)

def __create_classes():
    with database.dbase as db:
        db.execute("""
                   INSERT INTO Classes (name) VALUES (?)
                   """, args=["Shitpost"])
        db.execute("""
                   INSERT INTO Classes (name) VALUES (?)
                   """, args=["Asiallinen"], commit=True)


if __name__ == "__main__":
    __create_config()
    __create_database()
    __create_classes()
