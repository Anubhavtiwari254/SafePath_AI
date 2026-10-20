import os
from datetime import datetime, timezone, timedelta
from config import Config
from models import db, User, TrustedContact, HazardReport, ReportConfirmation, EmergencyShare, ModerationLog


def seed_database(app):
    """Populate database with demo accounts, trusted contacts, and realistic fictional hazards."""
    with app.app_context():
        db.create_all()

        # 1. Create Admin Account
        admin = User.query.filter_by(email="admin@safepath.ai").first()
        if not admin:
            admin = User(
                name="SafePath Administrator",
                email="admin@safepath.ai",
                is_admin=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            print("Created Admin user: admin@safepath.ai / admin123")

        # 2. Create Regular Demo User
        demo_user = User.query.filter_by(email="demo@safepath.ai").first()
        if not demo_user:
            demo_user = User(
                name="Alex Mercer",
                email="demo@safepath.ai",
                is_admin=False
            )
            demo_user.set_password("safepath123")
            db.session.add(demo_user)
            db.session.commit()
            print("Created Demo user: demo@safepath.ai / safepath123")

            # 3. Add Trusted Contacts for Demo User
            contacts = [
                TrustedContact(
                    user_id=demo_user.id,
                    contact_name="Sarah Mercer (Sister)",
                    contact_method="phone",
                    contact_value="+1 (555) 234-5678"
                ),
                TrustedContact(
                    user_id=demo_user.id,
                    contact_name="David Chen (Roommate)",
                    contact_method="phone",
                    contact_value="+1 (555) 876-5432"
                ),
                TrustedContact(
                    user_id=demo_user.id,
                    contact_name="Campus Security Escort",
                    contact_method="phone",
                    contact_value="+1 (555) 100-2000"
                )
            ]
            db.session.add_all(contacts)
            db.session.commit()
            print("Added sample trusted contacts for Alex Mercer.")

        # 4. Check if hazard reports already exist
        if HazardReport.query.count() > 0:
            print("Database already contains hazard reports. Skipping report seeding.")
            return

        now = datetime.now(timezone.utc)

        # Fictional demonstration community hazards across Delhi Central Corridor
        # (Connaught Place <-> Central Station <-> India Gate)
        fictional_reports = [
            # Near Central Railway Station & Paharganj side
            {
                "lat": 28.6415,
                "lon": 77.2185,
                "cat": "broken_streetlights",
                "desc": "Three consecutive streetlights flickering and out along station approach road. Very dark after 8 PM.",
                "sev": "medium",
                "days_ago": 2,
                "status": "verified",
                "confirmations": 4
            },
            {
                "lat": 28.6442,
                "lon": 77.2162,
                "cat": "isolated_areas",
                "desc": "Narrow unmonitored passage behind market stalls with no CCTV or security presence.",
                "sev": "high",
                "days_ago": 4,
                "status": "verified",
                "confirmations": 6
            },
            {
                "lat": 28.6390,
                "lon": 77.2140,
                "cat": "road_damage",
                "desc": "Large trench dug across pedestrian sidewalk with exposed cables and no safety barrier.",
                "sev": "medium",
                "days_ago": 1,
                "status": "pending",
                "confirmations": 2
            },
            # Connaught Place Inner/Outer Circle
            {
                "lat": 28.6328,
                "lon": 77.2180,
                "cat": "blocked_road",
                "desc": "Pedestrian colonnade blocked by heavy maintenance scaffolding. Walkers forced into vehicular lane.",
                "sev": "low",
                "days_ago": 5,
                "status": "verified",
                "confirmations": 3
            },
            {
                "lat": 28.6295,
                "lon": 77.2145,
                "cat": "suspicious_activity",
                "desc": "Unattended individuals loitering near the ATM kiosk and confronting pedestrians for cash.",
                "sev": "high",
                "days_ago": 3,
                "status": "verified",
                "confirmations": 5
            },
            {
                "lat": 28.6260,
                "lon": 77.2205,
                "cat": "broken_streetlights",
                "desc": "Dark stretch on Janpath connecting lane, walkway lamp broken.",
                "sev": "low",
                "days_ago": 12,
                "status": "verified",
                "confirmations": 2
            },
            # India Gate & Rajpath approach
            {
                "lat": 28.6185,
                "lon": 77.2260,
                "cat": "harassment",
                "desc": "Group passing aggressive verbal remarks towards lone runners in the unlit park periphery.",
                "sev": "high",
                "days_ago": 2,
                "status": "verified",
                "confirmations": 7
            },
            {
                "lat": 28.6150,
                "lon": 77.2230,
                "cat": "road_damage",
                "desc": "Open drain slab collapsed on cycle lane near roundabout.",
                "sev": "medium",
                "days_ago": 6,
                "status": "verified",
                "confirmations": 3
            },
            {
                "lat": 28.6110,
                "lon": 77.2320,
                "cat": "isolated_areas",
                "desc": "Thick foliage and unlit footpath behind bus shelter, poor pedestrian sightlines.",
                "sev": "medium",
                "days_ago": 9,
                "status": "pending",
                "confirmations": 1
            },
            # Delhi University / North Campus corridor
            {
                "lat": 28.6910,
                "lon": 77.2085,
                "cat": "broken_streetlights",
                "desc": "Campus perimeter wall lights non-functional along Ridge Road stretch.",
                "sev": "high",
                "days_ago": 1,
                "status": "verified",
                "confirmations": 8
            },
            {
                "lat": 28.6875,
                "lon": 77.2135,
                "cat": "suspicious_activity",
                "desc": "Speeding unmarked vehicles circling quiet hostel lane late night.",
                "sev": "medium",
                "days_ago": 3,
                "status": "verified",
                "confirmations": 4
            },
            # Manhattan / New York corridor (Times Square to Central Park)
            {
                "lat": 40.7620,
                "lon": -73.9820,
                "cat": "broken_streetlights",
                "desc": "Dim street lighting on side avenue connecting 8th and 9th Ave.",
                "sev": "medium",
                "days_ago": 2,
                "status": "verified",
                "confirmations": 5
            },
            {
                "lat": 40.7690,
                "lon": -73.9810,
                "cat": "road_damage",
                "desc": "Deep pothole and broken curb near pedestrian crosswalk.",
                "sev": "low",
                "days_ago": 7,
                "status": "verified",
                "confirmations": 2
            },
            {
                "lat": 40.7740,
                "lon": -73.9740,
                "cat": "isolated_areas",
                "desc": "Park pathway lighting obscured by overhanging branches after dusk.",
                "sev": "medium",
                "days_ago": 4,
                "status": "verified",
                "confirmations": 4
            },
            {
                "lat": 40.7550,
                "lon": -73.9870,
                "cat": "harassment",
                "desc": "Aggressive costumed solicitors cornering tourists and demanding tips.",
                "sev": "high",
                "days_ago": 1,
                "status": "verified",
                "confirmations": 9
            }
        ]

        for item in fictional_reports:
            inc_time = now - timedelta(days=item["days_ago"], hours=item.get("hours", 3))
            report = HazardReport(
                user_id=demo_user.id if demo_user else None,
                latitude=item["lat"],
                longitude=item["lon"],
                category=item["cat"],
                description=item["desc"],
                severity=item["sev"],
                incident_datetime=inc_time,
                created_at=inc_time,
                verification_status=item["status"],
                moderation_notes="Demo demonstration seed data (fictional)."
            )
            db.session.add(report)
            db.session.flush()

            # Add confirmations
            confs = item.get("confirmations", 0)
            for c_idx in range(confs):
                conf = ReportConfirmation(
                    report_id=report.id,
                    client_identifier=f"seed_client_{report.id}_{c_idx}"
                )
                db.session.add(conf)

        db.session.commit()
        print(f"Successfully seeded {len(fictional_reports)} realistic demonstration hazard reports.")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    seed_database(app)
