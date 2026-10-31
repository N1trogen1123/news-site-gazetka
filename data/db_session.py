import os
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session

class SqlAlchemyBase(orm.DeclarativeBase):
    pass

# scoped_session для потокобезопасности в продакшене
session_factory = None
db_session: orm.scoped_session = None


def global_init(db_url: str = None):
    """Инициализация движка и фабрики сессий."""
    global session_factory, db_session

    if db_session:
        return

    # Если URL не передан, пытаемся взять из окружения, иначе падаем на дефолтный sqlite
    if not db_url:
        db_url = os.getenv("DATABASE_URL", "sqlite:///db/news.db")

    # Для SQLite автоматически добавляем фикс многопоточности
    if db_url.startswith("sqlite://"):
        if "?" not in db_url:
            db_url += "?check_same_thread=False"
        elif "check_same_thread" not in db_url:
            db_url += "&check_same_thread=False"

    print(f" Подключение к БД: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    engine = sa.create_engine(url=db_url, echo=True)
    
    session_factory = orm.sessionmaker(bind=engine, expire_on_commit=False)
    
    # scoped_session гарантирует, что каждый веб-запрос получит свою изолированную сессию
    db_session = orm.scoped_session(session_factory)

    # Импортируем модели, чтобы SQLAlchemy знал о них
    from . import __all_models

    #SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    """Возвращает потокобезопасную сессию."""
    global db_session
    if not db_session:
        raise Exception("База данных не инициализирована. Вызовите global_init() сначала.")
    return db_session()
