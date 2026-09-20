from functools import wraps
from flask import abort
from flask_login import current_user

def required_role(*roles):
    if len(roles) == 1 and isinstance(roles[0], (list, tuple)):
        allowed_roles = roles[0]
    else:
        allowed_roles = roles

    def decorator(f):
        @wraps(f)
        def decorated_func(*args, **kwargs):
            if current_user.level not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_func
    return decorator
