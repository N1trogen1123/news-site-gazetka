import datetime
import sqlalchemy.exc

from data import db_session

from flask import Blueprint, request, redirect, render_template, url_for, abort, flash, jsonify
from flask_login import LoginManager, login_user, current_user, logout_user, login_required

from forms.LoginForm import LoginForm
from forms.RegisterForm import RegisterForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return render_template('home.dashboard')
    
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session().create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data)

            if user and user.check_password(form.password_data):
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('home.index'))
            else:
                return render_template('login.html', message='Неправильный логин или пароль', form=form)
        
        except Exception:
            return render_template('login.html', message="Неправильный логин или пароль", form=form)
        finally:
            db_sess.close()
    return render_template('login.html', title='Авторизация', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session().create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user:
                return render_template('register.html', form=form, message='Такая почта уже зарегистрирована')
            
            user = User()
            user.email = form.email.data
            user.username = form.username.data
            user.set_password(form.password.data)
            user.level = 'user'
            user.create_time = datetime.datetime.now()
            user.is_banned = 0

            db_sess.add(user)
            db_sess.commit()

            login_user(user)
            return redirect(url_for('home.index'))
        except Exception as e:
            db_sess.rollback()
            return f'Ошибка :{str(e)}', 500
        finally:
            db_sess.close()
