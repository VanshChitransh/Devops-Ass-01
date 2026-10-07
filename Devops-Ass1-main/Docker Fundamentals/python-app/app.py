from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    return "<h1>Hello World from Vansh's Python (Flask) app!</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
