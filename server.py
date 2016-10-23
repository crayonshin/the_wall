from flask import Flask, request, redirect, render_template, session, flash, escape
from mysqlconnection import MySQLConnector
from flask.ext.bcrypt import Bcrypt
import re
import datetime

app = Flask(__name__)
bcrypt = Bcrypt(app)
mysql = MySQLConnector(app,'the_wall')
app.secret_key = "wedontneednoeducation"
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$') # regex expression for email validation

@app.route("/")
def login_page():
    if "id" in session:
        return redirect("/thewall/"+session["email"])
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
        email = escape(request.form["email"]) # need to find out more about escape and when to use or not use it!!
        password = escape(request.form["password"])
        query = "SELECT * FROM users WHERE email = :email LIMIT 1"
        data = {"email": email}
        user = mysql.query_db(query, data)
        if request.form["action"] == "login":
            if not EMAIL_REGEX.match(email):
                flash("Please enter a valid email address.", "login_error")
                return redirect("/")
            if not user:
                flash(email+" is not registered.", "login_error")
                return redirect("/")
            elif bcrypt.check_password_hash(user[0]["password"], password):
                session["id"] = user[0]["id"]
                session["email"] = user[0]["email"]
                session["first_name"] = user[0]["first_name"]
                return redirect("/thewall/"+session["email"])
            else:
                flash("Please check login info and try again.", "login_error")
                return redirect("/")
        if request.form["action"] == "register":
            if request.form["first_name"] == "" or request.form["last_name"] == "" or email == "" or password == "" or request.form["vpassword"] == "":
                flash("Please fill out all fields.", "registration_error")
                return redirect("/")
            elif not EMAIL_REGEX.match(email):
                flash("Please enter a valid email address.", "registration_error")
                return redirect("/")
            elif user:
                flash(email+" is already registered.", "registration_error")
                return redirect("/")
            elif len(password) < 8:
                flash("Password must be at least 8 characters.", "registration_error")
                return redirect("/")
            elif password != request.form["vpassword"]:
                flash("Passwords do not match", "registration_error")
                return redirect("/")
            else:
                pw_hash = bcrypt.generate_password_hash(password)
                query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (:first_name, :last_name, :email, :password, NOW(), NOW())"
                data = {"first_name": request.form["first_name"], "last_name": request.form["last_name"], "email": email, "password": pw_hash}
                mysql.query_db(query, data) # this and above 2 lines will insert a new user into the DB
                get_id = "SELECT * FROM users WHERE email = :email LIMIT 1"
                get_id_data = {"email": email}
                id = mysql.query_db(get_id, get_id_data) # this and above 2 lines query the DB again looking for the newly created record so I can get the id to put in session
                session["id"] = id[0]["id"]
                session["email"] = id[0]["email"]
                session["first_name"] = id[0]["first_name"]
                return redirect("/thewall/"+session["email"])

@app.route("/thewall/<email>")
def main(email):
    if "id" not in session: # if session does not exist, redirect to login page
        # session.clear()
        return redirect("/")
    elif session["email"] != email: #if session does exist but user tried to access somebody else's URL, clear session and redirect to login page
        session.clear()
        return redirect("/")
    # query = "SELECT * FROM users JOIN messages ON users.id = messages.user_id ORDER BY messages.created_at DESC"
    query = "SELECT messages.id, message, messages.created_at, users.id as user_id, users.first_name as first_name, users.last_name as last_name FROM messages JOIN users ON messages.user_id = users.id ORDER BY created_at DESC";
    messages = mysql.query_db(query)
    # query = "SELECT message,comment FROM messages JOIN comments ON messages.id = comments.message_id ORDER BY comments.created_at ASC"
    query = "SELECT comments.id, message_id, comment, comments.created_at, users.id as user_id, users.first_name as first_name, users.last_name as last_name FROM comments JOIN users ON comments.user_id = users.id"
    comments = mysql.query_db(query)
    currentTime = datetime.datetime.now()
    return render_template("thewall.html", messages=messages, comments=comments, currentTime = currentTime)

@app.route("/newmessage", methods=["POST"])
def newmessage():
    if len(request.form["newmessage"]) < 1:
        flash("** New Message cannot be blank. **")
        return redirect("/thewall/"+session["email"])
    query = "INSERT INTO messages (message, user_id, created_at, updated_at) VALUES (:message, :user_id, NOW(), NOW())"
    data = {"message": request.form["newmessage"], "user_id": session["id"]}
    mysql.query_db(query, data)
    return redirect("/")

@app.route("/newcomment", methods=["POST"])
def newcomment():
    if len(request.form["newcomment"]) < 1:
        flash("** New Comment cannot be blank. **")
        return redirect("/thewall/"+session["email"])
    query = "INSERT INTO comments (comment, user_id, message_id, created_at, updated_at) VALUES (:comment, :user_id, :message_id, NOW(), NOW())"
    data = {"comment": request.form["newcomment"], "user_id": session["id"], "message_id": request.form["message_id"]}
    mysql.query_db(query, data)
    return redirect("/")

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("id", None)
    return redirect("/")

@app.route("/delete_message", methods=["POST"])
def delete_message():
    query = "SELECT created_at FROM messages WHERE id = :id";
    data = {"id": request.form["message_id"]}
    messageTime = mysql.query_db(query, data)
    if ((datetime.datetime.now() - messageTime[0]["created_at"]).seconds) / 60 > 29:
        flash("** Messages older than 30 minutes cannot be deleted. **")
        return redirect("/")
    query = "DELETE FROM comments where message_id = :id; DELETE FROM messages WHERE id = :id"
    data = {"id": request.form["message_id"]}
    mysql.query_db(query, data)
    return redirect("/")

app.run(debug=True)
