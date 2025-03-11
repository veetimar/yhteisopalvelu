import flask
from database import Database

app = flask.Flask(__name__)

@app.route("/")
def index():
    return flask.render_template("index.html")