from datetime import timedelta, date

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from extensions import db
from models import Asset, MaintenanceRequest, ResourceBooking, TransferRequest, AssetAllocation, Notification

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/kpis")
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


@dashboard_bp.get("/overdue")
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


@dashboard_bp.get("/activity")
@jwt_required()
def dashboard_activity():
    """Recent activity feed. In this minimal build we derive it directly
    from the notifications table (populated by the seed script / would
    be populated by app-side triggers in the full build)."""
    notifications = (
        Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    )
    return jsonify([n.to_dict() for n in notifications])
