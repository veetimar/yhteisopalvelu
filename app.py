import functools
import secrets
import sqlite3

import flask
import markupsafe
from werkzeug import security
from werkzeug.middleware import proxy_fix

import config
import data

app = flask.Flask(__name__)
app.secret_key = config.SECRET_KEY
app.wsgi_app = proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.template_filter()
def show_lines(content):
    content = str(markupsafe.escape(content))
    content = content.replace("\n", "<br />")
    return markupsafe.Markup(content)

def require_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "id" not in flask.session or "username" not in flask.session:
            return flask.redirect("/login")
        return f(*args, **kwargs)
    return wrapper

def check_csrf():
    if "csrf_token" not in flask.request.form or "csrf_token" not in flask.session:
        flask.abort(403)
    if flask.request.form["csrf_token"] != flask.session["csrf_token"]:
        flask.abort(403)

def create_session(user_id, username):
    flask.session["id"] = user_id
    flask.session["username"] = username
    flask.session["csrf_token"] = secrets.token_hex(16)

@app.route("/", methods=["GET", "POST"])
def index():
    posts = data.get_posts()
    if flask.request.method == "GET":
        return flask.render_template("index.html", posts=posts)
    if flask.request.method == "POST":
        if "cancel" in flask.request.form:
            return flask.render_template("index.html", posts=posts)
        keyword = flask.request.form["keyword"]
        if not keyword or len(keyword) > 1000:
            flask.abort(403)
        posts = data.get_posts(keyword=keyword)
        return flask.render_template("index.html", posts=posts, keyword=keyword)

@app.route("/register", methods=["GET", "POST"])
def register():
    if flask.request.method == "GET":
        return flask.render_template("register.html", filled={}, next_page=flask.request.referrer)
    if flask.request.method == "POST":
        next_page = flask.request.form["next_page"]
        if "get" in flask.request.form:
            return flask.render_template("register.html", filled={}, next_page=next_page)
        username = flask.request.form["username"]
        password1 = flask.request.form["password1"]
        password2 = flask.request.form["password2"]
        if not (username and password1 and password2) or max(len(username), len(password1), len(password2)) > 20:
            flask.abort(403)
        filled = {"username": username}
        if password1 != password2:
            flask.flash("VIRHE: Salasanat eivät täsmää")
            return flask.render_template("register.html", filled=filled, next_page=next_page)
        pwhash = security.generate_password_hash(password1)
        try:
            user_id = data.new_user(username, pwhash)
        except sqlite3.IntegrityError:
            flask.flash("VIRHE: Käyttäjätunnus on varattu")
            return flask.render_template("register.html", filled=filled, next_page=next_page)
        create_session(user_id, username)
        return flask.redirect(next_page)

@app.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "GET":
        return flask.render_template("login.html", filled={}, next_page=flask.request.referrer)
    if flask.request.method == "POST":
        next_page = flask.request.form["next_page"]
        if "get" in flask.request.form:
            return flask.render_template("login.html", filled={}, next_page=next_page)
        username = flask.request.form["username"]
        password = flask.request.form["password"]
        if not username or not password or len(username) > 20 or len(password) > 20:
            flask.abort(403)
        filled = {"username": username}
        usr = data.get_users(username=username)
        pwhash = usr["pwhash"] if usr else None
        if not pwhash:
            flask.flash("VIRHE: Käyttäjätunnusta ei löydy")
            return flask.render_template("login.html", filled=filled, next_page=next_page)
        if not security.check_password_hash(pwhash, password):
            flask.flash("VIRHE: Väärä salasana")
            return flask.render_template("login.html", filled=filled, next_page=next_page)
        create_session(usr["id"], username)
        return flask.redirect(next_page)

@app.route("/logout")
def logout():
    flask.session.pop("id", None)
    flask.session.pop("username", None)
    flask.session.pop("csrf_token", None)
    return flask.redirect("/")

@app.route("/user/<int:user_id>")
def user(user_id):
    usr = data.get_users(user_id=user_id)
    if not usr:
        flask.abort(404)
    return flask.render_template("user.html", user=usr)

@app.route("/add_image", methods=["GET", "POST"])
@require_login
def add_image():
    user_id = flask.session["id"]
    if flask.request.method == "GET":
        return flask.render_template("add_image.html")
    if flask.request.method == "POST":
        check_csrf()
        file = flask.request.files["image"]
        if not file:
            data.add_image(None, user_id)
            return flask.redirect(f"/user/{user_id}")
        if not file.filename.endswith(".jpg"):
            flask.abort(403)
        image = file.read()
        if len(image) > 1000 * 1024:
            flask.flash("VIRHE: Liian suuri kuva")
            return flask.render_template("add_image.html")
        data.add_image(image, user_id)
        return flask.redirect(f"/user/{user_id}")

@app.route("/show_image/<int:user_id>")
def show_image(user_id):
    image = data.get_image(user_id)
    if not image:
        flask.abort(404)
    response = flask.make_response(image)
    response.headers.set("Content-Type", "image/jpeg")
    return response

