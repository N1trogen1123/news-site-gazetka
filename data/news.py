from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from .db_session import SqlAlchemyBase
from datetime import datetime



class News(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'news'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    status: Mapped[str] = mapped_column(nullable=False)
    moderation_comment: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column()
    publisher_at: Mapped[datetime] = mapped_column()
    image_filename: Mapped[str] = mapped_column()

    author: Mapped["User"] = relationship(back_populates='news')
    category: Mapped["Categories"] = relationship(back_populates='news')
    moderation_logs: Mapped["ModerationLogs"] = relationship(back_populates='news')

    def __repr__(self):
        return f"<News {self.id}: {self.title[:50]}>"