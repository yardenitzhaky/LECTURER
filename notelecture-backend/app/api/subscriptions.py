# app/api/subscriptions.py
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.utils.common import get_db
from app.db.models import SubscriptionPlan, UserSubscription, User, Lecture
from app.auth import current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/subscriptions/plans")
async def get_subscription_plans(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get all available subscription plans."""
    try:
        plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
        
        return {
            "plans": [{
                "id": plan.id,
                "name": plan.name,
                "duration_days": plan.duration_days,
                "price": float(plan.price),
                "lecture_limit": plan.lecture_limit,
                "description": f"{plan.lecture_limit} lectures for {plan.duration_days} days"
            } for plan in plans]
        }
    except Exception as e:
        logger.error(f"Error retrieving subscription plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving plans: {str(e)}")


@router.get("/subscriptions/status")
async def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get current user's subscription status and usage."""
    try:
        # Get current active subscription
        now = datetime.utcnow()
        current_sub = db.query(UserSubscription).filter(
            UserSubscription.user_id == str(current_user.id),
            UserSubscription.is_active == True,
            UserSubscription.start_date <= now,
            UserSubscription.end_date >= now
        ).first()
        
        if current_sub:
            return {
                "has_subscription": True,
                "plan_name": current_sub.plan.name,
                "plan_id": current_sub.plan.id,
                "start_date": current_sub.start_date.isoformat(),
                "end_date": current_sub.end_date.isoformat(),
                "lectures_used": current_sub.lectures_used,
                "lectures_limit": current_sub.plan.lecture_limit,
                "lectures_remaining": current_sub.plan.lecture_limit - current_sub.lectures_used,
                "days_remaining": current_sub.days_remaining(),
                "is_expired": current_sub.is_expired()
            }
        else:
            return {
                "has_subscription": False,
                "free_lectures_used": current_user.free_lectures_used,
                "free_lectures_remaining": max(0, 3 - current_user.free_lectures_used),
                "free_lectures_limit": 3
            }
    except Exception as e:
        logger.error(f"Error retrieving subscription status for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving subscription status: {str(e)}")


@router.post("/subscriptions/subscribe/{plan_id}")
async def subscribe_to_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Subscribe user to a plan (without payment processing for now)."""
    try:
        # Get the plan
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == plan_id,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        
        # Check if user already has an active subscription
        now = datetime.utcnow()
        current_sub = db.query(UserSubscription).filter(
            UserSubscription.user_id == str(current_user.id),
            UserSubscription.is_active == True,
            UserSubscription.start_date <= now,
            UserSubscription.end_date >= now
        ).first()
        
        if current_sub:
            raise HTTPException(
                status_code=400, 
                detail="You already have an active subscription"
            )
        
        # Deactivate any existing subscriptions
        existing_subs = db.query(UserSubscription).filter(
            UserSubscription.user_id == str(current_user.id)
        ).all()
        for sub in existing_subs:
            sub.is_active = False
        
        # Create new subscription
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        new_subscription = UserSubscription(
            user_id=str(current_user.id),
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            lectures_used=0
        )
        
        db.add(new_subscription)
        db.commit()
        
        logger.info(f"User {current_user.id} subscribed to plan {plan.name}")
        
        return {
            "message": "Successfully subscribed to plan",
            "subscription": {
                "plan_name": plan.name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "lectures_limit": plan.lecture_limit
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error subscribing user {current_user.id} to plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing subscription: {str(e)}")


@router.get("/subscriptions/usage")
async def get_usage_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get detailed usage statistics for the current user."""
    try:
        # Get current active subscription
        now = datetime.utcnow()
        current_sub = db.query(UserSubscription).filter(
            UserSubscription.user_id == str(current_user.id),
            UserSubscription.is_active == True,
            UserSubscription.start_date <= now,
            UserSubscription.end_date >= now
        ).first()
        
        # Get total lectures created by user
        total_lectures = db.query(Lecture).filter(Lecture.user_id == str(current_user.id)).count()
        
        if current_sub:
            return {
                "subscription_type": "premium",
                "plan_name": current_sub.plan.name,
                "lectures_used_this_period": current_sub.lectures_used,
                "lectures_limit": current_sub.plan.lecture_limit,
                "lectures_remaining": current_sub.plan.lecture_limit - current_sub.lectures_used,
                "total_lectures_ever": total_lectures,
                "days_remaining": current_sub.days_remaining(),
                "subscription_end": current_sub.end_date.isoformat()
            }
        else:
            return {
                "subscription_type": "free",
                "free_lectures_used": current_user.free_lectures_used,
                "free_lectures_remaining": max(0, 3 - current_user.free_lectures_used),
                "total_lectures_ever": total_lectures,
                "needs_upgrade": current_user.free_lectures_used >= 3
            }
    except Exception as e:
        logger.error(f"Error retrieving usage stats for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving usage statistics: {str(e)}")


@router.delete("/subscriptions/cancel")
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Cancel the current user's subscription."""
    try:
        # Get current active subscription
        now = datetime.utcnow()
        current_sub = db.query(UserSubscription).filter(
            UserSubscription.user_id == str(current_user.id),
            UserSubscription.is_active == True,
            UserSubscription.start_date <= now,
            UserSubscription.end_date >= now
        ).first()
        
        if not current_sub:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Deactivate the subscription
        current_sub.is_active = False
        db.commit()
        
        logger.info(f"User {current_user.id} cancelled subscription to {current_sub.plan.name}")
        
        return {
            "message": "Subscription cancelled successfully",
            "cancelled_plan": current_sub.plan.name,
            "access_until": current_sub.end_date.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelling subscription for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error cancelling subscription: {str(e)}")