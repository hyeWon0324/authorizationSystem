from flask import Flask, render_template, request, redirect, url_for, session 
from flask_mysqldb import MySQL
import MySQLdb.cursors 
import re 

app = Flask(__name__)

app.secret_key = 'thisisthesecretkey'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'pythonlogin'

mysql = MySQL(app)

# http://localhost:5000/pythonlogin/ - login page, GET and POST requests
@app.route('/pythonlogin/', methods=['GET', 'POST'])
def login():
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password'in request.form:
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        if account: 
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            #Redirect to home page 
            return '로그인 성공!'
        else:
            msg = '잘못된 아이디 또는 패스워드'
    else:
        msg = '아이디 또는 패스워드를 입력하세요'
        
    return render_template('login.html', msg=msg)

# http://localhost:5000/pythonlogin/logout - logout page 
@app.route('/pythonlogin/logout')
def logout():
    # Remove session data, log user out 
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    #Redirect to login page 
    return redirect(url_for('login'))

# http://localhost:5000/pythonlogin/register - registration page 
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
        else: 
            # Account doesn't exist and the form data is valid. Insert new Account
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email))
            mysql.connection.commit()
            msg = '회원 등록 성공!'
    elif request.method == 'POST':
        # Form is empty
        msg = '회원 등록 정보를 입력해주세요'
    return render_template('register.html', msg=msg)
    
if __name__ == '__main__':
    app.run(debug=True) 