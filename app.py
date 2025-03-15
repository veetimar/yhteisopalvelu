import flask, config
from database import Database

app = flask.Flask(__name__)
app.secret_key = config.SECRET_KEY

@app.route("/")
def index():
    with Database() as db:
        db.execute("INSERT INTO Visits (time) VALUES (datetime('now'))", commit=True)
        visits = db.query("SELECT COUNT(*) FROM Visits", one=True)[0]
    return flask.render_template("index.html", visits=visits)

@app.route("/register")
def register():
    return flask.render_template("register.html")

@app.route("/create_account", methods=["POST"])
def create_account():
    return flask.redirect("/")

@app.route("/login")
def login():
    return flask.render_template("login.html")

@app.route("/create_session", methods=["POST"])
def create_session():
    return flask.redirect("/")

@app.route("/logout")
def logout():
    if "username" in flask.session:
        del flask.session["username"]
    return flask.redirect("/")
