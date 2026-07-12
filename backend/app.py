import os
from datetime import datetime, timedelta, date

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    db, Employee, Department, Asset, AssetAllocation, ResourceBooking,
    TransferRequest, MaintenanceRequest, Notification
)

import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/assetflow"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY",
    "dev-secret-change-me"
)

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)

CORS(app, resources={r"/api/*": {"origins": "*"}})
db.init_app(app)
jwt = JWTManager(app)


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------

@app.post("/api/auth/signup")
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


@app.post("/api/auth/login")
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


@app.get("/api/auth/me")
@jwt_required()
def me():
    employee = Employee.query.get_or_404(get_jwt_identity())
    return jsonify(employee.to_dict())


# ---------------------------------------------------------------------
# Dashboard (Screen 2)
# ---------------------------------------------------------------------

@app.get("/api/dashboard/kpis")
@jwt_required()
def dashboard_kpis():
    today = date.today()
    week_out = today + timedelta(days=7)

    assets_available = Asset.query.filter_by(status="Available").count()
    assets_allocated = Asset.query.filter_by(status="Allocated").count()

    maintenance_today = MaintenanceRequest.query.filter(
        MaintenanceRequest.status.in_(["Technician Assigned", "In Progress"]),
        db.func.date(MaintenanceRequest.created_at) == today,
    ).count()

    active_bookings = ResourceBooking.query.filter(
        ResourceBooking.status.in_(["Upcoming", "Ongoing"])
    ).count()

    pending_transfers = TransferRequest.query.filter_by(status="Requested").count()

    upcoming_returns = AssetAllocation.query.filter(
        AssetAllocation.status == "Active",
        AssetAllocation.expected_return_date.isnot(None),
        AssetAllocation.expected_return_date >= today,
        AssetAllocation.expected_return_date <= week_out,
    ).count()

    return jsonify({
        "assets_available": assets_available,
        "assets_allocated": assets_allocated,
        "maintenance_today": maintenance_today,
        "active_bookings": active_bookings,
        "pending_transfers": pending_transfers,
        "upcoming_returns": upcoming_returns,
    })


@app.get("/api/dashboard/overdue")
@jwt_required()
def dashboard_overdue():
    today = date.today()
    overdue = (
        AssetAllocation.query
        .filter(
            AssetAllocation.status == "Active",
            AssetAllocation.expected_return_date.isnot(None),
            AssetAllocation.expected_return_date < today,
        )
        .all()
    )
    result = []
    for a in overdue:
        result.append({
            "id": a.id,
            "asset_tag": a.asset.asset_tag if a.asset else None,
            "asset_name": a.asset.name if a.asset else None,
            "holder": a.employee.name if a.employee else (a.department.name if a.department else None),
            "expected_return_date": a.expected_return_date.isoformat(),
            "days_overdue": (today - a.expected_return_date).days,
        })
    return jsonify(result)


@app.get("/api/dashboard/activity")
@jwt_required()
def dashboard_activity():
    """Recent activity feed. In this minimal build we derive it directly
    from the notifications table (populated by the seed script / would
    be populated by app-side triggers in the full build)."""
    notifications = (
        Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    )
    return jsonify([n.to_dict() for n in notifications])


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
