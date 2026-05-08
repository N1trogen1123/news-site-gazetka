import os
import datetime
import sqlalchemy.exc

from flask import Flask, request, redirect, render_template, url_for, abort, flash, jsonify
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from sqlalchemy import or_

from werkzeug.utils import secure_filename

from data import db_session
from data.users import User
from data.news import News
from data.categories import Categories
from data.moderation_logs import ModerationLogs
from forms.LoginForm import LoginForm
from forms.Newsform import NewsForm
from forms.RegisterForm import RegisterForm
from forms.ModerationForm import ModerationForm

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.secret_key = 'your-secret-key-here'

# Настройка загрузки файлов
app.config['UPLOAD_FOLDER'] = 'static/uploads/news'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db_session.global_init("db/news.db")


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    try:
        return db_sess.get(User, user_id)
    finally:
        db_sess.close()


@app.route('/')
def index():
    """Главная страница со списком новостей"""
    db_sess = db_session.create_session()
    try:
        # Получаем параметры поиска и фильтрации
        search_query = request.args.get('q', '')
        selected_category = request.args.get('category', '')

        # Базовый запрос
        query = db_sess.query(News)

        # Фильтрация по категории
        if selected_category and selected_category.isdigit():
            query = query.filter(News.category_id == int(selected_category))

        # Поиск по заголовку и содержимому
        if search_query:
            query = query.filter(
                or_(
                    News.title.contains(search_query),
                    News.content.contains(search_query)
                )
            )

        # Сортировка по дате (сначала новые) и только опубликованные
        news_list = query.filter(News.status == 'Опубликовано').order_by(News.published_at.desc()).all()

        # Получаем все категории для фильтра
        categories = db_sess.query(Categories).all()

        # Для каждой новости добавляем имя автора и категории
        for news in news_list:
            # Получаем автора
            author = db_sess.query(User).filter(User.id == news.author_id).first()
            news.author_name = author.username if author else 'Неизвестный автор'

            # Получаем категорию
            category = db_sess.query(Categories).filter(Categories.id == news.category_id).first()
            news.category_name = category.name if category else 'Без категории'

        return render_template('index.html',
                               news_list=news_list,
                               categories=categories,
                               search_query=search_query,
                               selected_category=selected_category,
                               current_user=current_user)
    finally:
        db_sess.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()

            if user and user.check_password(form.password.data):
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
            user.username = form.username.data
            user.set_password(form.password.data)
            user.level = 'user'
            user.create_time = datetime.datetime.now()
            user.is_banned = 0

            db_sess.add(user)
            db_sess.commit()

            login_user(user)
            return redirect(url_for('index'))

        except Exception as e:
            db_sess.rollback()
            return f"ОШИБКА: {str(e)}", 500
        finally:
            db_sess.close()

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/add_news', methods=['GET', 'POST'])
def add_news():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    if current_user.is_banned == 1:
        abort(403)

    form = NewsForm()
    db_sess = db_session.create_session()
    try:
        categories = db_sess.query(Categories).all()
        form.category_id.choices = [(c.id, c.name) for c in categories]

        if form.validate_on_submit():

            existing_news = db_sess.query(News).filter(News.title == form.title.data).first()
            if existing_news:
                return render_template('add_news.html', form=form, message='Такая новость уже есть')

            news = News()
            news.title = form.title.data
            news.content = form.content.data
            news.author_id = current_user.id
            news.category_id = form.category_id.data

            if 'sa' in request.form:
                news.status = 'Черновик'
            elif 'submit' in request.form:
                if current_user.level == 'moderator' or current_user.level == 'admin':
                    news.status = 'Опубликовано'
                else:
                    news.status = 'На проверке'

            news.created_at = datetime.datetime.now()
            news.published_at = datetime.datetime.now()

            # Обработка изображения
            if form.image.data and form.image.data.filename:
                image_file = form.image.data
                filename = secure_filename(image_file.filename)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(file_path)
                news.image_filename = f"uploads/news/{filename}"
            else:
                news.image_filename = 'images/default.png'

            db_sess.add(news)
            db_sess.commit()

            # Перенаправляем с сообщением об успехе
            if news.status == 'Черновик':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('index'))

    except Exception as e:
        db_sess.rollback()
        print(f"Ошибка: {e}")
        return render_template('add_news.html', form=form, message='Ошибка при сохранении новости')
    finally:
        db_sess.close()

    return render_template('add_news.html', form=form)


