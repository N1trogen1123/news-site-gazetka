from sqlalchemy_serializer import SerializerMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from .db_session import SqlAlchemyBase

class Categories(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String())

    news: Mapped["News"] = relationship(back_populates='category')


    def __repr__(self):
        return f"<Category {self.id}: {self.name}>"