from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scratchpad.html")
def scratchpad():
    return render_template("scratchpad.html")


@app.route("/calculator.html")
def calculator():
    return render_template("calculator.html")


@app.route("/password.html")
def password():
    return render_template("password.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4399)
