import flask
from database import Database

app = flask.Flask(__name__)

@app.route("/")
def index():
    with Database() as db:
        db.execute("INSERT INTO Visits (time) VALUES (datetime('now'))", commit=True)
        times = db.query("SELECT COUNT(*) FROM Visits", one=True)[0]
    return flask.render_template("index.html", times=times)

@app.route("/register")
def register():
    return flask.render_template("register.html")

@app.route("/login")
def login():
    return flask.render_template("login.html")