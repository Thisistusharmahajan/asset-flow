from datetime import datetime, date

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Asset, Employee, AssetAllocation, TransferRequest, AssetStatusHistory
from decorators import role_required

allocations_bp = Blueprint("allocations", __name__, url_prefix="/api")


def _active_allocation(asset_id):
    return (
        AssetAllocation.query
        .filter_by(asset_id=asset_id, status="Active")
        .order_by(AssetAllocation.allocated_date.desc())
        .first()
    )


def _transfer_dict(t):
    return {
        "id": t.id,
        "asset_id": t.asset_id,
        "asset_tag": t.asset.asset_tag if t.asset else None,
        "asset_name": t.asset.name if t.asset else None,
        "from_employee_id": t.from_employee_id,
        "from_employee_name": t.from_employee.name if t.from_employee else None,
        "to_employee_id": t.to_employee_id,
        "to_employee_name": t.to_employee.name if t.to_employee else None,
        "requested_by": t.requested_by,
        "reason": t.rejection_reason if t.status == "Rejected" else None,
        "status": t.status,
        "requested_at": t.requested_at.isoformat() if t.requested_at else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
    }


# ---------------------------------------------------------------------
# Allocation status for an asset — drives the "already allocated" block
# ---------------------------------------------------------------------

@allocations_bp.get("/assets/<asset_id>/allocation")
@jwt_required()
def get_asset_allocation(asset_id):
    Asset.query.get_or_404(asset_id)
    alloc = _active_allocation(asset_id)
    if not alloc:
        return jsonify({"allocated": False})
    return jsonify({
        "allocated": True,
        "allocation_id": alloc.id,
        "employee_id": alloc.employee_id,
        "employee_name": alloc.employee.name if alloc.employee else None,
        "department_name": alloc.employee.department.name if alloc.employee and alloc.employee.department else None,
        "allocated_date": alloc.allocated_date.isoformat() if alloc.allocated_date else None,
    })


@allocations_bp.get("/assets/<asset_id>/allocation-history")
@jwt_required()
def get_allocation_history(asset_id):
    Asset.query.get_or_404(asset_id)
    events = []

    allocations = AssetAllocation.query.filter_by(asset_id=asset_id).order_by(
        AssetAllocation.allocated_date.desc()
    ).all()
    for a in allocations:
        holder = a.employee.name if a.employee else (a.department.name if a.department else "Unknown")
        events.append({
            "date": a.allocated_date.isoformat() if a.allocated_date else None,
            "description": f"Allocated to {holder}" + (
                f" - {a.department.name}" if a.employee and a.employee.department else ""
            ),
        })
        if a.actual_return_date:
            events.append({
                "date": a.actual_return_date.isoformat(),
                "description": f"Returned by {holder}" + (
                    "" if not a.status else f" - status: {a.status}"
                ),
            })

    events.sort(key=lambda e: e["date"] or "", reverse=True)
    return jsonify(events)


# ---------------------------------------------------------------------
# Direct allocation — blocked if the asset already has an active holder
# ---------------------------------------------------------------------

@allocations_bp.post("/assets/<asset_id>/allocate")
@role_required("AssetManager", "Admin")
def allocate_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    data = request.get_json(force=True) or {}
    employee_id = data.get("employee_id")

    if not employee_id or not Employee.query.get(employee_id):
        return jsonify({"error": "a valid employee_id is required"}), 400

    existing = _active_allocation(asset_id)
    if existing:
        holder = existing.employee.name if existing.employee else "someone"
        dept = existing.employee.department.name if existing.employee and existing.employee.department else None
        return jsonify({
            "error": f"Already allocated to {holder}" + (f" ({dept})" if dept else ""),
            "code": "ALREADY_ALLOCATED",
            "current_holder": holder,
            "department": dept,
        }), 409

    allocation = AssetAllocation(
        asset_id=asset_id,
        employee_id=employee_id,
        allocated_date=date.today(),
        expected_return_date=data.get("expected_return_date"),
        status="Active",
    )
    db.session.add(allocation)

    db.session.add(AssetStatusHistory(
        asset_id=asset_id,
        from_status=asset.status,
        to_status="Allocated",
        changed_by=get_jwt_identity(),
        notes="Direct allocation",
    ))
    asset.status = "Allocated"
    db.session.commit()
    return jsonify({"id": allocation.id}), 201


