import uuid
from datetime import datetime, date

from extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(150), nullable=False, unique=True)
    parent_department_id = db.Column(db.String(36), db.ForeignKey("departments.id"), nullable=True)
    head_employee_id = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Active")  # Active | Inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship("Department", remote_side=[id], foreign_keys=[parent_department_id])
    head = db.relationship("Employee", foreign_keys=[head_employee_id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "head_employee_id": self.head_employee_id,
            "head_name": self.head.name if self.head else None,
            "parent_department_id": self.parent_department_id,
            "parent_name": self.parent.name if self.parent else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


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
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AssetCategory(db.Model):
    __tablename__ = "asset_categories"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        asset_count = Asset.query.filter_by(category_id=self.id).count()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "asset_count": asset_count,
        }


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

    serial_number = db.Column(db.String(120), nullable=True, unique=True)
    qr_code = db.Column(db.String(120), nullable=True, unique=True)
    description = db.Column(db.Text, nullable=True)
    vendor = db.Column(db.String(150), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    purchase_cost = db.Column(db.Numeric(12, 2), nullable=True)
    warranty_expiry = db.Column(db.Date, nullable=True)
    condition = db.Column(db.String(30), nullable=True)  # New | Good | Fair | Poor

    registered_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship("AssetCategory")
    department = db.relationship("Department")

    def current_holder(self):
        """Active allocation holder, if any — used by the directory list."""
        alloc = (
            AssetAllocation.query
            .filter_by(asset_id=self.id, status="Active")
            .order_by(AssetAllocation.allocated_date.desc())
            .first()
        )
        if not alloc:
            return None
        if alloc.employee:
            return alloc.employee.name
        if alloc.department:
            return alloc.department.name
        return None

    def to_dict(self, include_holder=False):
        data = {
            "id": self.id,
            "asset_tag": self.asset_tag,
            "name": self.name,
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "location": self.location,
            "status": self.status,
            "is_bookable": self.is_bookable,
            "serial_number": self.serial_number,
            "qr_code": self.qr_code,
            "description": self.description,
            "vendor": self.vendor,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "purchase_cost": float(self.purchase_cost) if self.purchase_cost is not None else None,
            "warranty_expiry": self.warranty_expiry.isoformat() if self.warranty_expiry else None,
            "condition": self.condition,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_holder:
            data["current_holder"] = self.current_holder()
        return data


class AssetStatusHistory(db.Model):
    """One row per status transition — feeds the Screen 4 asset history tab."""
    __tablename__ = "asset_status_history"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    from_status = db.Column(db.String(30), nullable=True)
    to_status = db.Column(db.String(30), nullable=False)
    changed_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    changed_by_employee = db.relationship("Employee")

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": "status_change",
            "from_status": self.from_status,
            "to_status": self.to_status,
            "changed_by": self.changed_by_employee.name if self.changed_by_employee else "System",
            "notes": self.notes,
            "at": self.changed_at.isoformat() if self.changed_at else None,
        }


class AssetDocument(db.Model):
    """Metadata for files attached to an asset (invoice, warranty card, photo...).
    Actual file bytes are expected to live in whatever storage the frontend
    uploads to (S3 / local disk) — this table just tracks the reference."""
    __tablename__ = "asset_documents"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    doc_type = db.Column(db.String(50), nullable=True)  # Invoice | Warranty | Photo | Other
    uploaded_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by_employee = db.relationship("Employee")

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": "document",
            "file_name": self.file_name,
            "file_url": self.file_url,
            "doc_type": self.doc_type,
            "uploaded_by": self.uploaded_by_employee.name if self.uploaded_by_employee else None,
            "at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


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

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": "allocation",
            "holder": self.employee.name if self.employee else (self.department.name if self.department else None),
            "allocated_date": self.allocated_date.isoformat() if self.allocated_date else None,
            "expected_return_date": self.expected_return_date.isoformat() if self.expected_return_date else None,
            "actual_return_date": self.actual_return_date.isoformat() if self.actual_return_date else None,
            "status": self.status,
            "at": self.created_at.isoformat() if self.created_at else None,
        }


class TransferRequest(db.Model):
    __tablename__ = "transfer_requests"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    current_allocation_id = db.Column(db.String(36), db.ForeignKey("asset_allocations.id"))
    from_employee_id = db.Column(db.String(36), db.ForeignKey("employees.id"))
    to_employee_id = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=False)
    requested_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Requested")
    approved_by = db.Column(db.String(36), db.ForeignKey("employees.id"))
    rejection_reason = db.Column(db.Text)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    new_allocation_id = db.Column(db.String(36), db.ForeignKey("asset_allocations.id"))

    asset = db.relationship("Asset", foreign_keys=[asset_id])
    from_employee = db.relationship("Employee", foreign_keys=[from_employee_id])
    to_employee = db.relationship("Employee", foreign_keys=[to_employee_id])


