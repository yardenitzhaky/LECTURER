# app/api/subscriptions.py
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.utils.common import get_db, get_async_db
from app.db.models import SubscriptionPlan, UserSubscription, User, Lecture, Payment
from app.auth import current_active_user
from app.services.paypal import paypal_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for payment requests
class PaymentRequest(BaseModel):
    return_url: str
    cancel_url: str

class PaymentExecuteRequest(BaseModel):
    payment_id: str
    payer_id: str


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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get current user's subscription status and usage."""
    try:
        # Get current active subscription
        now = datetime.utcnow()
        result = await db.execute(
            select(UserSubscription).options(selectinload(UserSubscription.plan)).filter(
                UserSubscription.user_id == str(current_user.id),
                UserSubscription.is_active == True,
                UserSubscription.start_date <= now,
                UserSubscription.end_date >= now
            )
        )
        current_sub = result.scalar_one_or_none()

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


@router.post("/subscriptions/create-payment/{plan_id}")
async def create_payment_order(
    plan_id: int,
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Create a PayPal payment order for a subscription plan."""
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
        
        # Create PayPal payment order
        payment_result = paypal_service.create_payment_order(
            user=current_user,
            plan=plan,
            return_url=payment_request.return_url,
            cancel_url=payment_request.cancel_url
        )
        
        if payment_result["success"]:
            return {
                "success": True,
                "payment_id": payment_result["payment_id"],
                "approval_url": payment_result["approval_url"],
                "plan": {
                    "name": plan.name,
                    "price": float(plan.price),
                    "duration_days": plan.duration_days,
                    "lecture_limit": plan.lecture_limit
                }
            }
        else:
            logger.error(f"PayPal payment creation failed: {payment_result['error']}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create payment order: {payment_result['error']}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment for user {current_user.id}, plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating payment: {str(e)}")


@router.post("/payments/execute")
async def execute_payment(
    payment_execute: PaymentExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Execute/capture PayPal payment and activate subscription."""
    try:
        # Execute PayPal payment
        execution_result = paypal_service.execute_payment(
            payment_id=payment_execute.payment_id,
            payer_id=payment_execute.payer_id
        )
        
        if not execution_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Payment execution failed: {execution_result['error']}"
            )
        
        payment_record = execution_result["payment_record"]
        
        # Get the plan from the payment record's amount
        # We need to find which plan matches the payment amount
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.price == payment_record.amount,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found for payment amount")
        
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
        
        # Link payment to subscription
        payment_record.subscription_id = new_subscription.id
        
        db.commit()
        
        logger.info(f"User {current_user.id} payment executed and subscribed to plan {plan.name}")
        
        return {
            "success": True,
            "message": "Payment successful and subscription activated",
            "subscription": {
                "plan_name": plan.name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "lectures_limit": plan.lecture_limit
            },
            "payment": {
                "payment_id": payment_record.paypal_order_id,
                "amount": float(payment_record.amount),
                "status": payment_record.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error executing payment for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing payment: {str(e)}")


@router.get("/subscriptions/usage")
async def get_usage_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(current_active_user)
) -> Dict[str, Any]:
    """Get detailed usage statistics for the current user."""
    try:
        # Get current active subscription
        now = datetime.utcnow()
        result = await db.execute(
            select(UserSubscription).options(selectinload(UserSubscription.plan)).filter(
                UserSubscription.user_id == str(current_user.id),
                UserSubscription.is_active == True,
                UserSubscription.start_date <= now,
                UserSubscription.end_date >= now
            )
        )
        current_sub = result.scalar_one_or_none()

        # Get total lectures created by user
        lecture_count_result = await db.execute(
            select(func.count(Lecture.id)).filter(Lecture.user_id == str(current_user.id))
        )
        total_lectures = lecture_count_result.scalar()

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


@router.post("/payments/webhook")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Handle PayPal webhook notifications."""
    try:
        # Get request body and headers
        body = await request.body()
        headers = dict(request.headers)
        
        # Verify webhook signature (simplified)
        if not paypal_service.verify_webhook(headers, body.decode()):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook data
        import json
        webhook_data = json.loads(body.decode())
        
        event_type = webhook_data.get('event_type')
        resource = webhook_data.get('resource', {})
        
        # Process the webhook
        success = paypal_service.process_webhook(event_type, resource)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Webhook processing failed")
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook body")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing error")