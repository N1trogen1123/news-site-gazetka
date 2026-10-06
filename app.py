from flask import Flask
from flask_login import LoginManager

from data import db_session
from data.users import User

from blueprints.auth import auth_bp
from blueprints.home import home_bp
from blueprints.news import news_bp
from blueprints.moderation import mod_bp

from admin_panel import init_admin

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    login_manager.init_app(app)

    app.secret_key = 'poshel-nahui-sin-blyadi-1488'

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(mod_bp)

    app.config['UPLOAD_FOLDER'] = 'static/uploads/news'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db_session.global_init()

    @login_manager.user_loader
    def load_user(user_id):
        db_sess = db_session.create_session()
        try:
            return db_sess.get(User, int(user_id))        
        finally:
            db_sess.close()
     
        init_admin(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=44678, debug=True)
