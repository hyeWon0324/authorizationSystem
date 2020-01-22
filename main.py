from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from flask_scrypt import generate_random_salt, generate_password_hash, check_password_hash
from passlib.hash import sha256_crypt
#from flask.ext.bcrypt import Bcrypt
import MySQLdb.cursors 
import re 
import uuid 
import hashlib
import datetime
import redis
from rq import Queue
import time 

app = Flask(__name__)

app.secret_key = 'secretkeyneedtobesalt'               # TODO: Create random salt    uuid.uuid4()

# Database detail 
app.config['MYSQL_HOST'] = 'localhost'  #db['mysql_host']
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'pythonlogin'

# Email server detail 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'

#bcrypt = Bcrypt(app)
mysql = MySQL(app)
red = redis.Redis()
q = Queue(connection=red)

mail = Mail(app)

account_activation_required = False

# http://localhost:5000/pythonlogin/ - login page, GET and POST requests
@app.route('/pythonlogin/', methods=['GET', 'POST'])
def login():
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password'in request.form:
        username = request.form['username']
        password = request.form['password']

        #pw_hash = bcrypt.generate_password_hash(password, 10)

        #hash = password + app.secret_key
        #hash = hashlib.sha1(hash.encode())
        #password = hash.hexdigest()

        # Check if account exists using MySQL
        #connection = mysql.connector.connect(host='localhost',                                         database='pythonlogin',                                         user='root',                                         password='1234')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username))
        account = cursor.fetchone()
        
        if account:

            salt = account['salt']
            password_hash = account['password']

            if check_password_hash(password, password_hash, salt): 
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                if 'rememberme' in request.form:
                    # Create hash to store as cookie
                    #hash = account['username'] + request.form['password'] + app.secret_key 
                    #hash = hashlib.sha1(hash.encode())
                    #hash = hash.hexdigest()

                    # Cookie expire in 90days 
                    expire_date = datetime.datetime.now() + datetime.timedelta(days=90)
                    resp = make_response('Success', 200)
                    resp.set_cookie('rememberme', hash, expires=expire_date)

                    # Update rememeberme in accounts table to the cookie hash 
                    cursor.execute('UPDATE accounts SET rememberme = %s WHERE id = %s', (hash, account['id']))
                    mysql.connection.commit()
                    return resp
                cursor.close()
                mysql.connection.close()
                return 'Success'
            else:
                msg = '잘못된 비밀번호'
    else:
        msg = '존재하지 않는 아이디'
    return render_template('login.html', msg=msg)

# http://localhost:5000/pythonlogin/logout - logout page 
@app.route('/pythonlogin/logout')
def logout():
    # Remove session data, log user out 
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)

    # Remove cookie data "remember me" #Redirect to login page 
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('remember', expires=0)
    return resp 
    

# http://localhost:5000/pythonlogin/register - registration page GET and POST requests
@app.route('/pythonlogin/register', methods=['GET', 'POST'])
def register():
    msg=''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if register.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username))
        account = cursor.fetchone() 
        # If account exists show error and validation checks 
        if account: 
            msg= '이미 등록한 회원입니다!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email): 
            msg = '유효하지 않은 이메일 주소입니다!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = '아이디는 숫자와 문자로만 이루어져야합니다!'
        elif not username or not password or not email:
            msg = '입력 칸을 채워주세요!'
        elif account_activation_required:
            # Account activation enabled 

            # Generate a random unique id for activation code 
            activation_code = uuid.uuid4()
            
            # Scrypt password hashing and random salt generation
            salt = generate_random_salt()
            password_hash = generate_password_hash(password, salt)

            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s, %s, %s,"")', (username, password_hash, salt, email, activation_code))
            mysql.connection.commit()

            email = Message('Account Activation Required', sender = 'parkhw0324@gmail.com', recipients = [email])

            activate_link = 'http://localhost:5000/pythonlogin/activate/' + str(email) + '/' + str(activation_code)

            email.body = '<p>아래 링크를 클릭하여 이메일을 인증하세요: <a hredf="' + str(activate_link) + '">' + str(activate_link) + '</a></p>'
            mail.send(email)
            return '이메일이 발송되었습니다. 계정을 활성화하려면 이메일을 인증하세요!'
        else: 
            # Account doesn't exist and the form data is valid. Insert new Account
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            msg = '회원 등록 성공!'
        
        cursor.close()
        mysql.connection.close()
    elif request.method == 'POST':
        # Form is empty
        msg = '회원 등록 정보를 입력해주세요'
    
    return render_template('register.html', msg=msg)

# http://localhost:5000/pythonlogin/activate/<email>/<code> - 이메일과 활성화 코드가 올바른 경우 계정을 활성화
@app.route('/pythonlogin/activate/<string:email>/<string:code>', methods=['GET'])
def activate(email, code):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM accounts WHERE email = %s AND activation_code = %s', (email, code))
    account = cursor.fetchone()
    if account: 
        cursor.execute('UPDATE accounts SET activation_code = "activated" WHERE email = %s AND activation_code = %s', (email, code))
        mysql.connection.commit() 

        return '이메일 인증 성공!'
    return '해당 이메일의 계정이 존재하지 않거나 올바르지 않은 활성화 코드입니다!'

def loggedin():
    if 'loggedin' in session:
        return True
    elif 'rememberme' in request.cookies:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE rememberme = %s', (request.cookies['rememberme'],))
        account = cursor.fetchone()
        if account: 
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return True
    # account not logged in
    return False

# http://localhost:5000/pythonlogin/home - Home page only accessible for loggedin users
@app.route('/pythonlogin/home')
def home():

    if loggedin():
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

# http://localhost:5000/pythonlogin/profile - Profile page, only accessible for loggedin users 
@app.route('/pythonlogin/profile')
def profile():

    if loggedin(): 
        # Get all account info 
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        return render_template('profile.html', account=account)
    
    #if not logged in, go to login page 
    return redirect(url_for('login'))

@app.route('/pythonlogin/profile/edit', methods=['GET', 'POST'])
def edit_profile():

    if loggedin():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        msg = ''

        if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form: 
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']
            # Hash password 
            #hash = password + app.secret_key
            #hash = hashlib.sha1(hash.encode())
            #password = hash.hexdigest()

             # Scrypt password hashing and random salt generation
            salt = generate_random_salt()
            password_hash = generate_password_hash(password, salt)

            # Update account with new info 
            cursor.execute('UPDATE accounts SET username = %s, password = %s, salt = %s, email = %s WHERE id = %s', (username, password_hash, salt, email, session['id']))
            mysql.connection.commit() 
            msg = '업데이트 성공!'

        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone() 

        return render_template('profile-edit.html', account=account, msg=msg)
    return redirect(url_for('login'))


def background_task(n):
    
    delay = 2 

    print("Task running!!")
    print(f"Simulating {delay} second delay")

    time.sleep(delay)

    print(len(n))
    print("Task complete")

    return len(n)

@app.route("/task")
def add_task():
    
    if request.args.get("n"): 

        job = q.enqueue(background_task, request.args.get("n"))

        q_len = len(q)

        return f"Task {job.id} added to queue at {job.enqueued_at}. {q_len} tasks in the queue"

    return "No value for n"

if __name__ == '__main__':
    app.run(debug=True) 