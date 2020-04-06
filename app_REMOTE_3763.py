import os
import mysql.connector
from os.path import join, dirname
from dotenv import load_dotenv
from flask import *
from flask_bcrypt import Bcrypt
from datetime import date
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO
import random
import datetime

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
socketio = SocketIO(app)


def getuserdata(userdata):
	userdata['username'] = session['username']
	userdata['userid'] = session['userid']
	userdata['bio'] = session['bio']
	userdata['profile_picture'] = session['picture']


def getuserfriends(userdata):
	# Gets all Friends of the current user
	sql = "select distinct y.name,u2_id from Users join Friends on (Users.id = Friends.u1_id) join (select u2_id,name from Users join Friends on (Users.id = Friends.u2_id)) as y using(u2_id) where id = %s;" % (
		userdata['userid'])
	cursor.execute(sql)
	friends = cursor.fetchall()
	userdata['friends'] = friends
	# print(friends)


def getusergroups(userdata):
	# displays all groups user is in
	sql = sql = "select * from Community where c_id in (select community_id from Belongs where user_id =%s)" % (
		session['userid'])
	cursor.execute(sql)
	groups = cursor.fetchall()
	userdata['groups'] = groups


def getallusers(data):
	# Gets users which aren't already friends with current user
	sql = "select id,name from Users where id not in (select u2_id from Friends where u1_id = %s) and id <> %s and id not in (select u_id2 from Requests where u_id1 = %s);" % (
		session["userid"], session["userid"], session["userid"])
	cursor.execute(sql)
	data["otherusers"] = cursor.fetchall()


def getallgroups(data):
	# gets the groups of which user is not a part of
	sql = "select * from Community where c_id not in (select community_id from Belongs where user_id =%s)" % (
		session['userid'])
	cursor.execute(sql)
	data["othergroups"] = cursor.fetchall()


def getfriendrequests(data):
	# Gets all the friend requests for current user
	sql = "select u_id1,name from Requests join Users on Users.id = Requests.u_id1 where u_id2 = %s" % (
		session["userid"])
	cursor.execute(sql)
	data["requests"] = cursor.fetchall()


def getfriendsposts(userdata):
	# Gets all posts by friends
	sql = 'select name,content,time_stamp,p_id,photo from Users,Posts where u_id = id and community is null and (u_id in (select u2_id from Friends where u1_id =%s) or u_id = %s)' % (
		session["userid"], session["userid"])
	cursor.execute(sql)
	posts = cursor.fetchall()
	posts = posts[::-1]  # Newest posts come first
	userdata['posts'] = posts
	sql = 'select comm_id,post_id, name,content,timestamp,Users.id from Comments join Users on Users.id = Comments.user_id'
	cursor.execute(sql)
	comments = cursor.fetchall()
	userdata['comments'] = comments
	likes = {}
	for p in posts:
		sql = 'select count(*) from Likes where p_id=%s'%p[3]
		cursor.execute(sql)
		likes[p[3]] = cursor.fetchall()
	userdata['likes'] = likes

def getcommunity(comm, id):
	sql = "select * from Community where c_id=%s" % (id)
	cursor.execute(sql)
	comms = cursor.fetchall()
	comm['id'] = id
	comm['name'] = comms[0][1]
	comm['description'] = comms[0][2]
	#comm['owner'] = comments[0][3]


def getcommunityposts(userdata, id):
	sql = 'select name,content,time_stamp,p_id,photo from Users,Posts where community = %s and u_id = id and (u_id in (select u2_id from Friends where u1_id =%s) or u_id = %s)' % (
		id, session["userid"], session["userid"])
	cursor.execute(sql)
	posts = cursor.fetchall()
	posts = posts[::-1]  # Newest posts come first
	userdata['posts'] = posts
	sql = 'select comm_id,post_id, name,content,timestamp,Users.id from Comments join Users on Users.id = Comments.user_id'
	cursor.execute(sql)
	comments = cursor.fetchall()
	userdata['comments'] = comments
	likes = {}
	for p in posts:
		sql = 'select count(*) from Likes where p_id=%s'%p[3]
		cursor.execute(sql)
		likes[p[3]] = cursor.fetchall()
	userdata['likes'] = likes


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
	# Get all the details to display first and then render
	userdata = {}
	getuserdata(userdata)
	getuserfriends(userdata)
	getallusers(userdata)
	getfriendsposts(userdata)
	getfriendrequests(userdata)
	getallgroups(userdata)
	getusergroups(userdata)
	return render_template("./home.html", userdata=userdata, user=session['userid'], auth=session)


