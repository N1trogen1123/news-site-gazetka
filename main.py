import os

from flask import Flask, request, redirect, render_template, url_for
from flask_login import LoginManager, login_user, current_user, logout_user, login_required

from werkzeug.utils import secure_filename

from data import db_session
from data.users import User
from forms.LoginForm import LoginForm
from forms.RegisterForm import RegisterForm

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.secret_key = 'your-secret-key-here'

db_session.global_init("db/users.db")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    try:
        return db_sess.get(User, user_id)
    finally:
        db_sess.close()


@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('base.html')
    return render_template('base.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()

            if user and user.check_password(form.password.data, form.password.data):
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                return render_template('login.html',
                                       message="Неправильный логин или пароль",
                                       form=form)
        except Exception:
            return render_template('login.html',
                                   message="Произошла ошибка при авторизации",
                                   form=form)
        finally:
            db_sess.close()
    return render_template('login.html', title='Авторизация', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user:
                return render_template('register.html',
                                       form=form,
                                       message='Пользователь с такой электронной почтой уже зарегистрирован')

            user = User()
            user.email = form.email.data
            user.name = form.username.data
            user.set_password(form.password.data)
            user.level = 'user'

            db_sess.add(user)
            db_sess.commit()

            login_user(user)
            return redirect(url_for('index'))

        except Exception as e:
            db_sess.rollback()
            # Временный вывод ошибки на страницу
            return f"ОШИБКА: {str(e)}", 500
        finally:
            db_sess.close()

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=1000, debug=True)
