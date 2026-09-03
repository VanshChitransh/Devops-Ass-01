from flask import Flask

server = Flask(__name__)


@server.route("/")
def landing():
    return "<h1>Hello World from Vansh's Python (Flask) app!</h1>"


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=5000)
