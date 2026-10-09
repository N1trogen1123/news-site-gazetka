import datetime
import os

from sqlalchemy import select, delete

from data import db_session
from data.categories import Categories
from data.news import News
from data.users import User

from flask import Blueprint, render_template, url_for, flash, request, redirect, current_app, abort

from flask_login import current_user, login_required

from decorators.is_banned import is_banned
from decorators.is_user_author_or_staff import author_or_staff_required

from forms.Newsform import NewsForm

from werkzeug.utils import secure_filename

news_bp = Blueprint('news', __name__)

@news_bp.route('/add_news', methods=['GET', 'POST'])
@login_required
@is_banned
def add_news():
    form = NewsForm()
    db_sess = db_session.create_session()
    try:
        categories = db_sess.scalars(select(Categories)).all()
        form.category_id.choices = [(c.id, c.name) for c in categories]

        if form.validate_on_submit():
            existing_news = db_sess.scalars(select(News)).where(News.title == form.title.data).first()
            if existing_news:
                return render_template('add_news.html', form=form, message='Такая новость уже есть')

            news = News()
            form.populate_obj(news)

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

                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                image_file.save(file_path)
                news.image_filename = f"uploads/news/{filename}"
            else:
                news.image_filename = 'images/default.png'

            db_sess.add(news)
            db_sess.commit()

            # Перенаправляем с сообщением об успехе
            if news.status == 'Черновик':
                return redirect(url_for('home.dashboard'))
            else:
                return redirect(url_for('home.index'))

        return render_template('add_news.html', form=form)
    except Exception as e:
        db_sess.rollback()
        print(f"Ошибка: {e}")
        return render_template('add_news.html', form=form, message='Ошибка при сохранении новости')
    finally:
        db_sess.close()

    
@news_bp.route('/news/<int:id>')
@is_banned
def view_news(id):
    """Просмотр отдельной новости"""
    db_sess = db_session.create_session()
    try:
        news = db_sess.scalars(select(News)).where(News.id == id).first()
        if not news:
            return "Новость не найдена", 404

        author = db_sess.scalars(select(User)).where(User.id == news.author_id).first()
        news.author_name = author.username if author else 'Неизвестный автор'

        category = db_sess.scalars(select(Categories)).where(Categories.id == news.category_id).first()
        news.category_name = category.name if category else 'Без категории'

        return render_template('view_news.html', news=news, current_user=current_user)
    finally:
        db_sess.close()

@news_bp.route('/edit_news/<int:id>', methods=['GET', 'POST'])
@login_required
@is_banned
@author_or_staff_required
def edit_news(id):
    db_sess = db_session.create_session()
    try:
        news = db_sess.get(News, id)

        if not news:
            abort(404)

        form = NewsForm()

        categories = db_sess.scalars(select(Categories)).all()
        form.category_id.choices = [(c.id, c.name) for c in categories]
        if request.method == 'GET':
            form.title.data = news.title
            form.content.data = news.content
            form.category_id.data = news.category_id

        if not news:
            abort(404)


        if form.validate_on_submit():
            existing_news = db_sess.scalars(select(News)).where(
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
                    old_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                                  news.image_filename.replace('uploads/news/', ''))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                image_file.save(file_path)
                news.image_filename = f"uploads/news/{filename}"

            db_sess.commit()

            if news.status == 'Черновик':
                return redirect(url_for('home.dashboard'))
            else:
                return redirect(url_for('home.index'))

        return render_template('edit_news.html', form=form, news=news)
    finally:
        db_sess.close()
        
@news_bp.route('/news/<int:id>/delete', methods=['GET', 'POST'])
@login_required
@author_or_staff_required
@is_banned
def delete_news(id):
    db_sess = db_session.create_session()
    try:
        news = db_sess.get(News, id)

        if not news:
            flash('Новость не найдена', 'danger')
            return redirect(url_for('index'))
        try:
            db_sess.execute(delete(ModerationLogs).where(ModerationLogs.news_id == id))

            db_sess.delete(news)
            db_sess.commit()
            flash('Новость успешно удалена', 'success')
        except Exception as e:
            db_sess.rollback()
            flash('Ошибка при удалении новости', 'danger')
            print(f"Error deleting news: {e}")

        return redirect(url_for('home.index'))
    finally:
        db_sess.close()