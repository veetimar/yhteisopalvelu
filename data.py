import math

import database

def get_users(username=None, user_id=None):
    if username is not None and user_id is not None:
        raise ValueError("cannot process both username and user_id")
    args = []
    one = False
    sql = """SELECT U.id, U.username, U.pwhash, U.admin,
    (SELECT COUNT(*) FROM Posts P WHERE P.user_id = U.id) post_count,
    (SELECT COUNT(*) FROM Comments C WHERE C.user_id = U.id) comment_count,
    image IS NOT NULL has_image
    FROM Users U"""
    if username is not None:
        args.append(username)
        sql += " WHERE U.username = ?"
        one = True
    elif user_id is not None:
        args.append(user_id)
        sql += " WHERE U.id = ?"
        one = True
    sql += " GROUP BY U.id ORDER BY U.username"
    with database.dbase as db:
        return db.query(sql, args=args, one=one)

def get_image(user_id):
    sql = "SELECT image FROM Users WHERE id = ?"
    with database.dbase as db:
        return db.query(sql, args=[user_id], one=True)[0]

def get_posts(post_id=None, keyword=None, page=None):
    args = []
    one = False
    sql = """SELECT P.id, P.content, CL.id class_id, CL.name class, P.time, P.user_id, U.username, COUNT(C.id) count
    FROM Posts P LEFT JOIN Comments C ON P.id = C.post_id, Users U, Classes CL
    WHERE P.user_id = U.id AND P.class_id = CL.id"""
    if post_id is not None:
        args.append(post_id)
        sql += " AND P.id = ?"
        one = True
    if keyword is not None:
        args.append(f"%{keyword["keyword"]}%")
        if keyword["type"] == "content":
            sql += " AND P.content LIKE ?"
        elif keyword["type"] == "username":
            sql += " AND U.username LIKE ?"
        else:
            raise ValueError("illegal search-by parameter")
    sql += " GROUP BY P.id ORDER BY P.time DESC"
    if page is not None:
        args.append(page["size"])
        args.append((page["page"] - 1) * page["size"])
        sql += " LIMIT ? OFFSET ?"
    with database.dbase as db:
        return db.query(sql, args=args, one=one)

def get_post_pages(page_size, keyword=None):
    args = []
    sql = "SELECT COUNT(P.id) FROM Posts P"
    if keyword is not None:
        args.append(f"%{keyword["keyword"]}%")
        sql += ", Users U WHERE P.user_id = U.id AND "
        if keyword["type"] == "content":
            sql += "P.content LIKE ?"
        elif keyword["type"] == "username":
            sql += "U.username LIKE ?"
        else:
            raise ValueError("illegal search-by parameter")
    with database.dbase as db:
        post_count = db.query(sql, args=args, one=True)[0]
    return max(1, math.ceil(post_count / page_size))

def get_comments(post_id=None, comment_id=None, keyword=None, page=None):
    args = []
    one = False
    sql = """SELECT C.id, C.content, C.time, C.user_id, C.post_id, U.username
    FROM Comments C, Users U WHERE C.user_id = U.id"""
    if post_id is not None:
        args.append(post_id)
        sql += " AND C.post_id = ?"
    if comment_id is not None:
        args.append(comment_id)
        sql += " AND C.id = ?"
        one = True
    if keyword is not None:
        args.append(f"%{keyword["keyword"]}%")
        if keyword["type"] == "content":
            sql += " AND C.content LIKE ?"
        elif keyword["type"] == "username":
            sql += " AND U.username LIKE ?"
        else:
            raise ValueError("illegal search-by parameter")
    sql += " ORDER BY C.time"
    if page is not None:
        args.append(page["size"])
        args.append((page["page"] - 1) * page["size"])
        sql += " LIMIT ? OFFSET ?"
    with database.dbase as db:
        return db.query(sql, args=args, one=one)

def get_comment_pages(page_size, keyword=None, post_id=None):
    args = []
    sql = "SELECT COUNT(C.id) FROM COMMENTS C"
    if keyword is not None and keyword["type"] == "username":
        sql += ", Users U"
    if post_id is not None:
        args.append(post_id)
        sql += " WHERE C.post_id = ?"
    if keyword is not None:
        args.append(f"%{keyword["keyword"]}%")
        if post_id is not None:
            sql += " AND"
        else:
            sql += " WHERE"
        if keyword["type"] == "content":
            sql += " C.content LIKE ?"
        elif keyword["type"] == "username":
            sql += " C.user_id = U.id AND U.username LIKE ?"
        else:
            raise ValueError("illegal search-by parameter")
    with database.dbase as db:
        post_count = db.query(sql, args=args, one=True)[0]
    return max(1, math.ceil(post_count / page_size))

def get_classes(class_id=None):
    args = []
    one = False
    sql = "SELECT id, name FROM Classes"
    if class_id is not None:
        args.append(class_id)
        sql += " WHERE id = ?"
        one = True
    sql += " ORDER BY id"
    with database.dbase as db:
        return db.query(sql, args=args, one=one)

def new_user(username, pwhash):
    sql = "INSERT INTO Users (username, pwhash) VALUES (?, ?)"
    with database.dbase as db:
        return db.execute(sql, args=[username, pwhash])

def add_image(image, user_id):
    sql = "UPDATE Users SET image = ? WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[image, user_id])

def change_password(pwhash, user_id):
    sql = "UPDATE Users SET pwhash = ? WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[pwhash, user_id])

def make_admin(user_id):
    sql = "UPDATE Users SET admin = 1 WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[user_id])

def delete_user(user_id):
    sql = "DELETE FROM Users WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[user_id])

def new_post(content, user_id, cs):
    sql = """INSERT INTO Posts (content, time, user_id, class_id)
    VALUES (?, datetime('now', 'localtime'), ?, ?)"""
    with database.dbase as db:
        return db.execute(sql, args=[content, user_id, cs])

def edit_post(content, cs, post_id):
    sql = "UPDATE Posts SET content = ?, class_id = ? WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[content, cs, post_id])

def delete_post(post_id):
    sql = "DELETE FROM Posts WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[post_id])

def new_comment(content, user_id, post_id):
    sql = """INSERT INTO Comments (content, time, user_id, post_id)
    VALUES (?, datetime('now', 'localtime'), ?, ?)"""
    with database.dbase as db:
        return db.execute(sql, args=[content, user_id, post_id])

def edit_comment(content, comment_id):
    sql = "UPDATE Comments SET content = ? WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[content, comment_id])

def delete_comment(comment_id):
    sql = "DELETE FROM Comments WHERE id = ?"
    with database.dbase as db:
        return db.execute(sql, args=[comment_id])
