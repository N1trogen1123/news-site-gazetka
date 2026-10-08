from functools import wraps
from flask import abort, g
from flask_login import current_user
from data import db_session
from data.news import News

def author_or_staff_required(f): # 1 уровень: принимает саму функцию роута
    @wraps(f)
    def decorated_function(*args, **kwargs): # 2 уровень: принимает аргументы роута
        # 1. Извлекаем id из параметров URL маршрута
        record_id = kwargs.get('id')
        if not record_id:
            abort(404)

        # 2. Создаем сессию и ищем запись в БД
        db_sess = db_session.create_session()
        
        record = db_sess.get(News, record_id)
        
        # 3. Если записи с таким id нет — возвращаем 404
        if not record:
            db_sess.close()
            abort(404)

        # 4. Проверяем, не забанен ли текущий пользователь
        if current_user.is_authenticated and current_user.is_banned == 1:
            db_sess.close()
            abort(403)

        # 5. Сверяем author_id из вашей модели с текущим пользователем
        is_author = record.author_id == current_user.id
        is_staff = current_user.level in ['admin', 'moderator']

        if not (is_author or is_staff):
            db_sess.close()
            abort(403)

        # Передаем уже найденный объект и сессию в глобальный контекст запроса Flask
        g.db_sess = db_sess
        g.active_record = record

        try:
            return f(*args, **kwargs)
        finally:
            db_sess.close()
            
    return decorated_function
