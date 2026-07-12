import re
from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_

from extensions import db
from models import (
    Asset, AssetCategory, Department, AssetStatusHistory, AssetDocument,
    AssetAllocation,
)
from decorators import role_required

assets_bp = Blueprint("assets", __name__, url_prefix="/api/assets")

VALID_STATUSES = {
    "Available", "Allocated", "Reserved", "Under Maintenance",
    "Lost", "Retired", "Disposed",
}
ASSET_TAG_PREFIX = "AF"
ASSET_TAG_RE = re.compile(rf"^{ASSET_TAG_PREFIX}-(\d+)$")


def _next_asset_tag():
    """AF-0001, AF-0002, ... — derived from the highest existing numeric
    suffix rather than a row count, so it stays correct after deletions."""
    max_n = 0
    for (tag,) in db.session.query(Asset.asset_tag).all():
        m = ASSET_TAG_RE.match(tag or "")
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"{ASSET_TAG_PREFIX}-{max_n + 1:04d}"


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


# ---------------------------------------------------------------------
# Register (POST) + directory search (GET)
# ---------------------------------------------------------------------

@assets_bp.post("")
@role_required("AssetManager", "Admin")
def register_asset():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    category_id = data.get("category_id")

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not category_id or not AssetCategory.query.get(category_id):
        return jsonify({"error": "a valid category_id is required"}), 400

    department_id = data.get("department_id") or None
    if department_id and not Department.query.get(department_id):
        return jsonify({"error": "department not found"}), 400

    serial_number = (data.get("serial_number") or "").strip() or None
    if serial_number and Asset.query.filter_by(serial_number=serial_number).first():
        return jsonify({"error": "an asset with this serial number already exists"}), 409

    status = data.get("status", "Available")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    asset = Asset(
        asset_tag=_next_asset_tag(),
        name=name,
        category_id=category_id,
        department_id=department_id,
        location=(data.get("location") or "").strip() or None,
        status=status,
        is_bookable=bool(data.get("is_bookable", False)),
        serial_number=serial_number,
        qr_code=(data.get("qr_code") or "").strip() or None,
        description=data.get("description"),
        vendor=data.get("vendor"),
        purchase_date=_parse_date(data.get("purchase_date")),
        purchase_cost=data.get("purchase_cost"),
        warranty_expiry=_parse_date(data.get("warranty_expiry")),
        condition=data.get("condition"),
        registered_by=get_jwt_identity(),
    )
    db.session.add(asset)
    db.session.flush()  # get asset.id before writing history

    db.session.add(AssetStatusHistory(
        asset_id=asset.id,
        from_status=None,
        to_status=asset.status,
        changed_by=get_jwt_identity(),
        notes="Asset registered",
    ))
    db.session.commit()
    return jsonify(asset.to_dict()), 201


@assets_bp.get("")
@jwt_required()
def list_assets():
    """Search/filter for the directory table. Supports:
    q              — matches asset_tag, name, serial_number, or qr_code
    category_id, status, department_id — exact filters
    page, per_page — pagination (defaults 1 / 20, max 100)
    """
    q_text = (request.args.get("q") or "").strip()
    category_id = request.args.get("category_id")
    status = request.args.get("status")
    department_id = request.args.get("department_id")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)

    query = Asset.query

    if q_text:
        like = f"%{q_text}%"
        query = query.filter(or_(
            Asset.asset_tag.ilike(like),
            Asset.name.ilike(like),
            Asset.serial_number.ilike(like),
            Asset.qr_code.ilike(like),
        ))
    if category_id:
        query = query.filter_by(category_id=category_id)
    if status:
        query = query.filter_by(status=status)
    if department_id:
        query = query.filter_by(department_id=department_id)

    total = query.count()
    assets = (
        query.order_by(Asset.asset_tag.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify({
        "items": [a.to_dict(include_holder=True) for a in assets],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@assets_bp.get("/<asset_id>")
@jwt_required()
def get_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    return jsonify(asset.to_dict(include_holder=True))


@assets_bp.patch("/<asset_id>")
@role_required("AssetManager", "Admin")
def update_asset(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    data = request.get_json(force=True) or {}

    editable_direct_fields = [
        "name", "location", "is_bookable", "description", "vendor",
        "condition", "qr_code",
    ]
    for field in editable_direct_fields:
        if field in data:
            setattr(asset, field, data[field])

    if "category_id" in data:
        if not AssetCategory.query.get(data["category_id"]):
            return jsonify({"error": "category not found"}), 400
        asset.category_id = data["category_id"]

    if "department_id" in data:
        department_id = data["department_id"] or None
        if department_id and not Department.query.get(department_id):
            return jsonify({"error": "department not found"}), 400
        asset.department_id = department_id

    if "serial_number" in data:
        serial_number = (data["serial_number"] or "").strip() or None
        existing = Asset.query.filter_by(serial_number=serial_number).first() if serial_number else None
        if existing and existing.id != asset.id:
            return jsonify({"error": "an asset with this serial number already exists"}), 409
        asset.serial_number = serial_number

    if "purchase_date" in data:
        asset.purchase_date = _parse_date(data["purchase_date"])
    if "warranty_expiry" in data:
        asset.warranty_expiry = _parse_date(data["warranty_expiry"])
    if "purchase_cost" in data:
        asset.purchase_cost = data["purchase_cost"]

    if "status" in data and data["status"] != asset.status:
        new_status = data["status"]
        if new_status not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
        db.session.add(AssetStatusHistory(
            asset_id=asset.id,
            from_status=asset.status,
            to_status=new_status,
            changed_by=get_jwt_identity(),
            notes=data.get("status_note"),
        ))
        asset.status = new_status

    db.session.commit()
    return jsonify(asset.to_dict(include_holder=True))


# ---------------------------------------------------------------------
# History tab — status changes + allocation history, merged & sorted
# ---------------------------------------------------------------------

@assets_bp.get("/<asset_id>/history")
@jwt_required()
def asset_history(asset_id):
    Asset.query.get_or_404(asset_id)  # 404 if the asset doesn't exist

    status_events = AssetStatusHistory.query.filter_by(asset_id=asset_id).all()
    allocation_events = AssetAllocation.query.filter_by(asset_id=asset_id).all()
    document_events = AssetDocument.query.filter_by(asset_id=asset_id).all()

    timeline = (
        [e.to_dict() for e in status_events]
        + [e.to_dict() for e in allocation_events]
        + [e.to_dict() for e in document_events]
    )
    timeline.sort(key=lambda e: e["at"] or "", reverse=True)
    return jsonify(timeline)


# ---------------------------------------------------------------------
# Documents (invoice / warranty card / photo metadata)
# ---------------------------------------------------------------------

@assets_bp.post("/<asset_id>/documents")
@role_required("AssetManager", "Admin")
def add_asset_document(asset_id):
    Asset.query.get_or_404(asset_id)
    data = request.get_json(force=True) or {}
    file_name = (data.get("file_name") or "").strip()
    file_url = (data.get("file_url") or "").strip()

    if not file_name or not file_url:
        return jsonify({"error": "file_name and file_url are required"}), 400

    document = AssetDocument(
        asset_id=asset_id,
        file_name=file_name,
        file_url=file_url,
        doc_type=data.get("doc_type"),
        uploaded_by=get_jwt_identity(),
    )
    db.session.add(document)
    db.session.commit()
    return jsonify(document.to_dict()), 201
