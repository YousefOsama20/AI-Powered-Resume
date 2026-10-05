"""
Seed script — populates JobType and JobFunction lookup tables.
Run once after the DB tables are created.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from stores.db.database import SessionLocal, engine
from models.sql_models import Base, JobType, JobFunction

# Create all tables
Base.metadata.create_all(bind=engine)

# Seed data
JOB_TYPES = ["Full Time", "Part Time", "Remote", "Contract", "Freelance", "Internship"]
JOB_FUNCTIONS = [
    "Software Engineering", "AI/ML Engineering", "Data Engineering",
    "Data Science", "DevOps/Cloud", "Mobile Development",
    "Cybersecurity", "Product Management", "UI/UX Design",
    "QA/Testing", "Backend Development", "Frontend Development",
    "Full Stack Development", "System Administration"
]

db = SessionLocal()

try:
    # Seed Job Types
    for name in JOB_TYPES:
        existing = db.query(JobType).filter(JobType.name == name).first()
        if not existing:
            db.add(JobType(name=name))
            print(f"  + JobType: {name}")

    # Seed Job Functions
    for name in JOB_FUNCTIONS:
        existing = db.query(JobFunction).filter(JobFunction.name == name).first()
        if not existing:
            db.add(JobFunction(name=name))
            print(f"  + JobFunction: {name}")

    db.commit()
    print("\n✓ Seed complete!")

    # Verify
    print(f"\nJobTypes in DB: {[jt.name for jt in db.query(JobType).all()]}")
    print(f"JobFunctions in DB: {[jf.name for jf in db.query(JobFunction).all()]}")

except Exception as e:
    db.rollback()
    print(f"✗ Seed failed: {e}")
finally:
    db.close()
