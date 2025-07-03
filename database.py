import sqlite3

class Database:
    def __init__(self):
        self.db = None
        self.cur = None
        self.commit = False

    def execute(self, sql, args=[]):
        row_id = self.cur.execute(sql, args).lastrowid
        self.commit = True
        return row_id

    def executescript(self, file_path):
        with open(file_path) as file:
            self.cur.executescript(file.read())

    def query(self, sql, args=[], one=False):
        res = self.cur.execute(sql, args)
        return res.fetchone() if one else res.fetchall()

    def __enter__(self):
        self.db = sqlite3.connect("database.db")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.row_factory = sqlite3.Row
        self.cur = self.db.cursor()
        return self

    def __exit__(self, e_type, e_value, e_traceback):
        if self.commit:
            self.db.commit()
        self.cur.close()
        self.db.close()
        self.__init__()

dbase = Database()
