from flask import Flask, render_template, g, request, session, redirect, url_for
from database import connect_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
# app.config['SECRET_KEY'] = os.urandom(24)
app.config['SECRET_KEY'] = b'!~\xf5|\x83\xc1\x16\x98\x93\xbbtI\x99\xe5\xc7F\xf4W\x11A\xd8\xbd\x88\x0f'



# closing the database connection
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()




# Getting the data for current user
def get_current_user():
    
    user_result = None

    if 'user' in session:
        user = session['user']
        db = get_db()
        user_query = db.execute('SELECT id, name, password, expert, admin FROM users WHERE name = ?', [user])
        user_result = user_query.fetchone()

    return user_result



# Defining routes

@app.route('/')
def index():

    # user = None
    # if 'user' in session:
    #     user = session['user']
    user = get_current_user()
    db = get_db()

    questions_cur = db.execute('SELECT questions.id AS question_id, questions.question_text, askers.name AS asker_name, experts.name AS expert_name FROM questions JOIN users AS askers ON askers.id = questions.asked_by_id JOIN users AS experts ON experts.id = questions.expert_id WHERE questions.answer_text IS NOT NULL')
    questions_result = questions_cur.fetchall()

    return render_template('home.html', user=user, questions=questions_result)


@app.route('/register', methods=['GET', 'POST'])
def register():

    user = get_current_user()

    # handling the post request
    if request.method == 'POST':
        # return f'<h1>Name: {request.form["name"]}, Password: {request.form["password"]}'
        name = request.form['name']
        password = generate_password_hash(request.form['password'], method='sha256')
        db = get_db()

        existing_user_cur = db.execute('SELECT id FROM users WHERE name = ?', [name])
        existing_user = existing_user_cur.fetchone()
        if existing_user:
            return render_template('register.html', user=user, error='User already exists') 

        db.execute('INSERT INTO users (name, password, expert, admin) VALUES(?, ?, ?, ?)', [name, password, False, False])
        db.commit()

        session['user'] = request.form['name']

        return redirect(url_for('index'))

    return render_template('register.html', user=user) 


@app.route ('/login', methods=['GET', 'POST'])
def login():

    user = get_current_user()

    error_name = None
    error_password = None

    # handling the post request
    if request.method == 'POST':
        # return f'{request.form["name"]}, {request.form["password"]}'
        db = get_db()
        name = request.form['name']
        password = request.form['password']

        user_query = db.execute('SELECT id, name, password FROM users WHERE name = ?', [name])
        user_result = user_query.fetchone()

        # return f'{user_result["password"]}'

        if user_result:
            if check_password_hash(user_result["password"], password):
                session['user'] = user_result["name"]
                return redirect(url_for('index'))
            else:
                error_password = 'The password is incorrect.'

        else:
            error_name = 'The user does not exist.'

    return render_template('login.html', user=user, error_name=error_name, error_password=error_password) 


@app.route('/question/<question_id>')
def question(question_id):

    user = get_current_user()
    db = get_db()

    question_cur = db.execute('SELECT questions.question_text, questions.answer_text, askers.name AS asker_name, experts.name AS expert_name FROM questions JOIN users AS askers ON askers.id = questions.asked_by_id JOIN users AS experts ON experts.id = questions.expert_id WHERE questions.id = ?', [question_id])
    question = question_cur.fetchone()

    return render_template('question.html', user=user, question=question)


@app.route('/answer/<question_id>', methods=['GET', 'POST'])
def answer(question_id):

    user = get_current_user()
    db = get_db()

    if not user:
        return redirect(url_for('login'))
    
    if user['expert'] == False:
        return redirect(url_for('index'))

    question_cur = db.execute('SELECT id, question_text FROM questions WHERE id=?', [question_id])
    question = question_cur.fetchone()

    # handling the post request
    if request.method == 'POST':
        answer = request.form['answer']
        # return f'<h1>{answer}</h1>'
        db.execute('UPDATE questions SET answer_text = ? WHERE id = ?', [answer, question_id])
        db.commit()
        return redirect(url_for('unanswered'))

    return render_template('answer.html', user=user, question=question) 


@app.route('/ask', methods=['GET', 'POST'])
def ask():

    user = get_current_user()
    db = get_db()

    if not user:
        return redirect(url_for('login'))
    
    if (user['expert'] == True or user['admin'] == True):
        return redirect(url_for('index'))

    expert_cur = db.execute('SELECT id, name FROM users WHERE expert=true')
    expert_results = expert_cur.fetchall()

    # handling the POST request
    if request.method == 'POST':
        question = request.form['question']
        expert_id = int(request.form['expert'])
        user_id = int(user['id'])
        db.execute('INSERT INTO questions (question_text, asked_by_id, expert_id) VALUES (?, ?, ?)', [question, user_id, expert_id])
        db.commit()
        # return f'Question: {question}?, ASKED BY: {user["id"]}, expert: {expert_id}'
        return redirect(url_for('index'))

    return render_template('ask.html', user=user, experts=expert_results) 


@app.route('/unanswered')
def unanswered():

    user = get_current_user()

    if not user:
        return redirect(url_for('login'))

    if user['expert'] == False:
        return redirect(url_for('index'))

    db = get_db()
    questions_cur = db.execute('SELECT questions.id, questions.question_text, users.name FROM questions JOIN users ON users.id = questions.asked_by_id WHERE questions.answer_text IS NULL AND questions.expert_id=?', [user['id']])
    questions = questions_cur.fetchall()

    return render_template('unanswered.html', user=user, questions=questions) 


@app.route('/users')
def users():

    user = get_current_user()

    if not user:
        return redirect(url_for('login'))
    
    if user['admin'] == False:
        return redirect(url_for('index'))

    db = get_db()
    users_cur = db.execute("SELECT id, name, expert, admin FROM users")
    users_results = users_cur.fetchall()

    return render_template('users.html', user=user, users=users_results)


@app.route('/promote/<user_id>')
def promote(user_id):
    # return 'promoted'
    user = get_current_user()

    if not user:
        return redirect(url_for('login'))
    
    if user['admin'] == False:
        return redirect(url_for('index'))

    db=get_db()
    db.execute('UPDATE users SET expert=true WHERE id=?', [user_id])
    db.commit()
    return redirect(url_for('users'))


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect(url_for('index'))






if __name__ == '__main__':
    app.run()