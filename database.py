import sqlite3

class Database:
    def execute(self, sql, args=[], commit=False):
        id = self.db.execute(sql, args).lastrowid
        if commit:
            self.db.commit()
        return id

    def query(self, sql, args=[], one=False):
        cursor = self.db.execute(sql, args)
        return cursor.fetchone() if one else cursor.fetchall()

    def __enter__(self):
        self.db = sqlite3.connect("database.db")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.row_factory = sqlite3.Row
        return self

    def __exit__(self, type, value, traceback):
        self.db.close()