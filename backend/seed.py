"""Populate the dev database with demo data so Screens 1 & 2 render
meaningfully. Run with: python seed.py
"""
from datetime import datetime, timedelta, date

from werkzeug.security import generate_password_hash

from app import app
from models import (
    db, Employee, Department, AssetCategory, Asset, AssetAllocation,
    ResourceBooking, TransferRequest, MaintenanceRequest, Notification
)


def run():
    with app.app_context():

        it = Department(name="IT")
        engineering = Department(name="Engineering")
        facilities = Department(name="Facilities")
        db.session.add_all([it, engineering, facilities])
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
        db.session.add_all([admin, priya, rohan])
        db.session.flush()

        electronics = AssetCategory(name="Electronics")
        furniture = AssetCategory(name="Furniture")
        db.session.add_all([electronics, furniture])
        db.session.flush()

        assets = []
        for i in range(1, 129):
            assets.append(Asset(
                asset_tag=f"AF-{i:04d}", name="Dell Laptop", category_id=electronics.id,
                department_id=it.id, location="Bengaluru", status="Available",
            ))
        for i in range(129, 205):
            assets.append(Asset(
                asset_tag=f"AF-{i:04d}", name="Office Chair", category_id=furniture.id,
                department_id=facilities.id, location="Warehouse", status="Allocated",
            ))
        room_b2 = Asset(
            asset_tag="AF-0300", name="Conference Room B2", category_id=furniture.id,
            department_id=facilities.id, location="HQ Floor 2", status="Available",
            is_bookable=True,
        )
        projector = Asset(
            asset_tag="AF-0301", name="Projector", category_id=electronics.id,
            department_id=it.id, location="HQ Floor 2", status="Under Maintenance",
        )
        assets.extend([room_b2, projector])
        db.session.add_all(assets)
        db.session.flush()

        # a few active allocations, including one overdue
        overdue_alloc = AssetAllocation(
            asset_id=assets[0].id, employee_id=priya.id,
            allocated_date=date.today() - timedelta(days=20),
            expected_return_date=date.today() - timedelta(days=3),
            status="Active",
        )
        upcoming_alloc = AssetAllocation(
            asset_id=assets[1].id, employee_id=rohan.id,
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
                title="Laptop AF-0114 assigned",
                message="Laptop AF-0114 allocated to Priya Shah - IT dept",
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
