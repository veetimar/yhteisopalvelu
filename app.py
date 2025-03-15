import flask, werkzeug.security as sec
from config import SECRET_KEY
from database import Database

app = flask.Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def index():
    with Database() as db:
        db.execute("INSERT INTO Visits (time) VALUES (datetime('now'))", commit=True)
        visits = db.query("SELECT COUNT(*) FROM Visits", one=True)[0]
    return flask.render_template("index.html", visits=visits)

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
    pwhash = sec.generate_password_hash(password1)
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
    if pwhash and sec.check_password_hash(pwhash, password):
        flask.session["username"] = username
        return flask.redirect("/")
    flask.session["message"] = "VIRHE: Väärä käyttäjätunnus tai salasana"
    return flask.redirect("/login")

@app.route("/logout")
def logout():
    flask.session.pop("username", None)
    return flask.redirect("/")
