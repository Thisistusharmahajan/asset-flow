from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from extensions import db
from models import Department, AssetCategory, Employee
from decorators import role_required

organization_bp = Blueprint("organization", __name__, url_prefix="/api")

VALID_ROLES = {"Admin", "AssetManager", "DepartmentHead", "Employee"}


# ---------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------
# Reads are open to any signed-in user because Screens 4 & 5 need the
# department list for filters/picklists. Writes are Admin-only.

@organization_bp.get("/departments")
@jwt_required()
def list_departments():
    status = request.args.get("status")
    q = Department.query
    if status:
        q = q.filter_by(status=status)
    departments = q.order_by(Department.name.asc()).all()
    return jsonify([d.to_dict() for d in departments])


@organization_bp.post("/departments")
@role_required("Admin")
def create_department():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if Department.query.filter_by(name=name).first():
        return jsonify({"error": "a department with this name already exists"}), 409

    parent_department_id = data.get("parent_department_id") or None
    if parent_department_id and not Department.query.get(parent_department_id):
        return jsonify({"error": "parent department not found"}), 400

    head_employee_id = data.get("head_employee_id") or None
    if head_employee_id and not Employee.query.get(head_employee_id):
        return jsonify({"error": "head employee not found"}), 400

    department = Department(
        name=name,
        parent_department_id=parent_department_id,
        head_employee_id=head_employee_id,
        status=data.get("status", "Active"),
    )
    db.session.add(department)
    db.session.commit()
    return jsonify(department.to_dict()), 201


@organization_bp.patch("/departments/<department_id>")
@role_required("Admin")
def update_department(department_id):
    department = Department.query.get_or_404(department_id)
    data = request.get_json(force=True) or {}

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        existing = Department.query.filter_by(name=name).first()
        if existing and existing.id != department.id:
            return jsonify({"error": "a department with this name already exists"}), 409
        department.name = name

    if "parent_department_id" in data:
        parent_id = data["parent_department_id"] or None
        if parent_id == department.id:
            return jsonify({"error": "a department cannot be its own parent"}), 400
        if parent_id and not Department.query.get(parent_id):
            return jsonify({"error": "parent department not found"}), 400
        department.parent_department_id = parent_id

    if "head_employee_id" in data:
        head_id = data["head_employee_id"] or None
        if head_id and not Employee.query.get(head_id):
            return jsonify({"error": "head employee not found"}), 400
        department.head_employee_id = head_id

    if "status" in data:
        if data["status"] not in ("Active", "Inactive"):
            return jsonify({"error": "status must be Active or Inactive"}), 400
        department.status = data["status"]

    db.session.commit()
    return jsonify(department.to_dict())


# ---------------------------------------------------------------------
# Asset categories
# ---------------------------------------------------------------------

@organization_bp.get("/asset-categories")
@jwt_required()
def list_asset_categories():
    categories = AssetCategory.query.order_by(AssetCategory.name.asc()).all()
    return jsonify([c.to_dict() for c in categories])


@organization_bp.post("/asset-categories")
@role_required("Admin")
def create_asset_category():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if AssetCategory.query.filter_by(name=name).first():
        return jsonify({"error": "a category with this name already exists"}), 409

    category = AssetCategory(name=name, description=data.get("description"))
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


@organization_bp.patch("/asset-categories/<category_id>")
@role_required("Admin")
def update_asset_category(category_id):
    category = AssetCategory.query.get_or_404(category_id)
    data = request.get_json(force=True) or {}

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        existing = AssetCategory.query.filter_by(name=name).first()
        if existing and existing.id != category.id:
            return jsonify({"error": "a category with this name already exists"}), 409
        category.name = name

    if "description" in data:
        category.description = data["description"]

    db.session.commit()
    return jsonify(category.to_dict())


# ---------------------------------------------------------------------
# Employee directory (Screen 3 "Employee" tab) — Admin only.
# This is also the ONLY place role promotion happens.
# ---------------------------------------------------------------------

@organization_bp.get("/employees")
@role_required("Admin")
def list_employees():
    role = request.args.get("role")
    department_id = request.args.get("department_id")
    status = request.args.get("status")

    q = Employee.query
    if role:
        q = q.filter_by(role=role)
    if department_id:
        q = q.filter_by(department_id=department_id)
    if status:
        q = q.filter_by(status=status)

    employees = q.order_by(Employee.name.asc()).all()
    return jsonify([e.to_dict() for e in employees])


@organization_bp.patch("/employees/<employee_id>/role")
@role_required("Admin")
def update_employee_role(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    data = request.get_json(force=True) or {}
    new_role = data.get("role")

    if new_role not in VALID_ROLES:
        return jsonify({"error": f"role must be one of {sorted(VALID_ROLES)}"}), 400

    acting_admin_id = get_jwt_identity()
    if employee.id == acting_admin_id and new_role != "Admin":
        return jsonify({"error": "you can't demote your own account"}), 400

    employee.role = new_role
    employee.promoted_by = acting_admin_id
    employee.promoted_at = datetime.utcnow()
    db.session.commit()
    return jsonify(employee.to_dict())


@organization_bp.patch("/employees/<employee_id>")
@role_required("Admin")
def update_employee(employee_id):
    """General admin edits: reassign department, activate/deactivate."""
    employee = Employee.query.get_or_404(employee_id)
    data = request.get_json(force=True) or {}

    if "department_id" in data:
        department_id = data["department_id"] or None
        if department_id and not Department.query.get(department_id):
            return jsonify({"error": "department not found"}), 400
        employee.department_id = department_id

    if "status" in data:
        if data["status"] not in ("Active", "Inactive"):
            return jsonify({"error": "status must be Active or Inactive"}), 400
        if employee.id == get_jwt_identity() and data["status"] == "Inactive":
            return jsonify({"error": "you can't deactivate your own account"}), 400
        employee.status = data["status"]

    db.session.commit()
    return jsonify(employee.to_dict())
