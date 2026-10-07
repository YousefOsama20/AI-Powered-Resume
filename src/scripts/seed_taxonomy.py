import asyncio
import os
import sys

# Add src to path so we can import from models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stores.db.database import SessionLocal
from models.sql_models import JobType, JobFunction

JOB_TYPES = [
    "Full Time",
    "Part Time",
    "Remote",
    "Contract",
    "Freelance",
    "Internship"
]

JOB_FUNCTIONS = [
    "Software Engineering",
    "AI/ML Engineering",
    "Data Engineering",
    "Data Science",
    "DevOps/Cloud",
    "Mobile Development",
    "Cybersecurity",
    "Product Management",
    "UI/UX Design",
    "QA/Testing",
    "Backend Development",
    "Frontend Development",
    "Full Stack Development",
    "System Administration"
]

def seed():
    db = SessionLocal()
    try:
        # Seed Job Types
        print("Seeding Job Types...")
        for jt in JOB_TYPES:
            existing = db.query(JobType).filter_by(name=jt).first()
            if not existing:
                db.add(JobType(name=jt))
                
        # Seed Job Functions
        print("Seeding Job Functions...")
        for jf in JOB_FUNCTIONS:
            existing = db.query(JobFunction).filter_by(name=jf).first()
            if not existing:
                db.add(JobFunction(name=jf))
                
        db.commit()
        print("Seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
