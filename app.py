import functools
import secrets
import sqlite3
import time
import string

import flask
import markupsafe
from werkzeug import security
from werkzeug.middleware import proxy_fix

import config
import data

app = flask.Flask(__name__)
app.secret_key = config.SECRET_KEY
app.wsgi_app = proxy_fix.ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
PAGE_SIZE = 10
ASCII = string.printable + "öäåÖÄÅ"

@app.before_request
def before_request():
    flask.g.start_time = time.time()

@app.after_request
def after_request(response):
    elapsed_time = time.time() - flask.g.start_time
    if elapsed_time > 1:
        print(f"Response taking over a second ({round(elapsed_time, 2)} s)")
    return response

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

def get_keys(keys):
    values = []
    for key in keys:
        if key not in flask.request.form:
            flask.abort(403)
        values.append(flask.request.form[key])
    return values[0] if len(values) == 1 else values

def check_permission(user_id):
    if user_id != flask.session["id"] and not flask.session["admin"]:
        flask.abort(403)

def check_string(string):
    return all(char in ASCII for char in string)

def create_session(user_id, username, admin=False):
    flask.session["id"] = user_id
    flask.session["username"] = username
    flask.session["admin"] = admin
    flask.session["csrf_token"] = secrets.token_hex()

@app.route("/")
def index():
    if "keyword" in flask.request.args:
        keyword = flask.request.args.get("keyword")
        if not 0 < len(keyword) <= 1000:
            flask.abort(403)
        if "content" in flask.request.args and "username" not in flask.request.args:
            keyword = {"keyword": keyword, "type": "content"}
        elif "content" not in flask.request.args and "username" in flask.request.args:
            keyword = {"keyword": keyword, "type": "username"}
        else:
            flask.abort(403)
    else:
        keyword = None
    page_count = data.get_post_pages(PAGE_SIZE, keyword=keyword)
    page = int(flask.request.args.get("page", 1))
    if page < 1 or page > page_count:
        flask.abort(404)
    page = {"page": page, "size": PAGE_SIZE, "count": page_count} if page_count > 1 else None
    posts = data.get_posts(keyword=keyword, page=page)
    return flask.render_template("index.html", posts=posts, page=page, keyword=keyword)

@app.route("/register", methods=["GET", "POST"])
def register():
    if flask.request.method == "GET":
        next_page = flask.request.args.get("next_page", flask.request.referrer)
        return flask.render_template("register.html", filled={}, next_page=next_page)
    if flask.request.method == "POST":
        next_page = get_keys(["next_page"])
        username, password1, password2 = get_keys(["username", "password1", "password2"])
        if not (username and password1 and password2) or max(len(username), len(password1), len(password2)) > 20:
            flask.abort(403)
        filled = {"username": username}
        if not check_string(username):
            flask.flash("VIRHE: Käyttäjänimessä ei-sallittuja merkkejä")
            return flask.render_template("register.html", filled=filled, next_page=next_page)
        if password1 != password2:
            flask.flash("VIRHE: Salasanat eivät täsmää")
            return flask.render_template("register.html", filled=filled, next_page=next_page)
        pwhash = security.generate_password_hash(password1)
        try:
            user_id = data.new_user(username, pwhash)
        except sqlite3.IntegrityError:
            flask.flash("VIRHE: Käyttäjätunnus on varattu")
            return flask.render_template("register.html", filled=filled, next_page=next_page)
        if username == "admin":
            data.make_admin(user_id)
            create_session(user_id, username, admin=True)
        else:
            create_session(user_id, username)
        return flask.redirect(next_page)

@app.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "GET":
        next_page = flask.request.args.get("next_page", flask.request.referrer)
        return flask.render_template("login.html", filled={}, next_page=next_page)
    if flask.request.method == "POST":
        next_page = get_keys(["next_page"])
        username, password = get_keys(["username", "password"])
        if not username or not password or len(username) > 20 or len(password) > 20:
            flask.abort(403)
        filled = {"username": username}
        if not check_string(username):
            flask.flash("VIRHE: Käyttäjänimessä ei-sallittuja merkkejä")
            return flask.render_template("register.html", filled=filled, next_page=next_page)
        usr = data.get_users(username=username)
        pwhash = usr["pwhash"] if usr else None
        if not pwhash:
            flask.flash("VIRHE: Käyttäjätunnusta ei löydy")
            return flask.render_template("login.html", filled=filled, next_page=next_page)
        if not security.check_password_hash(pwhash, password):
            flask.flash("VIRHE: Väärä salasana")
            return flask.render_template("login.html", filled=filled, next_page=next_page)
        create_session(usr["id"], username, admin=bool(usr["admin"]))
        return flask.redirect(next_page)

@app.route("/logout")
def logout():
    flask.session.pop("id", None)
    flask.session.pop("username", None)
    flask.session.pop("admin", None)
    flask.session.pop("csrf_token", None)
    return flask.redirect("/")

