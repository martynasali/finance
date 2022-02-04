import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
# pk_8987dc7d88b94ad3b8344fb2ae557a44
# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    # info = db.execute("SELECT * FROM stocks WHERE user_id = ?", session["user_id"])
    info = db.execute("SELECT stock_name, SUM(amount) FROM stocks WHERE user_id = ? GROUP BY symbol", session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    cash = cash[0]['cash']
    total_cash = cash
    simbol = db.execute("SELECT symbol FROM stocks WHERE user_id = ? GROUP BY symbol", session["user_id"])

    print(simbol)
    current = []
    neiu = []
    all = []
    for sim in simbol:
        current = (lookup(sim['symbol']))
        neiu.append(current['price'])
    i = 0
    for inf in info:
        inf["price"] = neiu[i]
        total_cash += (neiu[i] * inf['SUM(amount)'])
        i += 1
    print(info)

    return render_template("index.html", INFO=info, cash=cash, total_cash=total_cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:

        if not request.form.get("shares").isnumeric():
            return apology("thats not a number", 400)

        if not int(request.form.get("shares")) > 0:
            return apology("Wrong share count", 400)
        symbol = request.form.get("symbol")
        quantity = int(request.form.get("shares"))
        price = lookup(symbol.upper())
        if not price:
            return apology("Stock by that name does not exist", 400)
        print("price", price)
        stock_name = price["name"]
        price = float(price["price"])
        total = float(quantity * price)
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = float(cash[0]["cash"])
        if total > cash:
            return apology("You don't have enough money", 400)
        cash = float(cash - total)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash,  session["user_id"])

        exists = db.execute("SELECT symbol, amount  FROM stocks WHERE symbol = ? and user_id = ?", symbol.upper(), session["user_id"])
        if exists:
            exists[0]['amount'] += quantity
            db.execute("UPDATE stocks SET amount = ? WHERE symbol = ? and user_id = ?", exists[0]['amount'], symbol.upper(), session["user_id"])
            db.execute("INSERT INTO history (symbol, amount, action, price, stock_name, total_price, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       symbol.upper(), quantity, "bought", price, stock_name, total, session["user_id"])
            return redirect("/")

        db.execute("INSERT INTO stocks (symbol, amount, status, price, stock_name, total_price, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   symbol.upper(), quantity, True, price, stock_name, total, session["user_id"])
        db.execute("INSERT INTO history (symbol, amount, action, price, stock_name, total_price, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   symbol.upper(), quantity, "bought", price, stock_name, total, session["user_id"])
        return redirect("/")


@app.route("/history")
@login_required
def history():
    datas = db.execute("SELECT * FROM history")
    return render_template("history.html", datas=datas)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "GET":
        return render_template("add_cash.html")
    else:
        if not request.form.get("money").isnumeric():
            return apology("thats not a number", 400)
        money = int(request.form.get("money"))
        curr_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        curr_cash = float(curr_cash[0]["cash"])
        db.execute("UPDATE users SET cash = ? WHERE id = ?", (curr_cash+money),  session["user_id"])
        return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        stocks = lookup(symbol.upper())
        if not stocks:
            return apology("stock does not exist", 400)
        return render_template("quoted.html", stocks=stocks)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":

        # Ensure username, password, confirmation was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        if not request.form.get("password"):
            return apology("must provide password", 400)

        if not request.form.get("confirmation"):
            return apology("must provide confirmation", 400)

        # Check if there is no same username
        nameuser = []
        nameuser = db.execute(
            "SELECT username FROM users WHERE username = ?", request.form.get("username"))
        if nameuser:
            return apology("username already exists", 400)

        # Ensure passwords match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)
        else:
            passw = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)",
                       request.form.get("username"), passw)
            return redirect("/")

    else:
        return render_template("register.html")


@ app.route("/sell", methods=["GET", "POST"])
@ login_required
def sell():
    if request.method == "GET":
        stocks = db.execute("SELECT symbol  FROM stocks WHERE user_id = ?", session["user_id"])
        return render_template("sell.html", stocks=stocks)

    else:
        if not request.form.get("shares"):
            return apology("Stock count not entered")
        if not request.form.get("symbol"):
            return apology("Share not selected")
        amount = db.execute("SELECT amount FROM stocks WHERE user_id = ? and symbol = ?", session["user_id"], request.form.get("symbol"))
        symbol = request.form.get("symbol").upper()
        price = lookup(symbol)
        price = price["price"]
        print(amount)
        curr_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        curr_cash = curr_cash[0]["cash"]
        if not amount:
            return apology("You don't have this share")
        if int(amount[0]['amount']) < int(request.form.get("shares")):
            return apology("You don't have enougth shares")
        all = db.execute("SELECT * FROM stocks WHERE user_id = ? and symbol = ?", session["user_id"], request.form.get("symbol"))
        if int(request.form.get("shares")) == int(amount[0]['amount']):
            db.execute("DELETE FROM stocks WHERE user_id = ? and symbol = ?", session["user_id"], request.form.get("symbol"))
            print("all:", all)
            db.execute("INSERT INTO history (symbol, amount, action, price, stock_name, total_price, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       symbol.upper(), int(request.form.get("shares")), "sold", price, all[0]['stock_name'], (price * int(request.form.get("shares"))), session["user_id"])
            cash = int(request.form.get("shares")) * float(price)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", (curr_cash+cash),  session["user_id"])

        if int(request.form.get("shares")) < int(amount[0]['amount']):
            left = int(amount[0]['amount']) - int(request.form.get("shares"))
            db.execute("UPDATE stocks SET amount = ? WHERE symbol = ? and user_id = ?", left, symbol.upper(), session["user_id"])
            db.execute("INSERT INTO history (symbol, amount, action, price, stock_name, total_price, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       symbol.upper(), int(request.form.get("shares")), "sold", price, all[0]['stock_name'], (price * int(request.form.get("shares"))), session["user_id"])
            cash = int(request.form.get("shares")) * float(price)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", (curr_cash+cash),  session["user_id"])
            # update line, update total cash
            # add line to history

            # db.execute("UPDATE stocks SET amount = ? WHERE symbol = ? and user_id = ?", exists[0]['amount'], .upper(), session["user_id"])

            # db.execute("")

        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
