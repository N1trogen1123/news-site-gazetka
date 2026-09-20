from flask import abort
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from data import db_session
from data.users import User
from data.news import News
from data.categories import Categories
from data.moderation_logs import ModerationLogs

class AdminAccess(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.level == 'admin' and current_user.is_banned != 1

    def inaccessible_callback(self, name, **kwargs):
        return abort(403)

class UserAdmin(AdminAccess):
    column_list = ['id', 'username', 'email', 'level', 'is_banned', 'create_time']
    column_searchable_list = ['username', 'email']
    column_filters = ['level', 'is_banned']
    column_labels = {
        'id': 'ID', 'username': 'Имя', 'email': 'Email', 
        'level': 'Уровень', 'is_banned': 'Заблокирован', 'create_time': 'Дата регистрации'
    }
    form_columns = ['username', 'email', 'level', 'is_banned']

class NewsAdmin(AdminAccess):
    column_list = ['id', 'title', 'author_id', 'status', 'created_at']
    column_searchable_list = ['title', 'content']
    column_filters = ['status', 'author_id', 'category_id']
    column_labels = {'id': 'ID', 'title': 'Заголовок', 'author_id': 'ID автора', 'status': 'Статус', 'created_at': 'Создано'}
    form_columns = ['title', 'content', 'category_id', 'status', 'image_filename']

class CategoriesAdmin(AdminAccess):
    column_list = ['id', 'name']
    column_searchable_list = ['name']
    column_labels = {'id': 'ID', 'name': 'Название'}

class ModerationLogsAdmin(AdminAccess):
    column_list = ['id', 'news_id', 'moderator_id', 'action', 'timestamp']
    column_filters = ['action']
    column_labels = {'id': 'ID', 'news_id': 'ID новости', 'moderator_id': 'ID модератора', 'action': 'Действие', 'timestamp': 'Время'}
    can_create = False
    can_edit = False


admin = Admin(name='Админ-панель', endpoint='admin')

def init_admin(app):
    """Функция для привязки админки к приложению в фабрике"""
    admin.init_app(app)
    
    admin_db_session = db_session.create_session()
    
    # Добавляем вьюшки
    admin.add_view(UserAdmin(User, admin_db_session, name='Пользователи', endpoint='admin_users'))
    admin.add_view(NewsAdmin(News, admin_db_session, name='Новости', endpoint='admin_news'))
    admin.add_view(CategoriesAdmin(Categories, admin_db_session, name='Категории', endpoint='admin_categories'))
    admin.add_view(ModerationLogsAdmin(ModerationLogs, admin_db_session, name='Логи модерации', endpoint='mod_logs'))
