from functools import wraps
from flask import request


def do_not_track():
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            request.do_not_track = True
            return f(*args, **kwargs)
        return wrapper
    return decorator
