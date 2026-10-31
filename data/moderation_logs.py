from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import orm
import sqlalchemy
from .db_session import SqlAlchemyBase

class ModerationLogs(SqlAlchemyBase):
    __tablename__ = 'moderation_logs'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True, nullable=False)
    news_id = sqlalchemy.Column(sqlalchemy.Integer,sqlalchemy.ForeignKey('news.id') ,nullable=False)
    moderator_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    action = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.TIMESTAMP)

    news = orm.relationship("News", back_populates="moderation_logs")
    moderator = orm.relationship("User", back_populates="moderator")


    def __repr__(self):
        return f"<ModerationLog {self.id}: {self.action} for news {self.news_id}>"