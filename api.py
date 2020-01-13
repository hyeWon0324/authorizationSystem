from flask import Flask

app = Flask(__name__)

@app.rout('/unprotected')
def unprotected():
    return ''

@app.route('/protected')
def protectedd(): 

app.route('/login')
def login(): 
    return ''

if __name__ == '__main__':
    app.run(debug=True) 
