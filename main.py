import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, request, redirect, render_template, url_for, abort, flash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from data.users import User
from forms.LoginForm import LoginForm
from forms.Newsform import NewsForm
from forms.RegisterForm import RegisterForm
from forms.ModerationForm import ModerationForm
from forms.CategoryForm import CategoryForm

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view ='login'
login_manager.login_message = 'Пожалуйста, войдите в аккаунт для доступа к этой странице.'
app.secret_key = 'your-secret-key-here'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = os.path.join(app.root_path,'db', 'news.db')


#  Модель пользователя для flask-login
class User(UserMixin):
    def __init__(self, id, username, email, hashed_password, level, is_banned, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.level = level
        self.is_banned = is_banned
        self.created_at = created_at

# Работа с БД
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# Инициализация всех таблиц.
def init_db():
    conn = get_db()
    conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'user',
                is_banned INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Черновик',
                moderation_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP,
                image_filename TEXT,
                FOREIGN KEY (author_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (news_id) REFERENCES news(id),
                FOREIGN KEY (moderator_id) REFERENCES users(id)
            );
        ''')
    # Категории по умолчанию
    cursor = conn.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            'Политика', 'Экономика', 'Технологии',
            'Спорт', 'Культура', 'Наука', 'Общество'
        ]
        conn.executemany(
            "INSERT INTO categories (name) VALUES (?)",
            [(c,) for c in default_categories]
        )
    conn.commit()
    conn.close()


# Инициализируем БД при запуске
init_db()

# Получение список всех категорий
def get_categories():
    conn = get_db()
    categories = conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
    conn.close()
    return categories

# Поиск пользователя по ID
def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            hashed_password=row['hashed_password'],
            level=row['level'],
            is_banned=row['is_banned'],
            created_at=row['created_at'],
        )
    return None

# Поиск пользователя по почте
def get_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row:
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            hashed_password=row['hashed_password'],
            level=row['level'],
            is_banned=row['is_banned'],
            created_at=row['created_at'],
        )
    return None

#Проверка допустимоего расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Сохранения зигруженого изображения, вернуть имя файла
def save_image(file):
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None

STATUS_BADGES = {
    'Черновик': 'secondary',
    'На модерации': 'warning',
    'Опубликовано': 'success',
    'Отклонено': 'danger',
}

@app.context_processor
def inject_helpers():
    return dict(status_badges=STATUS_BADGES)

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))

# Главная страница - опубликованные новости
@app.route('/')
def index():
    search_query = request.args.get('q', '').strip()
    category_id = request.args.get('category', '', type=str)
    conn = get_db()
    sql = """
        SELECT n.*, c.name AS category_name, u.username AS author_name
        FROM news n
        JOIN categories c ON n.category_id = c.id
        JOIN users u ON n.author_id = u.id
        WHERE n.status = 'Опубликовано'
    """
    params = []
    if search_query:
        sql += " AND (n.title LIKE ? OR n.content LIKE ?)"
        like_pattern = f"%{search_query}%"
        params.extend([like_pattern, like_pattern])
    if category_id and category_id.isdigit():
        sql += " AND n.category_id = ?"
        params.append(int(category_id))
    sql += " ORDER BY n.published_at DESC, n.created_at DESC"
    news_list = conn.execute(sql, params).fetchall()
    categories = get_categories()
    conn.close()
    return render_template('index.html',
                           news_list=news_list,
                           categories=categories,
                           search_query=search_query,
                           selected_category=category_id)

# Просмотр новости
@app.route('/news/<int:id>')
def view_news(id):
    conn = get_db()
    article = conn.execute("""
     SELECT n.*, c.name AS category_name, u.username AS author_name
        FROM news n
        JOIN categories c ON n.category_id = c.id
        JOIN users u ON n.author_id = u.id
        WHERE n.id = ?
        """, (id,)).fetchone()
    conn.close()
    if not article:
        abort(404)
    # Неопубликованные новости видны только автору и модератору/админу
    if article['status'] != 'Опубликовано':
        if not current_user.is_authenticated:
            abort(404)
        if (article['author_id'] != current_user.id and
                current_user.level not in ('moderator', 'admin')):
            abort(404)
    moderation_form = None
    if current_user.is_authenticated and current_user.level in ('moderator', 'admin') and article[
        'status'] == 'На модерации':
        moderation_form = ModerationForm()
    return render_template('news_detail.html', article=article, moderation_form=moderation_form)

@app.route('/news/<int:id>/moderte', methods=['POST'])
@login_required
def moderate_news(id):
    if current_user.level not in ('moderator', 'admin'):
        abort(403)
    form = ModerationForm()
    if form.validate_on_submit():
        action = 'Одобрено' if form.submit_approve.data else 'Отклонено'
        new_status = 'Опубликовано' if action == 'Одобрено' else 'Отклонено'
        comment = form.comment.data.strip() if form.comment.data else None
        published_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if action == 'Одобрено' else None
        conn = get_db()
        try:
            if action == 'Одобрено':
                conn.execute("""
                    UPDATE news 
                    SET status = ?, moderation_comment = ?, published_at = ?
                    WHERE id = ?
                """, (new_status, comment, published_at, id))
            else:
                conn.execute("""
                    UPDATE news 
                    SET status = ?, moderation_comment = ?
                    WHERE id = ?
                """, (new_status, comment, id))
            conn.execute("""
                INSERT INTO moderation_logs (news_id, moderator_id, action, comment)
                VALUES (?, ?, ?, ?)
            """, (id, current_user.id, action, comment))
            conn.commit()
            flash(f'Новость успешно {"одобрена" if action == "Одобрено" else "отклонена"}!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
        finally:
            conn.close()
    return redirect(url_for('view_news', id=id))

# Добавление новости
@app.route('/news/add', methods=['GET', 'POST'])
@login_required
def add_news():
    # Проверка на бан
    if current_user.is_banned:
        flash('Вы заблокированы и не можете создавать новости.', 'danger')
        return redirect(url_for('index'))
    form = NewsForm()
    form.category_id.choices = [(c['id'], c['name']) for c in get_categories()]
    if form.validate_on_submit():
        # Определяем статус по нажатой кнопке
        status = 'Черновик'
        if 'submit_moderation' in request.form:
            status = 'На модерации'
        # Сохраняем изображение
        image_filename = None
        if form.image.data:
            image_filename = save_image(form.image.data)
        conn = get_db()
        conn.execute("""
                INSERT INTO news (title, content, author_id, category_id, status,
                                  created_at, image_filename)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
            form.title.data,
            form.content.data,
            current_user.id,
            form.category_id.data,
            status,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            image_filename,
        ))
        conn.commit()
        conn.close()
        if status == 'На модерации':
            flash('Новость отправлена на модерацию!', 'info')
        else:
            flash('Черновик сохранён!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_news.html', form=form)

# Личный кабинет (Мои новости)

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    news_list = conn.execute("""
        SELECT n.*, c.name AS category_name
        FROM news n
        JOIN categories c ON n.category_id = c.id
        WHERE n.author_id = ?
        ORDER BY n.created_at DESC
        """, (current_user.id,)).fetchall()
    conn.close()
    return render_template('dashboard.html', news_list=news_list)

# Модерация
@app.route('/moderation')
@login_required
def moderation():
    if current_user.level not in ('moderator', 'admin'):
        abort(403)
    conn = get_db()
    news_list = conn.execute("""
        SELECT n.*, c.name AS category_name, u.username AS author_name
        FROM news n
        JOIN categories c ON n.category_id = c.id
        JOIN users u ON n.author_id = u.id
        WHERE n.status = 'На модерации'
        ORDER BY n.created_at ASC
    """).fetchall()
    conn.close()
    return render_template('moderation.html', news_list=news_list)

# Авторизация

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)
        if user and check_password_hash(user.hashed_password, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            return render_template('login.html',
                                   message="Неправильный логин или пароль",
                                   form=form)
    return render_template('login.html', title='Авторизация', form=form)

# Регистрация

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Проверяем, не занят ли email
        existing = get_user_by_email(form.email.data)
        if existing:
            return render_template('register.html',
                                   form=form,
                                   message='Пользователь с такой электронной почтой уже зарегистрирован')
        # Хэшируем пароль
        hashed_pw = generate_password_hash(form.password.data)
        conn = get_db()
        try:
            conn.execute("""
                    INSERT INTO users (username, email, hashed_password, level, is_banned, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                form.username.data,
                form.email.data,
                hashed_pw,
                'user',
                0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ))
            conn.commit()
            # Загружаем только что созданного пользователя и логиним
            user = get_user_by_email(form.email.data)
            login_user(user)
            flash('Регистрация прошла успешно!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            conn.rollback()
            return render_template('register.html',
                                   form=form,
                                   message=f'Ошибка при регистрации: {str(e)}')
        finally:
            conn.close()
    return render_template('register.html', form=form)

#Выход

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=1000, debug=True)
