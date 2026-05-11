from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy
from sqlalchemy import orm
from flask_login import UserMixin
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    level = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    is_banned = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime)

    news = orm.relationship("News", back_populates="author")
    moderator = orm.relationship("ModerationLogs", back_populates="moderator")

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        result = check_password_hash(self.hashed_password, password)
        return result

    def __repr__(self):
        return f"<ModerationLog {self.id}: {self.action} for news {self.news_id}>"