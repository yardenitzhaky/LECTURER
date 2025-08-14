#!/usr/bin/env python3
"""
Initialize subscription plans in the database.
Run this after database creation to populate default subscription plans.
"""

from app.db.session import SessionLocal
from app.db.models import SubscriptionPlan

def init_subscription_plans():
    """Initialize default subscription plans"""
    
    session = SessionLocal()
    
    # Check if plans already exist
    existing_plans = session.query(SubscriptionPlan).count()
    if existing_plans > 0:
        print(f"Subscription plans already exist ({existing_plans} plans found)")
        session.close()
        return
    
    # Create default subscription plans
    plans = [
        {
            "name": "Weekly",
            "duration_days": 7,
            "price": 1.90,
            "lecture_limit": 10
        },
        {
            "name": "Monthly", 
            "duration_days": 30,
            "price": 5.90,
            "lecture_limit": 50
        },
        {
            "name": "6 Months",
            "duration_days": 180,
            "price": 14.90,
            "lecture_limit": 300
        },
        {
            "name": "12 Months",
            "duration_days": 365, 
            "price": 24.90,
            "lecture_limit": 750
        }
    ]
    
    for plan_data in plans:
        plan = SubscriptionPlan(**plan_data)
        session.add(plan)
    
    session.commit()
    print(f"Created {len(plans)} subscription plans")
    session.close()

if __name__ == "__main__":
    init_subscription_plans()