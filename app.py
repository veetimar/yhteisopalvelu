import flask, werkzeug.security as security, werkzeug.middleware.proxy_fix as proxy_fix
from config import SECRET_KEY
from database import Database

app = flask.Flask(__name__)
app.secret_key = SECRET_KEY
app.wsgi_app = proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.route("/")
def index():
    with Database() as db:
        db.execute("INSERT INTO Visits (time) VALUES (datetime('now'))", commit=True)
        visits = db.query("SELECT COUNT(*) FROM Visits", one=True)[0]
        posts = db.query("""
                         SELECT P.id, P.content, P.time, U.username, COUNT(C.id) count
                         FROM Posts P LEFT JOIN Users U ON P.user_id = U.id LEFT JOIN Comments C ON P.id = C.post_id
                         GROUP BY P.id
                         ORDER BY P.time DESC
                         """)
    return flask.render_template("index.html", visits=visits, posts=posts)

@app.route("/register")
def register():
    message = flask.session.pop("message", None)
    return flask.render_template("register.html", message=message)

@app.route("/create_account", methods=["POST"])
def create_account():
    username = flask.request.form["username"]
    if not username:
        flask.session["message"] = "VIRHE: Tyhjä käyttäjätunnus"
        return flask.redirect("/register")
    password1 = flask.request.form["password1"]
    password2 = flask.request.form["password2"]
    if password1 != password2:
        flask.session["message"] = "VIRHE: Salasanat eivät täsmää"
        return flask.redirect("/register")
    if not password1:
        flask.session["message"] = "VIRHE: Tyhjä salasana"
        return flask.redirect("/register")
    pwhash = security.generate_password_hash(password1)
    try:
        with Database() as db:
            db.execute("INSERT INTO Users (username, pwhash) VALUES (?, ?)", [username, pwhash], commit=True)
    except:
        flask.session["message"] = "VIRHE: Käyttäjätunnus on varattu"
        return flask.redirect("/register")
    flask.session["message"] = "Rekisteröityminen onnistui, kirjaudu sisään"
    return flask.redirect("/login")

@app.route("/login")
def login():
    message = flask.session.pop("message", None)
    return flask.render_template("login.html", message=message)

@app.route("/create_session", methods=["POST"])
def create_session():
    username = flask.request.form["username"]
    password = flask.request.form["password"]
    with Database() as db:
        result = db.query("SELECT pwhash FROM Users WHERE username = ?", [username], one=True)
    pwhash = result[0] if result else None
    if pwhash and security.check_password_hash(pwhash, password):
        flask.session["username"] = username
        return flask.redirect("/")
    flask.session["message"] = "VIRHE: Väärä käyttäjätunnus tai salasana"
    return flask.redirect("/login")

@app.route("/logout")
def logout():
    flask.session.pop("username", None)
    return flask.redirect("/")

@app.route("/new_post")
def new_post():
    if "username" not in flask.session:
        return flask.redirect("/login")
    return flask.render_template("new_post.html")

@app.route("/create_post", methods=["POST"])
def create_post():
    content = flask.request.form["content"]
    username = flask.session["username"]
    with Database() as db:
        user_id = db.query("SELECT id FROM Users WHERE username = ?", [username], one=True)[0]
        db.execute("INSERT INTO Posts (content, time, user_id) VALUES (?, datetime('now'), ?)", [content, user_id], commit=True)
    return flask.redirect("/")

@app.route("/edit_post/<int:post_id>")
def edit_post(post_id):
    if "username" not in flask.session:
        return flask.redirect("/login")
    username = flask.session["username"]
    with Database() as db:
        post = db.query("SELECT U.username, P.id, P.content FROM Users U, Posts P WHERE U.id = P.user_id AND P.id = ?", [post_id], one=True)
    if post["username"] != username:
        return flask.redirect("/")
    return flask.render_template("/edit_post.html", post=post)

@app.route("/confirm_edit_post/<int:post_id>", methods=["POST"])
def confirm_edit_post(post_id):
    content = flask.request.form["content"]
    with Database() as db:
        db.execute("UPDATE Posts SET content = ? WHERE id = ?", [content, post_id], commit=True)
    return flask.redirect("/")

@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):
    if "username" not in flask.session:
        return flask.redirect("/login")
    username = flask.session["username"]
    with Database() as db:
        owner = db.query("SELECT U.username FROM Users U, Posts P WHERE U.id = P.user_id AND P.id = ?", [post_id], one=True)[0]
    if owner != username:
        return flask.redirect("/")
    with Database() as db:
        db.execute("DELETE FROM Posts WHERE id = ?", [post_id], commit=True)
    return flask.redirect("/")

@app.route("/show_post/<int:post_id>")
def show_post(post_id):
    return flask.render_template("show_post.html")