@app.route('/news/<int:id>')
def view_news(id):
    """Просмотр отдельной новости"""
    form = ModerationForm()
    db_sess = db_session.create_session()
    try:
        news = db_sess.query(News).filter(News.id == id).first()
        if not news:
            return "Новость не найдена", 404

        author = db_sess.query(User).filter(User.id == news.author_id).first()
        news.author_name = author.username if author else 'Неизвестный автор'

        category = db_sess.query(Categories).filter(Categories.id == news.category_id).first()
        news.category_name = category.name if category else 'Без категории'

        return render_template('view_news.html', news=news, current_user=current_user, form=form)
    finally:
        db_sess.close()


@app.route('/moderation')
@login_required
def moderation():
    """Страница модерации новостей"""
    # Проверяем права доступа
    if current_user.level not in ['moderator', 'admin'] or current_user.is_banned == 1:
        abort(403)

    db_sess = db_session.create_session()
    try:
        # Получаем новости на проверке
        news_list = db_sess.query(News).filter(News.status == 'На проверке').all()

        for article in news_list:
            author = db_sess.query(User).filter(User.id == article.author_id).first()
            article.author_name = author.username if author else 'Неизвестный автор'

            category = db_sess.query(Categories).filter(Categories.id == article.category_id).first()
            article.category_name = category.name if category else 'Без категории'

        return render_template('moderation.html', news_list=news_list, current_user=current_user)
    finally:
        db_sess.close()


@app.route('/moderate/<int:id>/<action>/')
@login_required
def moderate_news(id, action, comment='Причина не указана'):
    """Обработка модерации новости (одобрение/отклонение)"""
    if current_user.level not in ['moderator', 'admin']:
        abort(403)

    db_sess = db_session.create_session()
    try:
        news = db_sess.query(News).filter(News.id == id).first()
        if not news:
            abort(404)

        if news.status != 'На проверке':
            return redirect(url_for('moderation'))

        if action == 'approve':
            news.status = 'Опубликовано'
            message = f"Новость '{news.title}' одобрена"
        elif action == 'reject':
            news.status = 'Отклонено'
            message = f"Новость '{news.title}' отклонена"
        else:
            abort(400)

        log = ModerationLogs()
        log.news_id = id
        log.moderator_id = current_user.id
        log.action = action
        log.comment = comment
        log.timestamp = datetime.datetime.now()
        db_sess.add(log)

        db_sess.commit()
        flash(message, 'success')

        return redirect(url_for('moderation'))
    except Exception as e:
        db_sess.rollback()
        print(f"Ошибка при модерации: {e}")
        flash(f'Ошибка при модерации: {str(e)}', 'danger')
        return redirect(url_for('moderation'))
    finally:
        db_sess.close()


@app.route('/dashboard')
@login_required
def dashboard():
    """Дашборд пользователя"""
    db_sess = db_session.create_session()
    try:
        news_list = db_sess.query(News).filter(News.author_id == current_user.id).all()

        for news in news_list:
            category = db_sess.query(Categories).filter(Categories.id == news.category_id).first()
            news.category_name = category.name if category else 'Без категории'

        status_badges = {
            'Черновик': 'bg-secondary',
            'На проверке': 'bg-warning',
            'Опубликовано': 'bg-success',
            'Отклонено': 'bg-danger'
        }

        return render_template('dashboard.html',
                               news_list=news_list,
                               status_badges=status_badges,
                               current_user=current_user)
    finally:
        db_sess.close()


@app.route('/moderation/<int:id>', methods=['GET', 'POST'])
def moderate_news_id(id):
    db = db_session.create_session()
    try:
        article = db.get(News, id)

        # Проверка прав модератора
        if not current_user.is_authenticated or current_user.is_banned == 1 or not (current_user.level == 'moderator' or current_user.level == 'admin'):
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('index'))

        # Только новости на проверке можно модерировать
        if article.status != 'На проверке':
            flash('Эта новость уже была проверена', 'warning')
            return redirect(url_for('view_news', id=article.id))

        form = ModerationForm()

        if form.validate_on_submit():
            comment = form.comment.data.strip()

            if form.submit_approve.data:
                article.status = 'Опубликовано'
                article.published_at = datetime.datetime.now()
                article.moderation_comment = comment if comment else None
                flash('Новость одобрена и опубликована', 'success')

            elif form.submit_reject.data:
                article.status = 'Отклонено'
                article.moderation_comment = comment if comment else 'Отклонено без указания причины'
                flash('Новость отклонена', 'warning')

            article.moderated_at = datetime.datetime.now()
            article.moderated_by = current_user.id
            db.commit()

            return redirect(url_for('moderation'))

        return render_template('view_news.html', news=article, form=form)
    finally:
        db.close()