class ResourceBooking(db.Model):
    __tablename__ = "resource_bookings"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    booked_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Upcoming")

    asset = db.relationship("Asset")
    booker = db.relationship("Employee", foreign_keys=[booked_by])


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    raised_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    # Pending | Approved | Technician Assigned | In Progress | Resolved
    status = db.Column(db.String(30), nullable=False, default="Pending")
    technician_name = db.Column(db.String(150), nullable=True)
    notes = db.Column(db.Text, nullable=True)  # e.g. "parts ordered", "resolved 7 Jul"
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset = db.relationship("Asset")
    raised_by_employee = db.relationship("Employee", foreign_keys=[raised_by])

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_tag": self.asset.asset_tag if self.asset else None,
            "issue_description": self.issue_description,
            "status": self.status,
            "technician_name": self.technician_name,
            "notes": self.notes,
            "raised_by_name": self.raised_by_employee.name if self.raised_by_employee else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditCycle(db.Model):
    """One audit run against a department over a date window."""
    __tablename__ = "audit_cycles"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title = db.Column(db.String(200), nullable=False)  # e.g. "Q3 audit: Engineering dept"
    department_id = db.Column(db.String(36), db.ForeignKey("departments.id"), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    auditor_names = db.Column(db.String(300), nullable=True)  # comma-separated for simplicity
    status = db.Column(db.String(20), nullable=False, default="Open")  # Open | Closed
    created_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    department = db.relationship("Department")

    def to_dict(self, include_items=False):
        data = {
            "id": self.id,
            "title": self.title,
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "auditor_names": self.auditor_names,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "flagged_count": AuditItem.query.filter(
                AuditItem.audit_cycle_id == self.id,
                AuditItem.verification.in_(["Missing", "Damaged"]),
            ).count(),
        }
        if include_items:
            items = AuditItem.query.filter_by(audit_cycle_id=self.id).all()
            data["items"] = [i.to_dict() for i in items]
        return data


class AuditItem(db.Model):
    """One asset's expected-vs-actual check within an audit cycle."""
    __tablename__ = "audit_items"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    audit_cycle_id = db.Column(db.String(36), db.ForeignKey("audit_cycles.id"), nullable=False)
    asset_id = db.Column(db.String(36), db.ForeignKey("assets.id"), nullable=False)
    expected_location = db.Column(db.String(200), nullable=True)
    # Unverified | Verified | Missing | Damaged
    verification = db.Column(db.String(20), nullable=False, default="Unverified")
    notes = db.Column(db.Text, nullable=True)
    verified_by = db.Column(db.String(36), db.ForeignKey("employees.id"), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    asset = db.relationship("Asset")

    def to_dict(self):
        return {
            "id": self.id,
            "audit_cycle_id": self.audit_cycle_id,
            "asset_id": self.asset_id,
            "asset_tag": self.asset.asset_tag if self.asset else None,
            "asset_name": self.asset.name if self.asset else None,
            "expected_location": self.expected_location,
            "verification": self.verification,
            "notes": self.notes,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


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
