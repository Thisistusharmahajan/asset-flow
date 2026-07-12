"""Populate the dev database with demo data so Screens 1-4 render
meaningfully. Run with: python seed.py
"""
from datetime import datetime, timedelta, date

from werkzeug.security import generate_password_hash

from app import app
from extensions import db
from models import (
    Employee, Department, AssetCategory, Asset, AssetAllocation,
    AssetStatusHistory, ResourceBooking, TransferRequest,
    MaintenanceRequest, Notification,
)


def run():
    with app.app_context():
        db.drop_all()
        db.create_all()

        it = Department(name="IT")
        engineering = Department(name="Engineering")
        facilities = Department(name="Facilities")
        field_ops = Department(name="Field Ops")
        db.session.add_all([it, engineering, facilities, field_ops])
        db.session.flush()

        field_ops_east = Department(
            name="Field ops (east)", parent_department_id=field_ops.id, status="Inactive"
        )
        db.session.add(field_ops_east)
        db.session.flush()

        admin = Employee(
            name="Admin User", email="admin@assetflow.com",
            password_hash=generate_password_hash("password123"),
            role="Admin", department_id=it.id,
        )
        priya = Employee(
            name="Priya Shah", email="priya@assetflow.com",
            password_hash=generate_password_hash("password123"),
            role="Employee", department_id=engineering.id,
        )
        rohan = Employee(
            name="Rohan Mehta", email="rohan@assetflow.com",
            password_hash=generate_password_hash("password123"),
            role="AssetManager", department_id=facilities.id,
        )
        aditi = Employee(
            name="Aditi Rao", email="aditi@assetflow.com",
            password_hash=generate_password_hash("password123"),
            role="DepartmentHead", department_id=engineering.id,
        )
        sana = Employee(
            name="Sana Iqbal", email="sana@assetflow.com",
            password_hash=generate_password_hash("password123"),
            role="DepartmentHead", department_id=field_ops_east.id,
        )
        db.session.add_all([admin, priya, rohan, aditi, sana])
        db.session.flush()

        engineering.head_employee_id = aditi.id
        facilities.head_employee_id = rohan.id
        field_ops_east.head_employee_id = sana.id
        db.session.flush()

        electronics = AssetCategory(name="Electronics")
        furniture = AssetCategory(name="Furniture")
        db.session.add_all([electronics, furniture])
        db.session.flush()

        assets = []
        for i in range(1, 12):
            assets.append(Asset(
                asset_tag=f"AF-{i:04d}", name="Dell Laptop", category_id=electronics.id,
                department_id=it.id, location="Bengaluru", status="Available",
                serial_number=f"DL-SN-{1000 + i}", condition="Good",
            ))
        laptop_12 = Asset(
            asset_tag="AF-0012", name="Dell Laptop", category_id=electronics.id,
            department_id=engineering.id, location="Bengaluru", status="Allocated",
            serial_number="DL-SN-1012", condition="Good",
        )
        assets.append(laptop_12)

        for i in range(13, 62):
            assets.append(Asset(
                asset_tag=f"AF-{i:04d}", name="Office Chair", category_id=furniture.id,
                department_id=facilities.id, location="Warehouse", status="Allocated",
                condition="Fair",
            ))

        projector = Asset(
            asset_tag="AF-0062", name="Projector", category_id=electronics.id,
            department_id=it.id, location="HQ Floor 2", status="Under Maintenance",
            serial_number="PJ-SN-4471", condition="Fair",
        )
        chair_201 = Asset(
            asset_tag="AF-0201", name="Office Chair", category_id=furniture.id,
            department_id=facilities.id, location="Warehouse", status="Available",
            condition="Good",
        )
        room_b2 = Asset(
            asset_tag="AF-0300", name="Conference Room B2", category_id=furniture.id,
            department_id=facilities.id, location="HQ Floor 2", status="Available",
            is_bookable=True,
        )
        assets.extend([projector, chair_201, room_b2])

        db.session.add_all(assets)
        db.session.flush()

        for asset in assets:
            db.session.add(AssetStatusHistory(
                asset_id=asset.id, from_status=None, to_status=asset.status,
                changed_by=admin.id, notes="Asset registered (seed data)",
            ))

        # a few active allocations, including one overdue
        overdue_alloc = AssetAllocation(
            asset_id=assets[0].id, employee_id=priya.id,
            allocated_date=date.today() - timedelta(days=20),
            expected_return_date=date.today() - timedelta(days=3),
            status="Active",
        )
        upcoming_alloc = AssetAllocation(
            asset_id=laptop_12.id, employee_id=rohan.id,
            allocated_date=date.today() - timedelta(days=5),
            expected_return_date=date.today() + timedelta(days=4),
            status="Active",
        )
        db.session.add_all([overdue_alloc, upcoming_alloc])

        db.session.add(ResourceBooking(
            asset_id=room_b2.id, booked_by=priya.id,
            start_time=datetime.utcnow() + timedelta(hours=2),
            end_time=datetime.utcnow() + timedelta(hours=3),
            status="Upcoming",
        ))

        db.session.add(TransferRequest(
            asset_id=assets[2].id,
            from_employee_id=priya.id,
            to_employee_id=rohan.id,
            requested_by=priya.id,
            status="Requested",
        ))

        db.session.add(MaintenanceRequest(
            asset_id=projector.id, raised_by=priya.id,
            issue_description="Projector bulb not turning on",
            status="In Progress",
        ))

        db.session.add_all([
            Notification(
                recipient_id=admin.id, type="Asset Assigned",
                title="Laptop AF-0012 assigned",
                message="Laptop AF-0012 allocated to Rohan Mehta - Facilities dept",
            ),
            Notification(
                recipient_id=admin.id, type="Booking Confirmed",
                title="Room B2 booking confirmed",
                message="Room B2 - booking confirmed - 2:00 to 3:00 PM",
            ),
            Notification(
                recipient_id=admin.id, type="Maintenance Approved",
                title="Maintenance resolved",
                message="Projector AF-0062 - maintenance resolved",
            ),
        ])

        db.session.commit()
        print("Seeded database with demo data.")
        print("Login as: admin@assetflow.com / password123")


if __name__ == "__main__":
    run()