@app.route("/user/<int:user_id>")
def user(user_id):
    try:
        usr = data.get_users(user_id=user_id)
    except OverflowError:
        flask.abort(404)
    if not usr:
        flask.abort(404)
    return flask.render_template("user.html", user=usr)

@app.route("/add_image/<int:user_id>", methods=["GET", "POST"])
@require_login
def add_image(user_id):
    try:
        usr = data.get_users(user_id=user_id)
    except OverflowError:
        flask.abort(404)
    if not usr:
        flask.abort(404)
    check_permission(user_id)
    if flask.request.method == "GET":
        return flask.render_template("add_image.html", user_id=user_id)
    if flask.request.method == "POST":
        check_csrf()
        file = flask.request.files["new_image"]
        if not file:
            data.add_image(None, user_id)
            return flask.redirect(f"/user/{user_id}")
        if not file.filename.endswith(".jpg"):
            flask.abort(403)
        image = file.read()
        if len(image) > 1000 * 1024:
            flask.flash("VIRHE: Liian suuri kuva")
            return flask.render_template("add_image.html", user_id=user_id)
        data.add_image(image, user_id)
        return flask.redirect(f"/user/{user_id}")

@app.route("/show_image/<int:user_id>")
def show_image(user_id):
    try:
        image = data.get_image(user_id)
    except OverflowError:
        flask.abort(404)
    if not image:
        flask.abort(404)
    response = flask.make_response(image)
    response.headers.set("Content-Type", "image/jpeg")
    return response

@app.route("/change_password/<int:user_id>", methods=["GET", "POST"])
@require_login
def change_password(user_id):
    try:
        usr = data.get_users(user_id=user_id)
    except OverflowError:
        flask.abort(404)
    if not usr:
        flask.abort(404)
    check_permission(user_id)
    if flask.request.method == "GET":
        return flask.render_template("change_password.html", user_id=user_id)
    if flask.request.method == "POST":
        check_csrf()
        old_password, password1, password2 = get_keys(["old_password", "password1", "password2"])
        if not (old_password and password1 and password2) or max(len(old_password), len(password1), len(password2)) > 20:
            flask.abort(403)
        if password1 != password2:
            flask.flash("VIRHE: Salasanat eivät täsmää")
            return flask.render_template("change_password.html", user_id=user_id)
        if old_password == password1:
            flask.flash("VIRHE: Salasana on sama kuin aiemmin")
            return flask.render_template("change_password.html", user_id=user_id)
        if not security.check_password_hash(usr["pwhash"], old_password):
            flask.flash("VIRHE: Väärä salasana")
            return flask.render_template("change_password.html", user_id=user_id)
        pwhash = security.generate_password_hash(password1)
        data.change_password(pwhash, user_id)
        flask.flash("Salasanan vaihto onnistui")
        return flask.redirect(f"/user/{user_id}")

@app.route("/delete_user/<int:user_id>", methods=["GET", "POST"])
@require_login
def delete_user(user_id):
    try:
        usr = data.get_users(user_id=user_id)
    except OverflowError:
        flask.abort(404)
    if not usr:
        flask.abort(404)
    check_permission(user_id)
    if flask.request.method == "GET":
        return flask.render_template("delete_user.html", user_id=user_id)
    if flask.request.method == "POST":
        check_csrf()
        if "yes" in flask.request.form:
            data.delete_user(user_id)
            if user_id != flask.session["id"]:
                return flask.redirect("/")
            return flask.redirect("/logout")
        return flask.redirect(f"/user/{user_id}")

@app.route("/new_post", methods=["GET", "POST"])
@require_login
def new_post():
    classes = data.get_classes()
    if flask.request.method == "GET":
        return flask.render_template("new_post.html", classes=classes, filled={})
    if flask.request.method == "POST":
        check_csrf()
        content, cs = get_keys(["content", "class"])
        if not 0 < len(content) <= 1000:
            flask.abort(403)
        if not check_string(content):
            filled = {"content": content, "class": cs}
            flask.flash("VIRHE: Postauksessa ei-sallittuja merkkejä")
            return flask.render_template("new_post.html", classes=classes, filled=filled)
        user_id = flask.session["id"]
        try:
            data.new_post(content, user_id, cs)
        except sqlite3.IntegrityError:
            flask.abort(403)
        return flask.redirect("/")