@app.route("/change_password", methods=["GET", "POST"])
@require_login
def change_password():
    if flask.request.method == "GET":
        return flask.render_template("change_password.html")
    if flask.request.method == "POST":
        check_csrf()
        old_password = flask.request.form["old_password"]
        password1 = flask.request.form["password1"]
        password2 = flask.request.form["password2"]
        if not (old_password and password1 and password2) or max(len(old_password), len(password1), len(password2)) > 20:
            flask.abort(403)
        if password1 != password2:
            flask.flash("VIRHE: Salasanat eivät täsmää")
            return flask.render_template("change_password.html")
        if old_password == password1:
            flask.flash("VIRHE: Salasana on sama kuin aiemmin")
            return flask.render_template("change_password.html")
        user_id = flask.session["id"]
        usr = data.get_users(user_id=user_id)
        if not security.check_password_hash(usr["pwhash"], old_password):
            flask.flash("VIRHE: Väärä salasana")
            return flask.render_template("change_password.html")
        pwhash = security.generate_password_hash(password1)
        data.change_password(pwhash, user_id)
        return flask.redirect(f"/user/{user_id}")

@app.route("/delete_user", methods=["GET", "POST"])
@require_login
def delete_user():
    if flask.request.method == "GET":
        return flask.render_template("delete_user.html")
    if flask.request.method == "POST":
        check_csrf()
        user_id = flask.session["id"]
        if "yes" in flask.request.form:
            data.delete_user(user_id)
            return flask.redirect("/logout")
        return flask.redirect(f"/user/{user_id}")

@app.route("/new_post", methods=["GET", "POST"])
@require_login
def new_post():
    if flask.request.method == "GET":
        classes = data.get_classes()
        return flask.render_template("new_post.html", classes=classes)
    if flask.request.method == "POST":
        check_csrf()
        content = flask.request.form["content"]
        if not content or len(content) > 1000 or "class" not in flask.request.form:
            flask.abort(403)
        cs = flask.request.form["class"]
        user_id = flask.session["id"]
        try:
            data.new_post(content, cs, user_id)
        except sqlite3.IntegrityError:
            flask.abort(403)
        return flask.redirect("/")

@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@require_login
def edit_post(post_id):
    post = data.get_posts(post_id=post_id)
    if not post:
        flask.abort(404)
    if post["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        classes = data.get_classes()
        return flask.render_template("edit_post.html", post=post, classes=classes)
    if flask.request.method == "POST":
        check_csrf()
        content = flask.request.form["content"]
        if not content or len(content) > 1000 or "class" not in flask.request.form:
            flask.abort(403)
        cs = flask.request.form["class"]
        try:
            data.edit_post(content, cs, post_id)
        except sqlite3.IntegrityError:
            flask.abort(403)
        return flask.redirect("/")

@app.route("/delete_post/<int:post_id>", methods=["GET", "POST"])
@require_login
def delete_post(post_id):
    post = data.get_posts(post_id=post_id)
    if not post:
        flask.abort(404)
    if post["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("delete_post.html", post_id=post_id)
    if flask.request.method == "POST":
        check_csrf()
        if "yes" in flask.request.form:
            data.delete_post(post_id)
        return flask.redirect("/")

@app.route("/comments/<int:post_id>", methods=["GET", "POST"])
def comments(post_id):
    post = data.get_posts(post_id=post_id)
    cmmnts = data.get_comments(post_id=post_id)
    if not post:
        flask.abort(404)
    if flask.request.method == "GET":
        return flask.render_template("comments.html", post=post, comments=cmmnts)
    if flask.request.method == "POST":
        if "cancel" in flask.request.form:
            return flask.render_template("comments.html", post=post, comments=cmmnts)
        keyword = flask.request.form["keyword"]
        if not keyword or len(keyword) > 1000:
            flask.abort(403)
        cmmnts = data.get_comments(post_id=post_id, keyword=keyword)
        return flask.render_template("comments.html", post=post, comments=cmmnts, keyword=keyword)

@app.route("/new_comment/<int:post_id>", methods=["GET", "POST"])
@require_login
def new_comment(post_id):
    post = data.get_posts(post_id=post_id)
    if not post:
        flask.abort(404)
    if flask.request.method == "GET":
        return flask.render_template("new_comment.html", post_id=post_id)
    if flask.request.method == "POST":
        check_csrf()
        content = flask.request.form["content"]
        if not content or len(content) > 1000:
            flask.abort(403)
        user_id = flask.session["id"]
        data.new_comment(content, user_id, post_id)
        return flask.redirect(f"/comments/{post_id}")

@app.route("/edit_comment/<int:comment_id>", methods=["GET", "POST"])
@require_login
def edit_domment(comment_id):
    comment = data.get_comments(comment_id=comment_id)
    if not comment:
        flask.abort(404)
    if comment["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("edit_comment.html", comment=comment)
    if flask.request.method == "POST":
        check_csrf()
        content = flask.request.form["content"]
        if not content or len(content) > 1000:
            flask.abort(403)
        data.edit_comment(content, comment_id)
        return flask.redirect(f"/comments/{comment["post_id"]}")

@app.route("/delete_comment/<int:comment_id>", methods=["GET", "POST"])
@require_login
def delete_comment(comment_id):
    comment = data.get_comments(comment_id=comment_id)
    if not comment:
        flask.abort(404)
    if comment["user_id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("delete_comment.html", comment_id=comment_id)
    if flask.request.method == "POST":
        check_csrf()
        if "yes" in flask.request.form:
            data.delete_comment(comment_id)
    return flask.redirect(f"/comments/{comment["post_id"]}")


if __name__ == "__main__":
    app.run()
