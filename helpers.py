import os
import requests
import urllib.parse
import random

from flask import redirect, render_template, request, session
from functools import wraps


def error_login(message, code=400):
    return render_template("login.html", error_message=message), code

def error_index(message, code=400):
    return render_template("index.html", error_message=message), code

def error_register(message, code=400):
    return render_template("register.html", error_message=message), code    

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
    
def partition(lst, n):
    division = len(lst) / n
    return [lst[round(division * i):round(division * (i + 1))] for i in range(n)]

def chunk(lst, n):
    return [lst[i * n:(i + 1) * n] for i in range((len(lst) + n - 1) // n )]

def random_groups(lst, size):
    random.shuffle(lst)
    groupnum = int(round(len(lst) / size))

    if groupnum == 0:
        groups = [lst]

    else:
        groups = partition(lst, groupnum)

    return groups