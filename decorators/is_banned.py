from functools import wraps
from flask import abort, jsonify
from flask_login import current_user


def is_banned(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if current_user.is_banned:
            return jsonify({'message': 'Вы забанены на этом сайте'}), 403
        return f(*args, **kwargs)
    return decorated_func
