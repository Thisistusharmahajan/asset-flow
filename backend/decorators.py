from functools import wraps

from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity


def role_required(*roles):
    """Gate a route to one or more roles, e.g.

        @role_required("Admin")
        @role_required("AssetManager", "Admin")

    Always implies @jwt_required() — you don't need to stack both.
    Also rejects deactivated accounts, since a deactivated Admin
    shouldn't keep acting as one just because their token is still valid.
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            # imported lazily to avoid a circular import with models.py
            from models import Employee

            employee = Employee.query.get(get_jwt_identity())
            if not employee:
                return jsonify({"error": "account not found"}), 401
            if employee.status != "Active":
                return jsonify({"error": "this account has been deactivated"}), 403
            if employee.role not in roles:
                return jsonify({"error": "you don't have permission to do this"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
