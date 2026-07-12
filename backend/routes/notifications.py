from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

# Which notification types fall under each tab on Screen 10.
CATEGORY_TYPES = {
    "alerts": {
        "Overdue Return Alert", "Overdue Booking Alert", "Audit Discrepancy Flagged",
    },
    "approvals": {
        "Asset Assigned", "Maintenance Approved", "Maintenance Rejected",
        "Transfer Requested", "Transfer Approved", "Transfer Rejected",
    },
    "bookings": {
        "Booking Confirmed", "Booking Cancelled", "Booking Reminder",
    },
}


def _category_for(notif_type):
    for category, types in CATEGORY_TYPES.items():
        if notif_type in types:
            return category
    return "alerts"


@notifications_bp.get("")
@jwt_required()
def list_notifications():
    """All | Alerts | Approvals | Bookings tabs on Screen 10.
    In this build notifications are visible org-wide (not just to the
    recipient) so the activity feed reads like a shared log, matching
    the mockup's single unified list."""
    category = (request.args.get("category") or "all").lower()
    limit = min(int(request.args.get("limit", 50)), 200)

    notifications = (
        Notification.query.order_by(Notification.created_at.desc()).limit(200).all()
    )

    if category != "all":
        notifications = [n for n in notifications if _category_for(n.type) == category]

    data = []
    for n in notifications[:limit]:
        d = n.to_dict()
        d["category"] = _category_for(n.type)
        data.append(d)

    return jsonify(data)


@notifications_bp.patch("/<notification_id>/read")
@jwt_required()
def mark_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    return jsonify(notification.to_dict())


@notifications_bp.post("/mark-all-read")
@jwt_required()
def mark_all_read():
    Notification.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"status": "ok"})