# ---------------------------------------------------------------------
# Transfer requests — the only path to re-assign an already-allocated asset
# ---------------------------------------------------------------------

@allocations_bp.get("/transfer-requests")
@jwt_required()
def list_transfer_requests():
    asset_id = request.args.get("asset_id")
    status = request.args.get("status")

    q = TransferRequest.query
    if asset_id:
        q = q.filter_by(asset_id=asset_id)
    if status:
        q = q.filter_by(status=status)

    requests_ = q.order_by(TransferRequest.requested_at.desc()).all()
    return jsonify([_transfer_dict(t) for t in requests_])


@allocations_bp.post("/transfer-requests")
@role_required("AssetManager", "Admin", "DepartmentHead")
def create_transfer_request():
    data = request.get_json(force=True) or {}
    asset_id = data.get("asset_id")
    to_employee_id = data.get("to_employee_id")
    reason = (data.get("reason") or "").strip()

    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"error": "asset not found"}), 400
    if not to_employee_id or not Employee.query.get(to_employee_id):
        return jsonify({"error": "a valid to_employee_id is required"}), 400
    if not reason:
        return jsonify({"error": "a reason is required"}), 400

    current_alloc = _active_allocation(asset_id)
    if current_alloc and current_alloc.employee_id == to_employee_id:
        return jsonify({"error": "asset is already allocated to this employee"}), 400

    transfer = TransferRequest(
        asset_id=asset_id,
        current_allocation_id=current_alloc.id if current_alloc else None,
        from_employee_id=current_alloc.employee_id if current_alloc else None,
        to_employee_id=to_employee_id,
        requested_by=get_jwt_identity(),
        status="Requested",
        rejection_reason=reason,  # reused as the "reason for request" field
    )
    db.session.add(transfer)
    db.session.commit()
    return jsonify(_transfer_dict(transfer)), 201


@allocations_bp.patch("/transfer-requests/<transfer_id>")
@role_required("AssetManager", "Admin")
def resolve_transfer_request(transfer_id):
    """Approve or reject a pending transfer. Approving performs the actual
    re-allocation: closes the current active allocation and opens a new one."""
    transfer = TransferRequest.query.get_or_404(transfer_id)
    data = request.get_json(force=True) or {}
    action = data.get("action")

    if transfer.status != "Requested":
        return jsonify({"error": "this request has already been resolved"}), 400
    if action not in ("approve", "reject"):
        return jsonify({"error": "action must be 'approve' or 'reject'"}), 400

    if action == "reject":
        transfer.status = "Rejected"
        transfer.resolved_at = datetime.utcnow()
        transfer.approved_by = get_jwt_identity()
        db.session.commit()
        return jsonify(_transfer_dict(transfer))

    asset = Asset.query.get(transfer.asset_id)

    if transfer.current_allocation_id:
        current = AssetAllocation.query.get(transfer.current_allocation_id)
        if current and current.status == "Active":
            current.status = "Returned"
            current.actual_return_date = date.today()

    new_allocation = AssetAllocation(
        asset_id=transfer.asset_id,
        employee_id=transfer.to_employee_id,
        allocated_date=date.today(),
        status="Active",
    )
    db.session.add(new_allocation)
    db.session.flush()

    transfer.new_allocation_id = new_allocation.id
    transfer.status = "Approved"
    transfer.resolved_at = datetime.utcnow()
    transfer.approved_by = get_jwt_identity()

    db.session.add(AssetStatusHistory(
        asset_id=asset.id,
        from_status=asset.status,
        to_status="Allocated",
        changed_by=get_jwt_identity(),
        notes="Transfer approved",
    ))
    asset.status = "Allocated"

    db.session.commit()
    return jsonify(_transfer_dict(transfer))