import os
import pytest
from app import create_app  # Замените app на название вашего главного модуля
from data import db_session

@pytest.fixture(scope='session')
def app():
    # 1. Переопределяем путь к БД для тестов до инициализации
    # Если в db_session.global_init() захардкожен путь, 
    # лучше передавать его аргументом, например: db_session.global_init("sqlite:///:memory:")
    # Ниже предполагается стандартный сброс сессий:
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "UPLOAD_FOLDER": "static/uploads/test_news"
    })

    # Инициализируем базу данных (внутри global_init должна быть логика создания таблиц)
    db_session.global_init() 

    yield app

    # Очистка после всех тестов
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        import shutil
        shutil.rmtree(app.config['UPLOAD_FOLDER'])

@pytest.fixture(scope='function')
def db_sess():
    # Каждая функция получает чистую сессию
    session = db_session.create_session()
    yield session
    session.close()
    # Здесь можно добавить очистку таблиц (например, DELETE FROM users), 
    # если вы используете постоянный тестовый файл БД вместо :memory:

@pytest.fixture(scope='function')
def client(app):
    # Клиент для отправки HTTP-запросов (GET, POST и т.д.)
    return app.test_client()
