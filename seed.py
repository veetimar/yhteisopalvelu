import random

import database

USER_COUNT = 1000
POST_COUNT = 10**5
COMMENT_COUNT = 10**6

USERS = "INSERT INTO Users (username, pwhash) VALUES (?, ?)"
POSTS = "INSERT INTO Posts (content, time, user_id, class_id) VALUES (?, datetime('now'), ?, ?)"
COMMENTS = "INSERT INTO Comments (content, time, user_id, post_id) VALUES (?, datetime('now'), ?, ?)"

with database.dbase as db:
    db.execute("DELETE FROM Users")
    db.execute("DELETE FROM Posts")
    db.execute("DELETE FROM Comments")
    for i in range(1, USER_COUNT + 1):
        db.execute(USERS, [f"user{i}", "password"])
    for i in range(1, POST_COUNT + 1):
        user_id = random.randint(1, USER_COUNT)
        db.execute(POSTS, [f"post{i}", user_id, i % 2 + 1])
    for i in range(1, COMMENT_COUNT + 1):
        user_id = random.randint(1, USER_COUNT)
        post_id = random.randint(1, POST_COUNT)
        db.execute(COMMENTS, [f"comment{i}", user_id, post_id])