@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		email = request.form["email"]
		password = request.form["password"]
		sql = "select * from Users where email = '%s';" % (email)
		cursor.execute(sql)
		data = cursor.fetchall()
		# If it can't find an account with matching credentials
		if len(data) == 0:
			return render_template('./login.html', error="Wrong email")
			# If passwords do not match
		elif not bcrypt.check_password_hash(data[0][2], password):
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
		return render_template('./register.html', error="Passwords do not match")

	sql = "select * from Users where email='%s';" % (email)

	cursor.execute(sql)
	data = cursor.fetchall()

	if(len(data) > 1):
		return render_template('./register.html', error="User already exists")

	pw_hash = bcrypt.generate_password_hash(password)

	cursor.execute("insert into Users (name, password, gender, dob, email) values (%s,%s,%s,%s,%s);", (
		name, pw_hash, int(gender), dob, email))
	mydb.commit()
	return redirect(url_for('home'))


@app.route('/friends/<string:choice>/<string:id>', methods=['GET'])
def friends(choice, id):

	if choice == "add":
		sql = "insert into Requests values (%s,%s)" % (session['userid'], id)
		cursor.execute(sql)
	else:
		sql = "delete from Friends where (u1_id = %s and u2_id = %s) or (u1_id = %s and u2_id = %s) " % (
			id, session['userid'], session['userid'], id)
		cursor.execute(sql)
	mydb.commit()
	return redirect(session['url'])


@app.route('/requests/<string:choice>/<string:id>', methods=['GET'])
def requests(choice, id):
	if choice == "add":
		sql = "insert into Friends values (%s,%s)" % (id, session['userid'])
		cursor.execute(sql)
		sql = "insert into Friends values (%s,%s)" % (session['userid'], id)
		cursor.execute(sql)
	sql = "delete from Requests where u_id1 = %s and u_id2 = %s" % (
		id, session['userid'])
	cursor.execute(sql)
	mydb.commit()
	return redirect(session['url'])


@app.route('/groups/<string:choice>/<string:id>')
def groups(choice, id):
	if choice == "join":
		sql = "insert into Belongs values (%s,%s)" % (session['userid'], id)
		cursor.execute(sql)

		mydb.commit()
		return redirect(session['url'])

	print(id)

	sql = "delete from Belongs where community_id=%s and user_id=%s" % (
		id, session['userid'])
	cursor.execute(sql)
	mydb.commit()
	return redirect(session['url'])


@app.route('/myprofile', methods=['GET', 'POST'])
def myprofile():
	if request.method == 'GET':
		if 'logged_in' in session:
			userdata = {}
			getuserdata(userdata)
			getuserfriends(userdata)
			getfriendrequests(userdata)
			d = session['userid']
			cursor.execute("select * from Posts where u_id=%s and community is null" %str(d))
			data = cursor.fetchall()

			l = []
			count = []
			for i in range(len(data)):
				cursor.execute(
					"select * from Comments,Users where user_id=id and post_id="+str(data[i][0]))
				result = cursor.fetchall()
				l.append(result)
				cursor.execute(
					"select count(*) from Likes where p_id=%s" % (data[i][0]))
				cnt = cursor.fetchone()
				count.append(cnt)

				print(count)

			return render_template('./profile.html', userdata=userdata, user=session, data=data, tr=l, count=count)

		return render_template('./login.html', error="You must be logged in!")

	return redirect(url_for('home'))


