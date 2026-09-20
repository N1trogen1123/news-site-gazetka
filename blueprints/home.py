from data import db_session

from flask import Blueprint, request, redirect, render_template, url_for, abort, flash, jsonify
from flask_login import current_user, login_required

from data.news import News
from data.categories import Categories

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
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


@home_bp.route('/dashboard')
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