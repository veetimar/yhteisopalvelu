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
                         SELECT P.id, P.content, P.class, P.time, U.username, COUNT(C.id) count
                         FROM Posts P LEFT JOIN Users U ON P.user_id = U.id LEFT JOIN Comments C ON P.id = C.post_id
                         GROUP BY P.id
                         ORDER BY P.time DESC
                         """)
    return flask.render_template("index.html", visits=visits, posts=posts)

@app.route("/register", methods=["GET", "POST"])
def register():
    if flask.request.method == "GET":
        message = flask.session.pop("message", None)
        return flask.render_template("register.html", message=message)
    if flask.request.method == "POST":
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "GET":
        message = flask.session.pop("message", None)
        return flask.render_template("login.html", message=message)
    if flask.request.method == "POST":
        username = flask.request.form["username"]
        password = flask.request.form["password"]
        with Database() as db:
            result = db.query("SELECT id, pwhash FROM Users WHERE username = ?", [username], one=True)
        pwhash = result["pwhash"] if result else None
        if pwhash and security.check_password_hash(pwhash, password):
            flask.session["id"] = result["id"]
            flask.session["username"] = username
            return flask.redirect("/")
        flask.session["message"] = "VIRHE: Väärä käyttäjätunnus tai salasana"
        return flask.redirect("/login")

@app.route("/logout")
def logout():
    flask.session.pop("id", None)
    flask.session.pop("username", None)
    return flask.redirect("/")

@app.route("/new_post", methods=["GET", "POST"])
def new_post():
    if "id" not in flask.session:
        return flask.redirect("/login")
    if flask.request.method == "GET":
        message = flask.session.pop("message", None)
        return flask.render_template("new_post.html", message=message)
    if flask.request.method == "POST":
        content = flask.request.form["content"]
        if not content:
            flask.session["message"] = "VIRHE: Tyhjä postaus"
            return flask.redirect("/new_post")
        if "class" not in flask.request.form:
            flask.session["message"] = "VIRHE: Luokittelu puuttuu"
            return flask.redirect("/new_post")
        cs = flask.request.form["class"]
        user_id = flask.session["id"]
        with Database() as db:
            db.execute("INSERT INTO Posts (content, class, time, user_id) VALUES (?, ?, datetime('now'), ?)", [content, cs, user_id], commit=True)
        return flask.redirect("/")

@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if "id" not in flask.session:
        return flask.redirect("/login")
    with Database() as db:
        post = db.query("SELECT id, user_id, content FROM Posts WHERE id = ?", [post_id], one=True)
    if not post or post["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        message = flask.session.pop("message", None)
        return flask.render_template("/edit_post.html", post=post, message=message)
    if flask.request.method == "POST":
        content = flask.request.form["content"]
        if not content:
            flask.session["message"] = "VIRHE: Tyhjä postaus"
            return flask.redirect(f"/edit_post/{post_id}")
        with Database() as db:
            db.execute("UPDATE Posts SET content = ? WHERE id = ?", [content, post_id], commit=True)
        return flask.redirect("/")

@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):
    if "id" not in flask.session:
        return flask.redirect("/login")
    with Database() as db:
        post = db.query("SELECT user_id FROM Posts P WHERE P.id = ?", [post_id], one=True)
    if not post or post["user_id"] != flask.session["id"]:
        flask.abort(403)
    with Database() as db:
        db.execute("DELETE FROM Posts WHERE id = ?", [post_id], commit=True)
    return flask.redirect("/")

@app.route("/comments/<int:post_id>")
def comments(post_id):
    with Database() as db:
        post = db.query("SELECT P.id, P.content, P.class, P.time, U.username FROM Posts P, Users U WHERE P.user_id = U.id AND P.id = ?", [post_id], one=True)
        comments = db.query("SELECT C.id, C.content, C.time, U.username FROM Comments C, Users U WHERE C.user_id = U.id AND C.post_id = ?", [post_id])
    if not post:
        flask.abort(403)
    return flask.render_template("comments.html", post=post, comments=comments)

@app.route("/new_comment/<int:post_id>", methods=["GET", "POST"])
def new_comment(post_id):
    if "id" not in flask.session:
        return flask.redirect("/login")
    if flask.request.method == "GET":
        message = flask.session.pop("message", None)
        return flask.render_template("new_comment.html", post_id=post_id, message=message)
    if flask.request.method == "POST":
        content = flask.request.form["content"]
        if not content:
            flask.session["message"] = "VIRHE: Tyhjä kommentti"
            return flask.redirect(f"/new_comment/{post_id}") 
        user_id = flask.session["id"]
        with Database() as db:
            db.execute("INSERT INTO Comments (content, time, user_id, post_id) VALUES (?, datetime('now'), ?, ?)", [content, user_id, post_id], commit=True)
        return flask.redirect(f"/comments/{post_id}")

@app.route("/edit_comment/<int:comment_id>", methods=["GET", "POST"])
def edit_domment(comment_id):
    if "id" not in flask.session:
        return flask.redirect("/login")
    with Database() as db:
        comment = db.query("SELECT id, user_id, content, post_id FROM Comments C WHERE C.id = ?", [comment_id], one=True)
    if not comment or comment["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        message = flask.session.pop("message", None)
        return flask.render_template("edit_comment.html", comment=comment, message=message)
    if flask.request.method == "POST":
        content = flask.request.form["content"]
        if not content:
            flask.session["message"] = "VIRHE: Tyhjä kommentti"
            return flask.redirect(f"/edit_comment/{comment_id}") 
        with Database() as db:
            db.execute("UPDATE Comments SET content = ? WHERE id = ?", [content, comment_id], commit=True)
        return flask.redirect(f"/comments/{comment["post_id"]}")

@app.route("/delete_comment/<int:comment_id>")
def delete_domment(comment_id):
    if "id" not in flask.session:
        return flask.redirect("/login")
    with Database() as db:
        comment = db.query("SELECT user_id, post_id FROM Comments C WHERE C.id = ?", [comment_id], one=True)
    if not comment or comment["user_id"] != flask.session["id"]:
        flask.abort(403)
    with Database() as db:
        db.execute("DELETE FROM Comments WHERE id = ?", [comment_id], commit=True)
    return flask.redirect(f"/comments/{comment["post_id"]}")