@app.route('/createBio', methods=['POST'])
def createBio():
	if not request.form['bio']:
		pass
	else:
		bio = request.form['bio']
		cursor.execute("update Users set bio=%s where id=%s", (
			bio, session['userid']))
		mydb.commit()
	refreshcookies()
	return redirect(request.referrer)


@app.route('/uploadr', methods=['POST'])
def upload_files():
	if not request.files['file']:
		pass
	else:
		uploads_dir = os.path.join(app.static_folder, 'userimg')
		os.makedirs(uploads_dir, exist_ok=True)
		f = request.files['file']
		f.save(os.path.join(uploads_dir, secure_filename(f.filename)))
		print(f.filename)

		cursor.execute("update Users set picture=%s where id=%s",
					   ('static/userimg/'+f.filename, session['userid']))

		mydb.commit()
	refreshcookies()
	return redirect(request.referrer)


@app.route('/post', methods=['POST'])
def posts():
	u_id = session['userid']
	content = request.form['content']
	if not request.files['picture']:
		photo = "None"
	else:
		uploads_dir = os.path.join(app.static_folder, 'postimg/'+str(u_id))
		os.makedirs(uploads_dir, exist_ok=True)
		f = request.files['picture']
		f.save(os.path.join(uploads_dir, secure_filename(f.filename)))
		photo = 'static/postimg/'+str(u_id) + '/' + f.filename

	cursor.execute(
		"insert into Posts (u_id, content, photo) values (%s,%s,%s)", (u_id, content, photo))

	mydb.commit()
	return redirect(request.referrer)


@app.route('/delpost', methods=['POST'])
def delpost():
	dele = request.form['del']
	cursor.execute("delete from Posts where p_id=" + str(dele))
	mydb.commit()
	return redirect(url_for('myprofile'))


@app.route('/comment', methods=['POST'])
def comment():
	id = session['userid']
	content = request.form['content']
	p_id = request.form['comment']

	cursor.execute(
		"insert into Comments (post_id, user_id, content) values (%s,%s,%s)", (p_id, id, content))
	mydb.commit()
	return redirect(request.referrer)


@app.route('/delcom', methods=['POST'])
def delcom():
	id = request.form['delcom']
	cursor.execute("delete from Comments where comm_id="+str(id))
	mydb.commit()
	return redirect(request.referrer)


@app.route('/creategroup', methods=['POST'])
def creategroup():
	cname = request.form['cname']
	cdesc = request.form['cdesc']

	cursor.execute(
		"insert into Community (name, description, owner) values ('%s','%s','%s')" % (cname, cdesc, session['userid']))

	mydb.commit()
	return redirect(request.referrer)


@app.route('/groupposts/<string:id>', methods=['GET', 'POST'])
def groupposts(id):
	if request.method == 'GET':
		if not auth('/groupposts/%s' % (id)):
			redirect('/login')
		sql = 'Select * from Belongs,Users where community_id='+id+' and user_id=id;'
		cursor.execute(sql)
		users = cursor.fetchall()
		c_users = [item[0] for item in users]
		if session['userid'] not in c_users:
			sql2 = "INSERT INTO Belongs VALUES('%s','%s');" % (
				session['userid'], id)
			cursor.execute(sql2)
			mydb.commit()
		session['currentgroup'] = id
		userdata = {}
		getuserdata(userdata)
		getcommunityposts(userdata, id)
		community = {}
		getcommunity(community, id)
		return render_template("group.html", userdata=userdata, user=session['userid'], community=community, users=users, auth=session)
	else:
		content = request.form['content']
		if not request.files['picture']:
			photo = "None"
		else:
			uploads_dir = os.path.join(
				app.static_folder, 'postimg/'+str(session['userid']))
			os.makedirs(uploads_dir, exist_ok=True)
			f = request.files['picture']
			f.save(os.path.join(uploads_dir, secure_filename(f.filename)))
			photo = 'static/postimg/'+str(session['userid']) + '/' + f.filename

		cursor.execute(
			"insert into Posts (u_id, content, photo, community) values (%s,%s,%s,%s)", (session['userid'], content, photo, id))

		mydb.commit()
		return redirect("/groupposts/"+session['currentgroup'])


