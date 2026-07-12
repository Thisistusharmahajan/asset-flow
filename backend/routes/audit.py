from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Asset, Department, AuditCycle, AuditItem
from decorators import role_required

audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit-cycles")


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@audit_bp.get("")
@jwt_required()
def list_audit_cycles():
    status = request.args.get("status")
    q = AuditCycle.query
    if status:
        q = q.filter_by(status=status)
    cycles = q.order_by(AuditCycle.created_at.desc()).all()
    return jsonify([c.to_dict() for c in cycles])


@audit_bp.post("")
@role_required("AssetManager", "Admin")
def create_audit_cycle():
    """Starts an audit cycle and seeds one checklist row per asset in the
    department (or every asset, if no department is given)."""
    data = request.get_json(force=True) or {}
    title = (data.get("title") or "").strip()
    department_id = data.get("department_id") or None

    if not title:
        return jsonify({"error": "title is required"}), 400
    if department_id and not Department.query.get(department_id):
        return jsonify({"error": "department not found"}), 400

    cycle = AuditCycle(
        title=title,
        department_id=department_id,
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        auditor_names=data.get("auditor_names"),
        status="Open",
        created_by=get_jwt_identity(),
    )
    db.session.add(cycle)
    db.session.flush()

    assets_q = Asset.query
    if department_id:
        assets_q = assets_q.filter_by(department_id=department_id)

    for asset in assets_q.all():
        db.session.add(AuditItem(
            audit_cycle_id=cycle.id,
            asset_id=asset.id,
            expected_location=asset.location,
            verification="Unverified",
        ))

    db.session.commit()
    return jsonify(cycle.to_dict(include_items=True)), 201


@audit_bp.get("/<cycle_id>")
@jwt_required()
def get_audit_cycle(cycle_id):
    cycle = AuditCycle.query.get_or_404(cycle_id)
    return jsonify(cycle.to_dict(include_items=True))


@audit_bp.patch("/items/<item_id>")
@jwt_required()
def update_audit_item(item_id):
    """Records a checklist verification result: Verified | Missing | Damaged."""
    item = AuditItem.query.get_or_404(item_id)
    data = request.get_json(force=True) or {}

    verification = data.get("verification")
    if verification not in ("Unverified", "Verified", "Missing", "Damaged"):
        return jsonify({"error": "invalid verification value"}), 400

    item.verification = verification
    if "notes" in data:
        item.notes = data["notes"]
    item.verified_by = get_jwt_identity()
    item.verified_at = datetime.utcnow()

    db.session.commit()
    return jsonify(item.to_dict())


@audit_bp.post("/<cycle_id>/close")
@role_required("AssetManager", "Admin")
def close_audit_cycle(cycle_id):
    """Closes the cycle. Any items left Missing/Damaged are what the
    auto-generated discrepancy report is built from."""
    cycle = AuditCycle.query.get_or_404(cycle_id)
    if cycle.status == "Closed":
        return jsonify({"error": "this audit cycle is already closed"}), 400

    cycle.status = "Closed"
    cycle.closed_at = datetime.utcnow()
    db.session.commit()

    flagged = AuditItem.query.filter(
        AuditItem.audit_cycle_id == cycle.id,
        AuditItem.verification.in_(["Missing", "Damaged"]),
    ).all()

    return jsonify({
        "cycle": cycle.to_dict(),
        "discrepancy_report": [i.to_dict() for i in flagged],
    })
