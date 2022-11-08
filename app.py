import os
import random

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, partition

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///seatingchart.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def index():
    # Show homepage
    return render_template("index.html")

@app.route("/add_class", methods=["POST"])
@login_required
def add_class():
    # Add a class
    # Check for class field
    if not request.form.get("class"):
        return apology("please enter class name", 400)

    # Check for subject field
    if not request.form.get("subject"):
        return apology("please enter subject", 400)

    # Check for unique class name
    classname = db.execute("SELECT * FROM classes WHERE class = ?", request.form.get("class"))
    if len(classname) != 0:
        return apology("class name already used", 400)

    # Add class to database
    db.execute(
        "INSERT INTO classes (class, subject, teacher) VALUES (?, ?, ?)", request.form.get("class"), request.form.get("subject"), session["user_id"]
        )
    return redirect("/classes")

@app.route("/add_student", methods=["GET", "POST"])
@login_required
def add_student():
    # Add students to a class

    # If user reaches via POST
    if request.method == "POST":
        
        # If name or class is left blank
        if not request.form.get("name") or not request.form.get("class"):
            return apology("Enter name and class", 400)

        # Select for class ID
        period = db.execute("SELECT id FROM classes WHERE class = ? AND teacher = ?", request.form.get("class"), session["user_id"])
        period = int(period[0]["id"])
        
        # If class ID does not exist
        if not period:
            return apology("Class has not been created yet", 400)

        # Successfully add student
        else:
            flash("Student added!")            
            db.execute(
                "INSERT INTO students (name, class, teacher) VALUES (?, ?, ?)", request.form.get("name"), period, session["user_id"]
            )
            return redirect("/classes")

    else:
        return render_template("addstudent.html")

@app.route("/archive", methods=["POST"])
@login_required
def archive():
    # Get class id
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]
    yes = "yes"

    # Archive class
    db.execute("UPDATE classes SET archived = ? WHERE id = ?", yes, periodx)
    flash("Class archived.")
    return redirect("/classes")

@app.route("/classes")
@login_required
def classes():
    # Show teacher's active classes
    # Pull classes from database
    teacher = db.execute(
        "SELECT * FROM users WHERE id = ?", session["user_id"]
    )
    name = teacher[0]["usercase"]    

    classes = db.execute(
        "SELECT * FROM classes WHERE teacher = ? AND archived = ?", session["user_id"], "no"
    )

    archived = db.execute("SELECT * FROM classes WHERE teacher = ? AND archived = ?", session["user_id"], "yes")

    # If there are no classes
    if not classes:
        message = "You have not entered any classes"
        return render_template("classes.html", name=name, message=message)
    
    else:
        message = "Here are you classes"
        return render_template("classes.html", archived=archived, name=name, message=message, classes=classes)               
    
@app.route("/delete", methods=["POST"])
@login_required
def delete():
    # Confirm choice
    # """todo"""

    # Delete student
    period = request.args.get("period")
    student = request.args.get("studentid")
    db.execute("DELETE FROM students WHERE id = ?", student)
    flash("Student deleted.")
    return redirect("/edit?period=" + period)

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    # Group students  
    
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]
    classname = period_id[0]["class"]                
    students = db.execute("SELECT * FROM students WHERE class = ?", periodx)
    genders = db.execute("SELECT * FROM gender")
    
    return render_template("edit.html", name=name, period=period, classname=classname, students=students, genders=genders)    

@app.route("/group", methods=["GET", "POST"])
@login_required
def group():
    # Group students

    # User reaches via POST
    if request.method == "POST":
        teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        name = teacher[0]["usercase"]
        period = request.args.get("period")        
        period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
        periodx = period_id[0]["id"]
        classname = period_id[0]["class"]                
        students = db.execute("SELECT * FROM students WHERE class = ?", periodx)
      
        return render_template("group.html", name=name, period=period, classname=classname, students=students)

    # User reaches via GET
    else:
        return apology("TODO")       

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        username = request.form.get("username").lower()
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/classes")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to homepage
    return redirect("/")

@app.route("/randomize", methods=["POST"])
@login_required
def randomize():
    """Create random groups based on input"""
    # Get specific class       
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")
    classname = period        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]     

    # Get list of students and turn them into a list           
    students = db.execute("SELECT * FROM students WHERE class = ?", periodx)
    student_lst = []
    for i in range(len(students)):
        student_lst.append(students[i]["name"])

    # Make random groups
    random.shuffle(student_lst)
    groups = partition(student_lst, 4)

    return render_template("randomize.html", classname=classname, groups=groups, name=name, period=period, students=students)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation", 400)

        # Ensure username is unique
        username = request.form.get("username").lower()
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 0:
            return apology("username already taken", 400)

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        # Hash password
        hash = generate_password_hash(request.form.get("password"), method="pbkdf2:sha256", salt_length=8)

        # Add user to database
        usercase = request.form.get("username")
        db.execute("INSERT INTO users (username, hash, usercase) VALUES(?, ?, ?)", username, hash, usercase)

        # Log the user in
        current = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = current[0]["id"]

        return redirect("/")

    # User reaches route via GET
    else:
        return render_template("register.html")

@app.route("/restore", methods=["POST"])
@login_required
def restore():
    # Restore a class from archives
    # Get class id
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]
    no = "no"

    # Restore class
    db.execute("UPDATE classes SET archived = ? WHERE id = ?", no, periodx)
    flash("Class restored.")
    
    return redirect("/classes")
