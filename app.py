import flask, werkzeug.security as security, werkzeug.middleware.proxy_fix as proxy_fix # third party
import functools # built-in
import config, database # self-made

app = flask.Flask(__name__)
app.secret_key = config.SECRET_KEY
app.wsgi_app = proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

def require_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "id" not in flask.session or "username" not in flask.session:
            return flask.redirect("/login")
        return f(*args, **kwargs)
    return wrapper

@app.route("/", methods=["GET", "POST"])
def index():
    with database.Database() as db:
        db.execute("INSERT INTO Visits (time) VALUES (datetime('now'))", commit=True)
        visits = db.query("SELECT COUNT(*) FROM Visits", one=True)[0]
    if flask.request.method == "GET":
        posts = database.get_post()
        return flask.render_template("index.html", visits=visits, posts=posts)
    elif flask.request.method == "POST":
        keyword = flask.request.form["keyword"]
        if not keyword or len(keyword) > 1000:
            flask.abort(403)
        posts = database.get_post(keyword=keyword)
        return flask.render_template("index.html", visits=visits, posts=posts, keyword=keyword)

@app.route("/register", methods=["GET", "POST"])
def register():
    if flask.request.method == "GET":
        message = flask.session.pop("message", None)
        return flask.render_template("register.html", message=message)
    elif flask.request.method == "POST":
        username = flask.request.form["username"]
        password1 = flask.request.form["password1"]
        password2 = flask.request.form["password2"]
        if not username or not password1 or not password2 or len(username) > 20 or len(password1) > 20 or len(password2) > 20:
            flask.abort(403)
        if password1 != password2:
            flask.session["message"] = "VIRHE: Salasanat eivät täsmää"
            return flask.redirect("/register")
        pwhash = security.generate_password_hash(password1)
        try:
            with database.Database() as db:
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
    elif flask.request.method == "POST":
        username = flask.request.form["username"]
        password = flask.request.form["password"]
        if not username or not password or len(username) > 20 or len(password) > 20:
            flask.abort(403)
        with database.Database() as db:
            user = db.query("SELECT id, pwhash FROM Users WHERE username = ?", [username], one=True)
        pwhash = user["pwhash"] if user else None
        if pwhash and security.check_password_hash(pwhash, password):
            flask.session["id"] = user["id"]
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
@require_login
def new_post():
    if flask.request.method == "GET":
        return flask.render_template("new_post.html")
    elif flask.request.method == "POST":
        content = flask.request.form["content"]
        if not content or len(content) > 1000 or "class" not in flask.request.form:
            flask.abort(403)
        cs = flask.request.form["class"]
        user_id = flask.session["id"]
        with database.Database() as db:
            db.execute("INSERT INTO Posts (content, class, time, user_id) VALUES (?, ?, datetime('now'), ?)", [content, cs, user_id], commit=True)
        return flask.redirect("/")

@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@require_login
def edit_post(post_id):
    post = database.get_post(post_id=post_id)
    if not post:
        flask.abort(404)
    if post["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("edit_post.html", post=post)
    elif flask.request.method == "POST":
        content = flask.request.form["content"]
        cs = flask.request.form["class"]
        if not content or len(content) > 1000 or "class" not in flask.request.form:
            flask.abort(403)
        with database.Database() as db:
            db.execute("UPDATE Posts SET content = ?, class = ? WHERE id = ?", [content, cs, post_id], commit=True)
        return flask.redirect("/")

@app.route("/delete_post/<int:post_id>", methods=["GET", "POST"])
@require_login
def delete_post(post_id):
    post = database.get_post(post_id=post_id)
    if not post:
        flask.abort(404)
    if post["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("delete_post.html", post_id=post_id)
    elif flask.request.method == "POST":
        if "yes" in flask.request.form:
            with database.Database() as db:
                db.execute("DELETE FROM Posts WHERE id = ?", [post_id], commit=True)
        return flask.redirect("/")

@app.route("/comments/<int:post_id>", methods=["GET", "POST"])
def comments(post_id):
    post = database.get_post(post_id)
    if not post:
        flask.abort(404)
    if flask.request.method == "GET":
        comments = database.get_comment(post_id=post_id)
        return flask.render_template("comments.html", post=post, comments=comments)
    elif flask.request.method == "POST":
        keyword = flask.request.form["keyword"]
        if not keyword or len(keyword) > 1000:
            flask.abort(403)
        comments = database.get_comment(post_id=post_id, keyword=keyword)
        return flask.render_template("comments.html", post=post, comments=comments, keyword=keyword)

@app.route("/new_comment/<int:post_id>", methods=["GET", "POST"])
@require_login
def new_comment(post_id):
    if not database.get_post(post_id=post_id):
        flask.abort(404)
    if flask.request.method == "GET":
        return flask.render_template("new_comment.html", post_id=post_id)
    elif flask.request.method == "POST":
        content = flask.request.form["content"]
        if not content or len(content) > 1000:
            flask.abort(403)
        user_id = flask.session["id"]
        with database.Database() as db:
            db.execute("INSERT INTO Comments (content, time, user_id, post_id) VALUES (?, datetime('now'), ?, ?)", [content, user_id, post_id], commit=True)
        return flask.redirect(f"/comments/{post_id}")

@app.route("/edit_comment/<int:comment_id>", methods=["GET", "POST"])
@require_login
def edit_domment(comment_id):
    comment = database.get_comment(comment_id=comment_id)
    if not comment:
        flask.abort(404)
    if comment["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("edit_comment.html", comment=comment)
    elif flask.request.method == "POST":
        content = flask.request.form["content"]
        if not content or len(content) > 1000:
            flask.abort(403)
        with database.Database() as db:
            db.execute("UPDATE Comments SET content = ? WHERE id = ?", [content, comment_id], commit=True)
        return flask.redirect(f"/comments/{comment["post_id"]}")

@app.route("/delete_comment/<int:comment_id>", methods=["GET", "POST"])
@require_login
def delete_comment(comment_id):
    comment = database.get_comment(comment_id=comment_id)
    if not comment:
        flask.abort(404)
    if comment["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("delete_comment.html", comment_id=comment_id)
    elif flask.request.method == "POST":
        if "yes" not in flask.request.form and "no" not in flask.request.form:
            flask.abort(403)
        if "yes" in flask.request.form:
            with database.Database() as db:
                db.execute("DELETE FROM Comments WHERE id = ?", [comment_id], commit=True)
    return flask.redirect(f"/comments/{comment["post_id"]}")
