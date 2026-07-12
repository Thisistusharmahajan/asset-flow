from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_

from extensions import db
from models import Asset, ResourceBooking

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api")


def _booking_dict(b):
    return {
        "id": b.id,
        "asset_id": b.asset_id,
        "asset_name": b.asset.name if b.asset else None,
        "booked_by": b.booked_by,
        "booked_by_name": b.booker.name if getattr(b, "booker", None) else None,
        "start_time": b.start_time.isoformat() if b.start_time else None,
        "end_time": b.end_time.isoformat() if b.end_time else None,
        "status": b.status,
    }


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------
# Bookable resources (assets flagged is_bookable) — for the picker
# ---------------------------------------------------------------------

@bookings_bp.get("/resources")
@jwt_required()
def list_bookable_resources():
    resources = Asset.query.filter_by(is_bookable=True).order_by(Asset.name.asc()).all()
    return jsonify([{"id": a.id, "name": a.name, "location": a.location} for a in resources])


# ---------------------------------------------------------------------
# Bookings for a resource on a given day
# ---------------------------------------------------------------------

@bookings_bp.get("/bookings")
@jwt_required()
def list_bookings():
    asset_id = request.args.get("asset_id")
    date_str = request.args.get("date")  # YYYY-MM-DD

    if not asset_id:
        return jsonify({"error": "asset_id is required"}), 400

    q = ResourceBooking.query.filter_by(asset_id=asset_id)
    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "date must be YYYY-MM-DD"}), 400
        q = q.filter(db.func.date(ResourceBooking.start_time) == day)

    bookings = q.order_by(ResourceBooking.start_time.asc()).all()
    return jsonify([_booking_dict(b) for b in bookings])


@bookings_bp.post("/bookings")
@jwt_required()
def create_booking():
    """Books a slot for a resource. Blocks if it overlaps an existing
    Upcoming/Ongoing booking on the same resource."""
    data = request.get_json(force=True) or {}
    asset_id = data.get("asset_id")
    start_time = _parse_dt(data.get("start_time"))
    end_time = _parse_dt(data.get("end_time"))

    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"error": "resource not found"}), 400
    if not asset.is_bookable:
        return jsonify({"error": "this resource is not bookable"}), 400
    if not start_time or not end_time or end_time <= start_time:
        return jsonify({"error": "a valid start_time and end_time are required"}), 400

    conflict = ResourceBooking.query.filter(
        ResourceBooking.asset_id == asset_id,
        ResourceBooking.status.in_(["Upcoming", "Ongoing"]),
        and_(
            ResourceBooking.start_time < end_time,
            ResourceBooking.end_time > start_time,
        ),
    ).first()

    if conflict:
        return jsonify({
            "error": "Requested slot conflicts with an existing booking - slot is unavailable",
            "code": "SLOT_CONFLICT",
            "conflict": _booking_dict(conflict),
        }), 409

    booking = ResourceBooking(
        asset_id=asset_id,
        booked_by=get_jwt_identity(),
        start_time=start_time,
        end_time=end_time,
        status="Upcoming",
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify(_booking_dict(booking)), 201


@bookings_bp.patch("/bookings/<booking_id>")
@jwt_required()
def update_booking(booking_id):
    booking = ResourceBooking.query.get_or_404(booking_id)
    data = request.get_json(force=True) or {}

    if "status" in data:
        if data["status"] not in ("Upcoming", "Ongoing", "Completed", "Cancelled"):
            return jsonify({"error": "invalid status"}), 400
        booking.status = data["status"]

    db.session.commit()
    return jsonify(_booking_dict(booking))