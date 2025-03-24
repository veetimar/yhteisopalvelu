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

def get_post(post_id=None):
    args = []
    sql = """SELECT P.id, P.content, P.class, P.time, P.user_id, U.username, COUNT(C.id) count 
    FROM Posts P LEFT JOIN Users U ON P.user_id = U.id LEFT JOIN Comments C ON P.id = C.post_id"""
    if post_id:
        args.append(post_id)
        sql += " WHERE P.id = ?"
        one = True
    else:
        one = False
    sql += " GROUP BY P.id ORDER BY P.time DESC"
    with Database() as db:
        return db.query(sql, args=args, one=one)

def get_comment(post_id=None, comment_id=None):
    args = []
    sql = """SELECT C.id, C.content, C.time, C.user_id, C.post_id, U.username
    FROM Comments C, Users U WHERE C.user_id = U.id"""
    if post_id:
        args.append(post_id)
        sql += " AND C.post_id = ?"
    if comment_id:
        args.append(comment_id)
        sql += " AND C.id = ?"
        one = True
    else:
        one = False
    sql += " ORDER BY C.time"
    with Database() as db:
        return db.query(sql, args=args, one=one)
