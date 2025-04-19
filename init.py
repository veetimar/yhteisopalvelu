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
        db.executescript("schema.sql")
        db.executescript("init.sql")


if __name__ == "__main__":
    __create_config()
    __create_database()
