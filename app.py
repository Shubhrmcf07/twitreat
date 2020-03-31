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

@app.route("/")
def home():
    return render_template("home.html")

if __name__ == "__main__":
	app.run(port=3000, debug=True)
