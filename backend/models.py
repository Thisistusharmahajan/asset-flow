import uuid
from datetime import datetime, date

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def gen_uuid():
    return str(uuid.uuid4())


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(150), nullable=False, unique=True)
    parent_department_id = db.Column(db.String(36), db.ForeignKey("departments.id"), nullable=True)
    head_employee_id = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "status": self.status}


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    department_id = db.Column(db.String(36), db.ForeignKey("departments.id"), nullable=True)
    # Admin | AssetManager | DepartmentHead | Employee
    role = db.Column(db.String(20), nullable=False, default="Employee")
    status = db.Column(db.String(20), nullable=False, default="Active")
    promoted_by = db.Column(db.String(36), nullable=True)
    promoted_at = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship("Department", foreign_keys=[department_id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "department": self.department.name if self.department else None,
            "department_id": self.department_id,
        }


class AssetCategory(db.Model):
    __tablename__ = "asset_categories"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_tag = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey("asset_categories.id"), nullable=False)
    department_id = db.Column(db.String(36), db.ForeignKey("departments.id"), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    # Available | Allocated | Reserved | Under Maintenance | Lost | Retired | Disposed
    status = db.Column(db.String(30), nullable=False, default="Available")
    is_bookable = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship("AssetCategory")


class AssetAllocation(db.Model):
    __tablename__ = "asset_allocations"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    employee_id = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    department_id = db.Column(db.String(36), db.ForeignKey("departments.id"), nullable=True)
    allocated_date = db.Column(db.Date, default=date.today)
    expected_return_date = db.Column(db.Date, nullable=True)
    actual_return_date = db.Column(db.Date, nullable=True)
    # Active | Returned | Overdue
    status = db.Column(db.String(20), nullable=False, default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    asset = db.relationship("Asset")
    employee = db.relationship("Employee")
    department = db.relationship("Department")


class TransferRequest(db.Model):
    __tablename__ = "transfer_requests"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)

    asset_id = db.Column(
        db.String(36),
        db.ForeignKey("assets.id"),
        nullable=False,
    )

    current_allocation_id = db.Column(
        db.String(36),
        db.ForeignKey("asset_allocations.id"),
    )

    from_employee_id = db.Column(
        db.String(36),
        db.ForeignKey("employees.id"),
    )

    to_employee_id = db.Column(
        db.String(36),
        db.ForeignKey("employees.id"),
        nullable=False,
    )

    requested_by = db.Column(
        db.String(36),
        db.ForeignKey("employees.id"),
        nullable=False,
    )

    status = db.Column(db.String(20), nullable=False, default="Requested")

    approved_by = db.Column(
        db.String(36),
        db.ForeignKey("employees.id"),
    )

    rejection_reason = db.Column(db.Text)

    requested_at = db.Column(db.DateTime, default=datetime.utcnow)

    resolved_at = db.Column(db.DateTime)

    new_allocation_id = db.Column(
        db.String(36),
        db.ForeignKey("asset_allocations.id"),
    )


class ResourceBooking(db.Model):
    __tablename__ = "resource_bookings"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    booked_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Upcoming")

    asset = db.relationship("Asset")


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    raised_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    recipient_id = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }
