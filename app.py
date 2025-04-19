import functools
import secrets

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

@app.route("/", methods=["GET", "POST"])
def index():
    if flask.request.method == "GET":
        posts = data.get_posts()
        return flask.render_template("index.html", posts=posts)
    if flask.request.method == "POST":
        if "cancel" in flask.request.form:
            return flask.redirect("/")
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
            data.new_user(username, pwhash)
        except:
            flask.flash("VIRHE: Käyttäjätunnus on varattu")
            return flask.render_template("register.html", filled=filled, next_page=next_page)
        flask.flash("Rekisteröityminen onnistui, kirjaudu sisään")
        return flask.render_template("login.html", filled={}, next_page=next_page)

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
        if security.check_password_hash(pwhash, password):
            flask.session["id"] = usr["id"]
            flask.session["username"] = username
            flask.session["csrf_token"] = secrets.token_hex(16)
            return flask.redirect(next_page)
        flask.flash("VIRHE: Väärä salasana")
        return flask.render_template("login.html", filled=filled, next_page=next_page)

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

@app.route("/delete_user/<int:user_id>", methods=["GET", "POST"])
@require_login
def delete_user(user_id):
    usr = data.get_users(user_id=user_id)
    if not usr:
        flask.abort(404)
    if usr["id"] != flask.session["id"]:
        flask.abort(403)
    if flask.request.method == "GET":
        return flask.render_template("delete_user.html", user_id=user_id)
    if flask.request.method == "POST":
        check_csrf()
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
        except:
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
        except:
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
    post = data.get_posts(post_id)
    if not post:
        flask.abort(404)
    if flask.request.method == "GET":
        cmmnts = data.get_comments(post_id=post_id)
        return flask.render_template("comments.html", post=post, comments=cmmnts)
    if flask.request.method == "POST":
        if "cancel" in flask.request.form:
            return flask.redirect(f"/comments/{post_id}")
        keyword = flask.request.form["keyword"]
        if not keyword or len(keyword) > 1000:
            flask.abort(403)
        cmmnts = data.get_comments(post_id=post_id, keyword=keyword)
        return flask.render_template("comments.html", post=post, comments=cmmnts, keyword=keyword)

@app.route("/new_comment/<int:post_id>", methods=["GET", "POST"])
@require_login
def new_comment(post_id):
    if not data.get_posts(post_id=post_id):
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
