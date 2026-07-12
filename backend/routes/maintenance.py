from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Asset, MaintenanceRequest, AssetStatusHistory
from decorators import role_required

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/api/maintenance")

# Kanban columns, in board order
STATUSES = ["Pending", "Approved", "Technician Assigned", "In Progress", "Resolved"]


@maintenance_bp.get("")
@jwt_required()
def list_maintenance_requests():
    """Returns every open/resolved maintenance ticket — the frontend buckets
    these into kanban columns by status."""
    asset_id = request.args.get("asset_id")
    status = request.args.get("status")

    q = MaintenanceRequest.query
    if asset_id:
        q = q.filter_by(asset_id=asset_id)
    if status:
        q = q.filter_by(status=status)

    requests_ = q.order_by(MaintenanceRequest.created_at.desc()).all()
    return jsonify([r.to_dict() for r in requests_])


@maintenance_bp.post("")
@jwt_required()
def create_maintenance_request():
    """Any signed-in employee can raise a ticket for an asset — starts in Pending."""
    data = request.get_json(force=True) or {}
    asset_id = data.get("asset_id")
    issue_description = (data.get("issue_description") or "").strip()

    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"error": "asset not found"}), 400
    if not issue_description:
        return jsonify({"error": "issue_description is required"}), 400

    ticket = MaintenanceRequest(
        asset_id=asset_id,
        raised_by=get_jwt_identity(),
        issue_description=issue_description,
        status="Pending",
    )
    db.session.add(ticket)
    db.session.commit()
    return jsonify(ticket.to_dict()), 201


@maintenance_bp.patch("/<request_id>")
@role_required("AssetManager", "Admin")
def update_maintenance_request(request_id):
    """Drives the kanban card moves. Approving a card moves the asset to
    'Under Maintenance'; resolving it returns the asset to 'Available'."""
    ticket = MaintenanceRequest.query.get_or_404(request_id)
    data = request.get_json(force=True) or {}

    if "status" in data:
        new_status = data["status"]
        if new_status not in STATUSES:
            return jsonify({"error": f"status must be one of {STATUSES}"}), 400

        asset = ticket.asset

        if new_status == "Approved" and ticket.status == "Pending":
            db.session.add(AssetStatusHistory(
                asset_id=asset.id,
                from_status=asset.status,
                to_status="Under Maintenance",
                changed_by=get_jwt_identity(),
                notes=f"Maintenance approved: {ticket.issue_description}",
            ))
            asset.status = "Under Maintenance"

        if new_status == "Resolved" and ticket.status != "Resolved":
            db.session.add(AssetStatusHistory(
                asset_id=asset.id,
                from_status=asset.status,
                to_status="Available",
                changed_by=get_jwt_identity(),
                notes=data.get("notes") or "Maintenance resolved",
            ))
            asset.status = "Available"
            ticket.resolved_at = datetime.utcnow()

        ticket.status = new_status

    if "technician_name" in data:
        ticket.technician_name = data["technician_name"]
    if "notes" in data:
        ticket.notes = data["notes"]

    db.session.commit()
    return jsonify(ticket.to_dict())
