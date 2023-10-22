from flask import Flask, render_template, url_for, request, redirect, session, g
from werkzeug.security import check_password_hash, generate_password_hash
import csv
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = "OCML3BRawWEUeaxcuKHLpw"

DATABASE = 'data.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route("/", methods=["GET", "POST"])
def index():
    items = query_db('select * from items')
    if 'email' in session.keys():
        return render_template('index.html', items=items, logged=True, userID=session['userID'], balance=session['balance'])
    else:
        return render_template('index.html', items=items)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get('email')
        password = request.form.get('password')

        user = query_db('select * from accounts where email = ?', [email], one=True)
        if user is not None and check_password_hash(user["password"], password):
            session['userID'] = user['userID']
            session['email'] = user['email']
            user = query_db('select * from user_info where email = ?', [email], one=True)
            session['name'] = user['name']
            session['balance'] = user['balance']
            return profile()
        else:
            return render_template('login.html', wrong=True)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        email = request.form.get('email')

        same_email = query_db('select * from accounts where email = ?', [email], one=True)
        if same_email is not None:
            return render_template('register.html', taken=True, email=email)

        password = request.form.get('password')
        password2 = request.form.get('password2')

        if password != password2:
            return render_template('register.html', mismatch=True)

        name = request.form.get('first') + " " + request.form.get('last')

        query_db('insert into accounts ("email", "password") VALUES (?,?)', (email, generate_password_hash(password)))
        query_db('insert into user_info ("email", "name", "balance") VALUES (?,?,?)', (email, name, 0))
        get_db().commit()

        user = query_db('select * from accounts where email = ?', [email], one=True)
        session['userID'] = user['userID']
        session['email'] = email
        session['name'] = name
        session['balance'] = 0
        return index()
    else:
        return render_template("register.html")

@app.route("/profile")
def profile():
    items = query_db('select * from items where userID = ?', [session['userID']])
    return render_template('profile.html', email=session['email'], name=session['name'], balance=session['balance'], items=items)

@app.route("/logout")
def logout():
    session.pop('userID', None)
    session.pop('email', None)
    session.pop('name', None)
    session.pop('balance', None)
    return index()

@app.route("/addBalance", methods=["GET", "POST"])
def addBalance():
    if (request.form.get('addBalance') != None):
        add = float(request.form.get('addBalance'))
        session['balance'] = session['balance'] + add
        query_db('update user_info set balance = ? where email = ?', (session['balance'], session['email']))
        get_db().commit()
    return profile()

@app.route("/addListing", methods=["GET", "POST"])
def addListing():
    if request.method == "POST":
        item = request.form.get('item')
        price = request.form.get('price')

        query_db('insert into items ("item", "seller", "price", "userID") VALUES (?,?,?,?)', (item, session['name'], price, session['userID']))
        get_db().commit()
        return profile()
    else:
        return render_template('create.html')

@app.route("/removeListing")
def removeListing():
    itemID = request.args.get('itemID')
    query_db('delete from items where itemID = ?', [itemID])
    get_db().commit()
    return profile()

@app.route("/buy")
def buy():
    item_price = float(request.args.get('item_price'))
    itemID = request.args.get('itemID')
    sellerID = request.args.get('sellerID')

    # remove money from buyer
    session['balance'] = session['balance'] - item_price
    query_db('update user_info set balance = ? where userID = ?', (session['balance'], session['userID']))
    # add money to seller
    seller = query_db('select * from user_info where userID = ?', [sellerID], one=True)
    seller_balance = seller['balance'] + item_price
    query_db('update user_info set balance = ? where userID = ?', (seller_balance, sellerID))
    # remove item from store
    query_db('delete from items where itemID = ?', [itemID])

    get_db().commit()
    return index()
