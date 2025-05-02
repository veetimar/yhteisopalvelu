CREATE TABLE Users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    pwhash TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0,
    image BLOB
);
CREATE TABLE Posts (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    time TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES Users ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES Classes ON DELETE RESTRICT
);
CREATE TABLE Comments (
    id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,
    time TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES Users ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES Posts ON DELETE CASCADE
);
CREATE TABLE Classes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE INDEX idx_username ON Users (username);
CREATE INDEX idx_user_posts ON Posts (user_id);
CREATE INDEX idx_user_comments ON Comments (user_id);
CREATE INDEX idx_post_comments ON Comments (post_id);
