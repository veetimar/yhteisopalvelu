import sqlite3

class Database:
    def execute(self, sql, args=[]):
        id = self.db.execute(sql, args).lastrowid
        self.db.commit()
        return id

    def query(self, sql, args=[], one=False):
        result = self.db.execute(sql, args).fetchall()
        return result if not one else result[0]
    
    def __enter__(self):
        self.db = sqlite3.connect("database.db")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.row_factory = sqlite3.Row
        return self

    def __exit__(self, type, value, traceback):
        self.db.close()