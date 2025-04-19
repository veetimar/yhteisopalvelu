import sqlite3

class Database:
    def __init__(self):
        self.db = None

    def execute(self, sql, args=[], commit=False):
        row_id = self.db.execute(sql, args).lastrowid
        if commit:
            self.db.commit()
        return row_id
    
    def executescript(self, file_path):
        with open(file_path) as file:
            self.db.executescript(file.read())

    def query(self, sql, args=[], one=False):
        cursor = self.db.execute(sql, args)
        return cursor.fetchone() if one else cursor.fetchall()

    def __enter__(self):
        self.db = sqlite3.connect("database.db")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.row_factory = sqlite3.Row
        return self

    def __exit__(self, e_type, e_value, e_traceback):
        self.db.close()
        self.db = None

dbase = Database()
