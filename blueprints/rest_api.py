from flask import Blueprint, jsonify, request

import sqlalchemy.exc

from data.users import User
from data.news import News
from data.categories import Categories

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/news')
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


@api_bp.route('/api/news/<int:news_id>')
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


@api_bp.route('/api/news', methods=['POST'])
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


@api_bp.route("/api/news/<int:news_id>", methods=["DELETE"])
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


@api_bp.route('/api/users')
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


@api_bp.route('/api/users/<int:user_id>', methods=['GET'])
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


@api_bp.route('/api/categories', methods=['GET'])
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


@api_bp.route('/api/categories/<int:category_id>')
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


@api_bp.route('/api/categories', methods=['POST'])
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