@app.route('/edit_news/<int:id>', methods=['GET', 'POST'])
def edit_news(id):
    db_sess = db_session.create_session()
    try:
        news = db_sess.query(News).get(id)
        form = NewsForm()

        categories = db_sess.query(Categories).all()
        form.category_id.choices = [(c.id, c.name) for c in categories]
        if request.method == 'GET':
            form.title.data = news.title
            form.content.data = news.content
            form.category_id.data = news.category_id

        if not news:
            abort(404)

        if not ((current_user.level == 'moderator' or current_user.level == 'admin') or (news.author_id == current_user.id)) or (current_user.is_banned == 1):
            abort(403)


        if form.validate_on_submit():
            existing_news = db_sess.query(News).filter(
                News.title == form.title.data,
                News.id != id
            ).first()

            if existing_news:
                return render_template('edit_news.html', form=form, news=news,
                                       message='Такая новость уже есть')

            news.title = form.title.data
            news.content = form.content.data
            news.category_id = form.category_id.data

            if 'sa' in request.form:
                news.status = 'Черновик'
            elif 'submit' in request.form:
                if 'submit' in request.form and (current_user.level in ['admin', 'moderator']):
                    news.status = 'Опубликовано'
                else:
                    news.status = 'На проверке'

            news.updated_at = datetime.datetime.now()

            if form.image.data and form.image.data.filename:
                image_file = form.image.data
                filename = secure_filename(image_file.filename)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"

                if news.image_filename and news.image_filename != 'image/default.jpg':
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                                  news.image_filename.replace('uploads/news/', ''))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(file_path)
                news.image_filename = f"uploads/news/{filename}"

            db_sess.commit()

            if news.status == 'Черновик':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('index'))

        return render_template('edit_news.html', form=form, news=news)
    finally:
        db_sess.close()


@app.route('/news/<int:id>/delete', methods=['GET', 'POST'])
@login_required
def delete_news(id):
    db_sess = db_session.create_session()
    try:
        news = db_sess.get(News, id)

        if not news:
            flash('Новость не найдена', 'danger')
            return redirect(url_for('index'))

        if current_user.id != news.author_id and current_user.level not in ['admin', 'moderator'] or (current_user.is_banned == 1):
            flash('У вас нет прав на удаление этой новости', 'danger')
            return redirect(url_for('news_detail', id=id))

        try:
            logs = db_sess.query(ModerationLogs).filter(ModerationLogs.news_id == id).all()

            for log in logs:
                db_sess.delete(log)

            db_sess.delete(news)
            db_sess.commit()
            flash('Новость успешно удалена', 'success')
        except Exception as e:
            db_sess.rollback()
            flash('Ошибка при удалении новости', 'danger')
            print(f"Error deleting news: {e}")

        return redirect(url_for('index'))
    finally:
        db_sess.close()


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    return "В разработке"


# REST API

@app.route('/api/news')
def api_get_news():
    db_sess = db_session.create_session()
    try:
        news = db_sess.query(News).filter(News.status == 'Опубликовано').all()
        return jsonify(
            {
                'news': [
                    item.to_dict(only=(
                        'id', 'title', 'content', 'status',
                        'created_at', 'published_at', 'image_filename',
                        'author.id', 'author.username',
                        'category.id', 'category.name',
                    ))
                    for item in news
                ]
            }
        )
    finally:
        db_sess.close()


