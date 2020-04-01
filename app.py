import os
import mysql.connector
from os.path import join, dirname
from dotenv import load_dotenv
from flask import *
from werkzeug.security import generate_password_hash
from flask_bcrypt import Bcrypt
from datetime import date
import random

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

mydb = mysql.connector.connect(
    host=os.getenv("localhost"),
    user=os.getenv("user"),
    passwd=os.getenv("passwd"),
    database=os.getenv("database")
)

cursor = mydb.cursor()
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "thisisatopsecretkey"


def auth(page):
    # Session url holds the last visited link by the user
    session['url'] = page
    if 'logged_in' in session:
        return True
    else:
        return False


def refreshcookies():
    sql = "select * from Users where id = '%s';" % (session['userid'])
    cursor.execute(sql)
    data = cursor.fetchall()
    session.clear()
    session['logged_in'] = True
    session['userid'] = data[0][0]
    session['username'] = data[0][1]
    session['dob'] = data[0][3]
    session['bio'] = data[0][5]
    session['city'] = data[0][6]
    session['country'] = data[0][7]
    session['email'] = data[0][8]
    session['phone'] = data[0][9]
    session['picture'] = data[0][10]


@app.route('/', methods=['GET'])
def home():
    # If user not logged in
    if not auth("/"):
        return redirect('/login')
    print(session['userid'])
    return render_template("./home.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]
        sql = "select * from Users where email = '%s';" % (
            email, password)
        cursor.execute(sql)
        data = cursor.fetchall()

        # If it can't find an account with matching credentials
        if len(data) == 0:
            return render_template('./login.html', error="Wrong email")
            # If passwords do not match
        elif not bcrypt.check_password_hash(data[0].password, password):
            return render_template('./login.html', error="Incorrect Password")

        # Account found
        else:
            # Set session variables
            session['logged_in'] = True
            session['userid'] = data[0][0]
            session['username'] = data[0][1]
            session['dob'] = data[0][3]
            session['bio'] = data[0][5]
            session['city'] = data[0][6]
            session['country'] = data[0][7]
            session['email'] = data[0][8]
            session['phone'] = data[0][9]
            session['picture'] = data[0][10]
            return redirect('/')
    else:
        # If GET and already logged in, just redirect
        if 'logged_in' in session:
            return redirect('/')
        # If not logged in show login page
        return render_template("./login.html")


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    # Clear Session
    session.clear()
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    name = request.form['name']
    email = request.form['email']
    password = request.form['password1']
    confirmpw = request.form['password2']
    gender = request.form['gender']
    dob = request.form['dob']

    if not name or not email or not password or not confirmpw or not gender or not dob:
        return render_template('./register.html', error="All fields required")

    if len(password) < 6:
        return render_template('./register.html', error="Password too short")

    if password != confirmpw:
        return render_template('./register.html', error="Passwords do not match<br>")

    sql = "select * from Users where email='%s';" % (
        email)

    cursor.execute(sql)
    data = cursor.fetchall()

    if(len(data) > 1):
        return render_template('./register.html', "User already exists")

    pw_hash = bcrypt.generate_password_hash(password)

    cursor.execute("insert into Users (name, password, gender, dob, email) values (%s,%s,%s,%s,%s);", (
        name, pw_hash, int(gender), dob, email))

    mydb.commit()
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(port=3000, debug=True)
