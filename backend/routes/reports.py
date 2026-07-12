from datetime import datetime, timedelta, date

from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required

from extensions import db
from models import (
    Asset, Department, AssetAllocation, ResourceBooking, MaintenanceRequest,
)

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@reports_bp.get("/utilization-by-department")
@jwt_required()
def utilization_by_department():
    """Bar chart data: active allocations per department right now."""
    rows = (
        db.session.query(Department.name, db.func.count(AssetAllocation.id))
        .outerjoin(
            AssetAllocation,
            db.and_(
                AssetAllocation.department_id == Department.id,
                AssetAllocation.status == "Active",
            ),
        )
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
        .all()
    )
    return jsonify([{"department": name, "count": count} for name, count in rows])


@reports_bp.get("/maintenance-frequency")
@jwt_required()
def maintenance_frequency():
    """Line chart data: maintenance tickets raised per month, last 6 months."""
    today = date.today().replace(day=1)
    months = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    counts = []
    for y, m in months:
        start = date(y, m, 1)
        end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        n = MaintenanceRequest.query.filter(
            MaintenanceRequest.created_at >= start,
            MaintenanceRequest.created_at < end,
        ).count()
        counts.append({"label": start.strftime("%b"), "count": n})

    return jsonify(counts)


@reports_bp.get("/most-used")
@jwt_required()
def most_used_assets():
    """Top 5 assets by usage: booking count for bookable resources,
    allocation count for everything else."""
    limit = min(int(request.args.get("limit", 5)), 20)

    booking_counts = dict(
        db.session.query(ResourceBooking.asset_id, db.func.count(ResourceBooking.id))
        .filter(ResourceBooking.status != "Cancelled")
        .group_by(ResourceBooking.asset_id)
        .all()
    )
    allocation_counts = dict(
        db.session.query(AssetAllocation.asset_id, db.func.count(AssetAllocation.id))
        .group_by(AssetAllocation.asset_id)
        .all()
    )

    results = []
    for asset in Asset.query.all():
        if asset.is_bookable:
            count = booking_counts.get(asset.id, 0)
            unit = "bookings this month"
        else:
            count = allocation_counts.get(asset.id, 0)
            unit = "uses"
        if count > 0:
            results.append({
                "asset_tag": asset.asset_tag,
                "asset_name": asset.name,
                "count": count,
                "unit": unit,
            })

    results.sort(key=lambda r: r["count"], reverse=True)
    return jsonify(results[:limit])


@reports_bp.get("/idle")
@jwt_required()
def idle_assets():
    """Assets with no allocation or booking activity in the last N days."""
    limit = min(int(request.args.get("limit", 5)), 20)
    threshold_days = int(request.args.get("threshold_days", 30))
    now = datetime.utcnow()

    results = []
    for asset in Asset.query.filter(Asset.status == "Available").all():
        last_alloc = (
            AssetAllocation.query.filter_by(asset_id=asset.id)
            .order_by(AssetAllocation.created_at.desc())
            .first()
        )
        last_booking = (
            ResourceBooking.query.filter_by(asset_id=asset.id)
            .order_by(ResourceBooking.start_time.desc())
            .first()
        )

        last_activity = None
        if last_alloc:
            last_activity = last_alloc.created_at
        if last_booking and (not last_activity or last_booking.start_time > last_activity):
            last_activity = last_booking.start_time

        if last_activity is None:
            days_idle = (now - asset.created_at).days if asset.created_at else 9999
        else:
            days_idle = (now - last_activity).days

        if days_idle >= threshold_days:
            results.append({
                "asset_tag": asset.asset_tag,
                "asset_name": asset.name,
                "days_idle": days_idle,
            })

    results.sort(key=lambda r: r["days_idle"], reverse=True)
    return jsonify(results[:limit])


@reports_bp.get("/maintenance-due")
@jwt_required()
def maintenance_due():
    """Assets whose warranty expires soon, or that are old enough to be
    nearing retirement (>4 years since purchase)."""
    soon = date.today() + timedelta(days=30)
    retirement_cutoff = date.today().replace(year=date.today().year - 4)

    due_soon = Asset.query.filter(
        Asset.warranty_expiry.isnot(None),
        Asset.warranty_expiry <= soon,
        Asset.warranty_expiry >= date.today(),
    ).all()

    nearing_retirement = Asset.query.filter(
        Asset.purchase_date.isnot(None),
        Asset.purchase_date <= retirement_cutoff,
        Asset.status.notin_(["Retired", "Disposed", "Lost"]),
    ).all()

    results = []
    for a in due_soon:
        days = (a.warranty_expiry - date.today()).days
        results.append({
            "asset_tag": a.asset_tag, "asset_name": a.name,
            "reason": f"service due in {days} days" if days > 0 else "service due now",
        })
    for a in nearing_retirement:
        years = date.today().year - a.purchase_date.year
        results.append({
            "asset_tag": a.asset_tag, "asset_name": a.name,
            "reason": f"{years} years old — nearing retirement",
        })

    return jsonify(results)


@reports_bp.get("/export")
@jwt_required()
def export_report():
    """CSV export of the current asset directory (the 'Export report' button)."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Asset Tag", "Name", "Category", "Department", "Status",
        "Location", "Condition", "Purchase Date", "Purchase Cost",
    ])
    for a in Asset.query.order_by(Asset.asset_tag).all():
        writer.writerow([
            a.asset_tag, a.name,
            a.category.name if a.category else "",
            a.department.name if a.department else "",
            a.status, a.location or "", a.condition or "",
            a.purchase_date.isoformat() if a.purchase_date else "",
            a.purchase_cost if a.purchase_cost is not None else "",
        ])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=assetflow-report.csv"},
    )
