from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models import Employee

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/signup")
def signup():
    """Signup ALWAYS creates a plain Employee account. No role selection
    here — roles are only ever assigned later by an Admin from the
    Organization Setup > Employee Directory screen."""
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    if Employee.query.filter_by(email=email).first():
        return jsonify({"error": "an account with this email already exists"}), 409

    employee = Employee(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role="Employee",
        status="Active",
    )
    db.session.add(employee)
    db.session.commit()

    token = create_access_token(identity=employee.id)
    return jsonify({"token": token, "user": employee.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    employee = Employee.query.filter_by(email=email).first()
    if not employee or not check_password_hash(employee.password_hash, password):
        return jsonify({"error": "invalid email or password"}), 401
    if employee.status != "Active":
        return jsonify({"error": "this account has been deactivated"}), 403

    employee.last_login_at = datetime.utcnow()
    db.session.commit()

    token = create_access_token(identity=employee.id)
    return jsonify({"token": token, "user": employee.to_dict()}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    employee = Employee.query.get_or_404(get_jwt_identity())
    return jsonify(employee.to_dict())
