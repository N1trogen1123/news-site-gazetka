from data import db_session

from flask import Blueprint, request, redirect, render_template, url_for, abort, flash, jsonify
from flask_login import current_user, login_required

from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

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

        stmt = (
            select(News)
            .options(
                joinedload(News.author),
                joinedload(News.category)
            )
            .where(News.status == 'Опубликовано')
        )

        if selected_category and selected_category.isdigit():
            stmt = stmt.where(News.category_id == int(selected_category))
        
        if search_query:
            stmt = stmt.where(
                or_(
                    News.title.contains(search_query),
                    News.content.contains(search_query)
                )
            )

        stmt = stmt.order_by(News.published_at.desc())

        news_list = db_sess.scalars(stmt).all()

        categories = db_sess.scalars(select(Categories)).all()

        # Для каждой новости добавляем имя автора и категории
        for news in news_list:
            news.author_name = news.author.username if news.author else 'Неизвестный автор'
            news.category_name = news.category.name if news.category else 'Без категории'

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
        stmt = (
            select(News)
            .options(joinedload(News.category))
            .where(News.author_id == current_user.id)
        )
        news_list = db_sess.scalars(stmt).all()

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