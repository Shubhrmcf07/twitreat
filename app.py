import os
import mysql.connector
from os.path import join, dirname
from dotenv import load_dotenv
from flask import *
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
app.secret_key = "thisisatopsecretkey"

def auth(page):
	# Session url holds the last visited link by the user
	session['url'] = page
	if 'logged_in' in session:
		return True
	else:
		return False

def refreshcookies():
	sql = "select * from Users where id = '%s';"%(session['userid'])
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

@app.route('/',methods=['GET'])
def home():
	# If user not logged in
	if not auth("/"):
		return redirect('/login')
	print(session['userid'])
	return render_template("./home.html")

@app.route('/login',methods=['GET','POST'])
def login():
	if request.method == 'POST':
		email = request.form["email"]
		password = request.form["password"]
		sql = "select * from Users where email = '%s' and password = '%s';"%(email,password)
		cursor.execute(sql)
		data = cursor.fetchall()

		# If it can't find an account with matching credentials
		if len(data)==0:
			return render_template('./login.html',error = "Wrong email or password")

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

@app.route('/logout',methods=['POST','GET'])
def logout():
	# Clear Session
	session.clear()
	return redirect('/login')

if __name__ == "__main__":
	app.run(port=3000, debug=True)
