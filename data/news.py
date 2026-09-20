from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import orm
import sqlalchemy
from .db_session import SqlAlchemyBase



class News(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'news'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    content = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    category_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('categories.id'), nullable=False)
    status = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    moderation_comment = sqlalchemy.Column(sqlalchemy.String)
    created_at = sqlalchemy.Column(sqlalchemy.TIMESTAMP)
    published_at = sqlalchemy.Column(sqlalchemy.TIMESTAMP)
    image_filename = sqlalchemy.Column(sqlalchemy.String)

    author = orm.relationship('User', back_populates='news')
    category = orm.relationship('Categories', back_populates='news')
    moderation_logs = orm.relationship('ModerationLogs', back_populates='news')

    def __repr__(self):
        return f"<News {self.id}: {self.title[:50]}>"