@app.route('/createvent', methods=['POST'])
def createvent():
	host = session['userid']
	location = request.form['location']
	description = request.form['edesc']

	cursor.execute("insert into Events (host, location, description) values (%s,%s,%s)",
				   (host, location, description))
	mydb.commit()
	return redirect(url_for('events'))


@app.route('/events')
def events():
	cursor.execute("select * from Events where host=" + str(session['userid']))
	host = cursor.fetchall()
	cursor.execute(
		'select * from Events where e_id in (select event_id from Attending where user_id=%s)' % session['userid'])
	attending = cursor.fetchall()

	cursor.execute(
		'select * from Events where e_id not in (select event_id from Attending where user_id=%s)' % session['userid'])
	recommended = cursor.fetchall()

	l = []

	for i in range(len(recommended)):
		cursor.execute("select * from Users where id in (select u2_id from Friends where u1_id=%s and u2_id in (select user_id from Attending where event_id = %s))" %
					   (session['userid'], recommended[i][0]))
		frns = cursor.fetchall()
		l.append(frns)

	return render_template('events.html', host=host, attending=attending, recommended=recommended, tr=l, auth=session)


@app.route('/even/<string:choice>/<string:id>')
def even(choice, id):
	if(choice == 'join'):
		cursor.execute("insert into Attending values (%s,%s)" %
					   (id, session['userid']))
		mydb.commit()
		return redirect(url_for('events'))

	elif choice == 'withdraw':
		cursor.execute("delete from Attending where event_id = %s and user_id = %s" % (
			id, session['userid']))
		mydb.commit()
		return redirect(url_for('events'))

	cursor.execute("delete from Events where e_id=%s and host=%s" %
				   (id, session['userid']))
	mydb.commit()
	return redirect(url_for('events'))


@app.route('/messenger')
def messenger():
	return render_template('messenger.html')


def messageReceived(methods=['GET', 'POST']):
	print('Received')


@socketio.on('my event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
	print('Event:' + str(json))
	socketio.emit('my response', json, callback=messageReceived)


@app.route('/updUser', methods=['POST'])
def updUser():
	city = request.form['city']
	country = request.form['country']
	phone = request.form['phone']

	cursor.execute("update Users set city=%s , country=%s, phone_number=%s where id=%s",
				   (city, country, phone, session['userid']))
	mydb.commit()
	return redirect(request.referrer)


@app.route('/like', methods=['POST'])
def like():
	u_id = session['userid']
	p_id = request.form['like']

	cursor.execute(
		"select * from Likes where u_id=%s and p_id=%s", (u_id, p_id))
	data = cursor.fetchall()
	if len(data) > 0:
		cursor.execute(
			"delete from Likes where u_id = %s and p_id=%s", (u_id, p_id))
		mydb.commit()
		return redirect(request.referrer)

	cursor.execute("insert into Likes values (%s, %s)", (u_id, p_id))
	mydb.commit()
	return redirect(request.referrer)

@app.route('/profile/<string:id>/')
def profile(id):
	sql = 'select * from Users where id = %s ;' %id
	cursor.execute(sql)
	user = cursor.fetchall()

	sql2 = "select * from Posts where u_id=%s and community is null" %(id)
	cursor.execute(sql2)
	data = cursor.fetchall()

	l = []

	for i in range(len(data)):
		cursor.execute(
			"select * from Comments,Users where user_id=id and post_id="+str(data[i][0]))
		result = cursor.fetchall()
		l.append(result)

	sql3 = 'select * from Friends,Users where u1_id = %s and u2_id=id;' %id
	cursor.execute(sql3)
	friends = cursor.fetchall()

	return render_template('friend.html', user=user, data=data, tr=l, friends=friends)

if __name__ == "__main__":
	socketio.run(app, port=3000, debug=True)
