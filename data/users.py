from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from sqlalchemy import DateTime, String, Enum as SQLEnum
from flask_login import UserMixin
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime


class UserLevel(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    # 60 символов потому что тут хранится хэш bcrypt
    hashed_password: Mapped[str] = mapped_column(String(60))
    level: Mapped[UserLevel] = mapped_column(
        SQLEnum(UserLevel),
        default=UserLevel.USER
    )
    is_banned: Mapped[bool]
    created_at: Mapped[datetime]

    news: Mapped["News"] = relationship(back_populates="author")
    moderator: Mapped["ModerationLogs"] = relationship(back_populates="moderator")


    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        result = check_password_hash(self.hashed_password, password)
        return result

    def __repr__(self):
        return f"<ModerationLog {self.id}: {self.action} for news {self.news_id}>"