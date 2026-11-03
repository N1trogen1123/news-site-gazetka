import os
import pytest
from app import create_app
from data import db_session

from data.users import User

from werkzeug.security import generate_password_hash

@pytest.fixture(scope='session')
def app():

    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-key-nahui-pohui",
        "UPLOAD_FOLDER": "static/uploads/test_news",
        "SQLALCHEMY_DATABASE_URI": 'sqlite:///:memory:'
    })

    # Инициализируем базу данных (внутри global_init должна быть логика создания таблиц)
    db_session.global_init() 

    yield app

    # Очистка после всех тестов
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        import shutil
        shutil.rmtree(app.config['UPLOAD_FOLDER'])

@pytest.fixture(scope='session')
def db_sess():
    session = db_session.create_session()
    yield session
    session.close()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def authenticated_client(client, db_sess):
    client.post('/auth/login', data={'email': 'test3333@test.com', 'password': '12345'}, follow_redirects=True)
    return client
