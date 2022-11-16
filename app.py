import os
import random

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, chunk, login_required, partition

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
        classes = db.execute("SELECT class FROM classes WHERE teacher = ?", session["user_id"])
        genders = db.execute("SELECT gender FROM gender")
        return render_template("addstudent.html", classes=classes, genders=genders)

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

@app.route("/differentiated", methods=["POST"])
@login_required
def differentiated():
    # Group students by score

    # Get specific class
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")
    classname = period        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]  

    # Get student list sorted by score
    students = db.execute("SELECT * FROM students WHERE class = ? ORDER BY score DESC", periodx)    

    # Group students by score       
    groupnum = int(round(len(students) / 4))
    groups = partition(students, groupnum)

    return render_template("randomize.html", classname=classname, groups=groups, name=name, period=period, students=students)

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
    classes = db.execute("SELECT * FROM classes WHERE teacher = ?", session["user_id"])
    
    return render_template("edit.html", name=name, period=period, classname=classname, students=students, genders=genders, classes=classes)    

@app.route("/gender_hetero", methods=["POST"])
@login_required
def gender_hetero():
    # Create random groups heterogeneous by gender

    # Get specific class       
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")
    classname = period        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]        

    # Initialize student list
    student_lst = []
    
    # Get list of male students
    males = db.execute("SELECT * FROM students WHERE class = ? AND gender IN (SELECT id FROM gender WHERE gender = ?)", periodx, "Male")
    
    # Get list of female students
    females = db.execute("SELECT * FROM students WHERE class = ? AND gender IN (SELECT id FROM gender WHERE gender = ?)", periodx, "Female")
    
    # Shuffle lists separately and extend
    random.shuffle(males)
    random.shuffle(females)

    ml = len(males)
    fl = len(females)

    for i in range(max(ml, fl)):
        if i < ml:
            student_lst.append(males[i])
        if i < fl:
            student_lst.append(females[i])           

    # Make groups    
    groupnum = int(round(len(student_lst) / 4))
    groups = partition(student_lst, groupnum)

    return render_template("randomize.html", classname=classname, groups=groups, name=name, period=period)

@app.route("/gender_homo", methods=["POST"])
@login_required
def gender_homo():
    # Create random groups homogeneous by gender

    # Get specific class       
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")
    classname = period        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]        

    # Set up list of students      
    student_lst = []
    
    # Get list of male students
    males = db.execute("SELECT * FROM students WHERE class = ? AND gender IN (SELECT id FROM gender WHERE gender = ?)", periodx, "Male")
    random.shuffle(males)    
    for i in range(len(males)):
        student_lst.append(males[i])  

    # Get list of female students
    females = db.execute("SELECT * FROM students WHERE class = ? AND gender IN (SELECT id FROM gender WHERE gender = ?)", periodx, "Female")
    random.shuffle(females)
    for i in range(len(females)):
        student_lst.append(females[i])       

    # Make groups    
    groupnum = int(round(len(student_lst) / 4))
    groups = partition(student_lst, groupnum)

    return render_template("randomize.html", classname=classname, groups=groups, name=name, period=period)

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

@app.route("/kagan", methods=["POST"])
@login_required
def kagan():
    # Sort students into kagan groups

    # Get specific class
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]
    period = request.args.get("period")
    classname = period        
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]
    
    # Get student list sorted by score
    students = db.execute("SELECT * FROM students WHERE class = ? ORDER BY score DESC", periodx)
    

    # Sort students into differentiated groups, shuffled       
    diff_groups = partition(students, 4)
    for group in diff_groups:
        index = diff_groups.index(group)
        for student in group:
            student["group"] = index
    for group in diff_groups:
        random.shuffle(group)
    
    # Sort students kagan style
    biggest = (max([len(group) for group in  diff_groups]))
    final_groups = []
    for i in range(biggest):
        for j in range(len(diff_groups)):
            if i < len(diff_groups[j]):
                final_groups.append(diff_groups[j][i])            

    # Make groups    
    groups = chunk(final_groups, 4)

    return render_template("randomize.html", classname=classname, groups=groups, name=name, period=period, students=students)    

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

    # Make random groups
    random.shuffle(students)
    groupnum = int(round(len(students) / 4))
    groups = partition(students, groupnum)

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

@app.route("/update", methods=["POST"])
@login_required
def update():
    # Update all fields for a given student

    # Get teacher name
    teacher = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    name = teacher[0]["usercase"]

    # Get period
    period = request.args.get("period")
    period_id = db.execute("SELECT * FROM classes WHERE teacher = ? and class = ?", session["user_id"], period)
    periodx = period_id[0]["id"]
    classname = period_id[0]["class"]    
    genders = db.execute("SELECT * FROM gender")
    classes = db.execute("SELECT * FROM classes WHERE teacher = ?", session["user_id"])    

    # Get student id
    student_id = (request.args.get("studentid"))
    if student_id and student_id.isnumeric():
        student_id = int(request.args.get("studentid"))

    # Pull teacher's students for a rough server check
    your_students = db.execute("SELECT id FROM students WHERE teacher = ?", session["user_id"])
    student_lst = []
    for i in range(len(your_students)):
        student_lst.append(int(your_students[i]["id"]))
    
    if not student_id:
        return apology("Select a student", 400)

    elif not student_id in student_lst:
        return apology("Stop hacking.", 400)   

    # Get information from form
    new_name = request.form.get("name")
    new_class = request.form.get("class")
    new_gender = request.form.get("gender")
    new_score = request.form.get("score")

    # Validate form information
    if not new_name:
        return apology("Student name field left blank", 400)
    
    if not new_class:
        return apology("Class field left blank", 400)

    if new_class:
        all_classes = db.execute("SELECT * FROM classes WHERE teacher = ?", session["user_id"])
        class_lst = []
        for i in range(len(all_classes)):
            class_lst.append(all_classes[i]["class"])
        
        if new_class not in class_lst:
            return apology("Class not in database", 400)
        
        # Transform class into integer
        for i in range(len(all_classes)):
            if new_class == all_classes[i]["class"]:
                new_class = int(all_classes[i]["id"])
                break

    if new_gender:
        all_genders = db.execute("SELECT * FROM gender")
        gender_lst = []
        for i in range(len(all_genders)):
            gender_lst.append(all_genders[i]["gender"])

        if new_gender not in gender_lst:
            return apology("Gender not in database", 400)
        
        # Transform gender into integer
        for i in range(len(all_genders)):
            if new_gender == all_genders[i]["gender"]:
                new_gender = int(all_genders[i]["id"])
                break
    
    if new_score:
        if not new_score.isnumeric():
            return apology("Score must be integer 0-100", 400)
        
        else:
            new_score = int(new_score)
    
    if new_score > 100 or new_score < 0:
        return apology("Score must be integer 0-100", 400)

    # Update records
    db.execute("UPDATE students SET (name, class, gender, score) = (?, ?, ?, ?) WHERE id = ?", new_name, new_class, new_gender, new_score, student_id) 

    # Refresh students
    students = db.execute("SELECT * FROM students WHERE class = ?", periodx)   

    # Flash and redirect
    flash("Student updated.")       
    return render_template("edit.html", name=name, period=period, classname=classname, students=students, genders=genders, classes=classes)  
