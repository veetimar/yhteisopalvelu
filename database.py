import sqlite3

class Database:
    def __init__(self):
        self.db = None

    def execute(self, sql, args=[], commit=False):
        row_id = self.db.execute(sql, args).lastrowid
        if commit:
            self.db.commit()
        return row_id

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

def get_users(username=None, user_id=None):
    if username and user_id:
        raise ValueError("cannot process both username and user_id")
    args = []
    one = False
    sql = """SELECT U.id, U.username, U.pwhash,
    (SELECT COUNT(*) FROM Posts P WHERE P.user_id = U.id) post_count,
    (SELECT COUNT(*) FROM Comments C WHERE C.user_id = U.id) comment_count
    FROM Users U"""
    if username:
        args.append(username)
        sql += " WHERE U.username = ?"
        one = True
    if user_id:
        args.append(user_id)
        sql += " WHERE U.id = ?"
        one = True
    sql += " GROUP BY U.id ORDER BY U.username"
    with dbase as db:
        return db.query(sql, args=args, one=one)

def get_posts(post_id=None, keyword=None):
    args = []
    one = False
    sql = """SELECT P.id, P.content, CL.name class, P.time, P.user_id, U.username, COUNT(C.id) count
    FROM Posts P LEFT JOIN Comments C ON P.id = C.post_id, Users U, Classes CL
    WHERE P.user_id = U.id AND P.class_id = CL.id"""
    if post_id:
        args.append(post_id)
        sql += " AND P.id = ?"
        one = True
    if keyword:
        args.append("%" + keyword + "%")
        sql += " AND P.content LIKE ?"
    sql += " GROUP BY P.id ORDER BY P.time DESC"
    with dbase as db:
        return db.query(sql, args=args, one=one)

def get_comments(post_id=None, comment_id=None, keyword=None):
    args = []
    one = False
    sql = """SELECT C.id, C.content, C.time, C.user_id, C.post_id, U.username
    FROM Comments C, Users U WHERE C.user_id = U.id"""
    if post_id:
        args.append(post_id)
        sql += " AND C.post_id = ?"
    if comment_id:
        args.append(comment_id)
        sql += " AND C.id = ?"
        one = True
    if keyword:
        args.append("%" + keyword + "%")
        sql += " AND C.content LIKE ?"
    sql += " ORDER BY C.time"
    with dbase as db:
        return db.query(sql, args=args, one=one)

def get_classes(class_id=None):
    args = []
    one = False
    sql = "SELECT id, name FROM Classes"
    if class_id:
        args.append(class_id)
        sql += " WHERE id = ?"
        one = True
    sql += " ORDER BY id"
    with dbase as db:
        return db.query(sql, args=args, one=one)