@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@require_login
def edit_post(post_id):
    try:
        post = data.get_posts(post_id=post_id)
    except OverflowError:
        flask.abort(404)
    if not post:
        flask.abort(404)
    check_permission(post["user_id"])
    classes = data.get_classes()
    if flask.request.method == "GET":
        filled = {"content": post["content"], "class": post["class_id"]}
        return flask.render_template("edit_post.html", post_id=post_id, classes=classes, filled=filled)
    if flask.request.method == "POST":
        check_csrf()
        content, cs = get_keys(["content", "class"])
        if not 0 < len(content) <= 1000:
            flask.abort(403)
        if not check_string(content):
            filled = {"content": content, "class": cs}
            flask.flash("VIRHE: Postauksessa ei-sallittuja merkkejä")
            return flask.render_template("edit_post.html", post_id=post_id, classes=classes, filled=filled)
        try:
            data.edit_post(content, cs, post_id)
        except sqlite3.IntegrityError:
            flask.abort(403)
        return flask.redirect("/")

@app.route("/delete_post/<int:post_id>", methods=["GET", "POST"])
@require_login
def delete_post(post_id):
    try:
        post = data.get_posts(post_id=post_id)
    except OverflowError:
        flask.abort(404)
    if not post:
        flask.abort(404)
    check_permission(post["user_id"])
    if flask.request.method == "GET":
        return flask.render_template("delete_post.html", post_id=post_id)
    if flask.request.method == "POST":
        check_csrf()
        if "yes" in flask.request.form:
            data.delete_post(post_id)
        return flask.redirect("/")

@app.route("/comments")
@app.route("/comments/<int:post_id>")
def comments(post_id=None):
    if post_id is not None:
        try:
            post = data.get_posts(post_id=post_id)
        except OverflowError:
            flask.abort(404)
        if not post:
            flask.abort(404)
    else:
        post = None
    if "keyword" in flask.request.args:
        keyword = flask.request.args.get("keyword")
        if not 0 < len(keyword) <= 1000:
            flask.abort(403)
        if "content" in flask.request.args and "username" not in flask.request.args:
            keyword = {"keyword": keyword, "type": "content"}
        elif "content" not in flask.request.args and "username" in flask.request.args:
            keyword = {"keyword": keyword, "type": "username"}
        else:
            flask.abort(403)
    else:
        keyword = None
    page_count = data.get_comment_pages(PAGE_SIZE, keyword=keyword, post_id=post_id)
    page = int(flask.request.args.get("page", 1))
    if page < 1 or page > page_count:
        flask.abort(404)
    page = {"page": page, "size": PAGE_SIZE, "count": page_count} if page_count > 1 else None
    cmmnts = data.get_comments(post_id=post_id, keyword=keyword, page=page)
    return flask.render_template("comments.html", post=post, comments=cmmnts, page=page, keyword=keyword)

@app.route("/new_comment/<int:post_id>", methods=["GET", "POST"])
@require_login
def new_comment(post_id):
    try:
        post = data.get_posts(post_id=post_id)
    except OverflowError:
        flask.abort(404)
    if not post:
        flask.abort(404)
    if flask.request.method == "GET":
        return flask.render_template("new_comment.html", post_id=post_id, filled={})
    if flask.request.method == "POST":
        check_csrf()
        content = get_keys(["content"])
        if not 0 < len(content) <= 1000:
            flask.abort(403)
        if not check_string(content):
            filled = {"content": content}
            flask.flash("VIRHE: Kommentissa ei-sallittuja merkkejä")
            return flask.render_template("new_comment.html", post_id=post_id, filled=filled)
        user_id = flask.session["id"]
        data.new_comment(content, user_id, post_id)
        return flask.redirect(f"/comments/{post_id}")

@app.route("/edit_comment/<int:comment_id>", methods=["GET", "POST"])
@require_login
def edit_domment(comment_id):
    try:
        comment = data.get_comments(comment_id=comment_id)
    except OverflowError:
        flask.abort(404)
    if not comment:
        flask.abort(404)
    check_permission(comment["user_id"])
    if flask.request.method == "GET":
        return flask.render_template("edit_comment.html", comment=comment, filled={})
    if flask.request.method == "POST":
        check_csrf()
        content = get_keys(["content"])
        if not 0 < len(content) <= 1000:
            flask.abort(403)
        if not check_string(content):
            filled = {"content": content}
            flask.flash("VIRHE: Kommentissa ei-sallittuja merkkejä")
            return flask.render_template("edit_comment.html", comment=comment, filled=filled)
        data.edit_comment(content, comment_id)
        return flask.redirect(f"/comments/{comment["post_id"]}")

@app.route("/delete_comment/<int:comment_id>", methods=["GET", "POST"])
@require_login
def delete_comment(comment_id):
    try:
        comment = data.get_comments(comment_id=comment_id)
    except OverflowError:
        flask.abort(404)
    if not comment:
        flask.abort(404)
    check_permission(comment["user_id"])
    if flask.request.method == "GET":
        return flask.render_template("delete_comment.html", comment_id=comment_id)
    if flask.request.method == "POST":
        check_csrf()
        if "yes" in flask.request.form:
            data.delete_comment(comment_id)
    return flask.redirect(f"/comments/{comment["post_id"]}")


if __name__ == "__main__":
    app.run()