@app.route('/api/news/<int:news_id>')
def api_get_one_news(news_id):
    db_sess = db_session.create_session()
    try:
        item = db_sess.query(News).filter(
            News.id == news_id,
            News.status == 'Опубликовано').first()
        if not item:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(
            {
                'news': item.to_dict(only=(
                    'id', 'title', 'content', 'status',
                    'moderation_comment', 'created_at', 'published_at', 'image_filename',
                    'author.id', 'author.username',
                    'category.id', 'category.name',
                ))
            }
        )
    finally:
        db_sess.close()


@app.route('/api/news', methods=['POST'])
def api_created_news():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Bad request', 'message': 'Ожидается JSON'}), 400

    errors = {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    author_id = data.get('author_id')
    category_id = data.get('category_id')
    status = data.get('status', 'Черновик')

    if not title:
        errors['title'] = 'Обязательное поле'
    if not content:
        errors['content'] = 'Обязательное поле'
    if not author_id:
        errors['author_id'] = 'Обязательное поле'
    if not category_id:
        errors['category_id'] = 'Обязательное поле'
    if status not in ('Черновик', 'На модерации'):
        errors['status'] = 'Допустимо: Черновик, На модерации'

    if errors:
        return jsonify({'error': 'Validation Error', 'fields': errors}), 422

    db_sess = db_session.create_session()
    try:
        news_item = News(
            title=title,
            content=content,
            author_id=author_id,
            category_id=category_id,
            status=status,
            created_at=datetime.datetime.now(),
        )
        db_sess.add(news_item)
        db_sess.commit()
        return jsonify({'news': news_item.to_dict(only=('id', 'title', 'status', 'created_at'))}), 201
    except Exception as e:
        db_sess.rollback()
        return jsonify({'error': 'Server Error', 'message': str(e)}), 500
    finally:
        db_sess.close()


@app.route("/api/news/<int:news_id>", methods=["DELETE"])
def api_delete_news(news_id):
    db_sess = db_session.create_session()
    try:
        item = db_sess.query(News).get(news_id)
        if not item:
            return jsonify({'error': 'Not found'}), 404
        db_sess.delete(item)
        db_sess.commit()
        return jsonify({'message': f'Новость #{news_id} удалена'})
    finally:
        db_sess.close()


@app.route('/api/users')
def api_get_users():
    db_sess = db_session.create_session()
    try:
        users = db_sess.query(User).all()
        return jsonify(
            {
                'users': [
                    item.to_dict(only=('id', 'username', 'level', 'created_at'))
                    for item in users
                ]
            }
        )
    finally:
        db_sess.close()


@app.route('/api/users/<int:user_id>')
def api_get_one_user(user_id):
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).get(user_id)
        if not user:
            return jsonify({'error': 'user not found'}), 404
        return jsonify(
            {
                'user': user.to_dict(only=('id', 'username', 'level', 'created_at'))
            }
        )
    finally:
        db_sess.close()


@app.route('/api/categories')
def api_get_categories():
    db_sess = db_session.create_session()
    try:
        categories = db_sess.query(Categories).order_by(Categories.name).all()
        return jsonify(
            {
                'categories': [
                    item.to_dict(only=('id', 'name'))
                    for item in categories
                ]
            }
        )
    finally:
        db_sess.close()


@app.route('/api/categories/<int:category_id>')
def api_get_one_category(category_id):
    db_sess = db_session.create_session()
    try:
        category = db_sess.query(Categories).get(category_id)
        if not category:
            return jsonify({'error': 'Not Found'}), 404
        return jsonify(
            {
                'category': category.to_dict(only=('id', 'name'))
            }
        )
    finally:
        db_sess.close()


@app.route('/api/categories', methods=['POST'])
def api_create_category():
    data = request.get_json(silent=True)
    name = (data.get('name') or '').strip() if data else ''
    if not name:
        return jsonify({'error': 'Validation Error', 'fields': {'name': 'Обязательное поле'}}), 422

    db_sess = db_session.create_session()
    try:
        cat = Categories(name=name)
        db_sess.add(cat)
        db_sess.commit()
        return jsonify({'category': cat.to_dict(only=('id', 'name'))}), 201
    except sqlalchemy.exc.IntegrityError:
        db_sess.rollback()
        return jsonify({'error': 'Conflict', 'message': 'Такая категория уже существует'}), 409
    except Exception as e:
        db_sess.rollback()
        return jsonify({'error': 'Server Error', 'message': str(e)}), 500
    finally:
        db_sess.close()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=1000, debug=True)