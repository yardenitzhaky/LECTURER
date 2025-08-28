# app/services/paypal.py
import logging
from typing import Dict, Any, Optional
import paypalrestsdk
from datetime import datetime

from app.core.config import settings
from app.db.models import Payment, UserSubscription, SubscriptionPlan, User
from app.utils.common import get_db_sync

logger = logging.getLogger(__name__)

class PayPalService:
    def __init__(self):
        if settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET:
            paypalrestsdk.configure({
                "mode": settings.PAYPAL_MODE,  # sandbox or live
                "client_id": settings.PAYPAL_CLIENT_ID,
                "client_secret": settings.PAYPAL_CLIENT_SECRET
            })
            self.configured = True
        else:
            logger.warning("PayPal credentials not configured. PayPal functionality will be disabled.")
            self.configured = False
    
    def create_payment_order(
        self, 
        user: User, 
        plan: SubscriptionPlan, 
        return_url: str, 
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a PayPal payment order for a subscription plan."""
        if not self.configured:
            return {
                "success": False,
                "error": "PayPal not configured. Please contact administrator."
            }
        
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": return_url,
                    "cancel_url": cancel_url
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": f"NoteLecture.AI - {plan.name} Subscription",
                            "sku": f"plan_{plan.id}",
                            "price": str(plan.price),
                            "currency": "USD",
                            "quantity": 1,
                            "description": f"{plan.lecture_limit} lectures for {plan.duration_days} days"
                        }]
                    },
                    "amount": {
                        "total": str(plan.price),
                        "currency": "USD"
                    },
                    "description": f"NoteLecture.AI {plan.name} Subscription"
                }]
            })

            if payment.create():
                logger.info(f"PayPal payment created successfully: {payment.id}")
                
                # Store payment record in database
                db = next(get_db_sync())
                try:
                    payment_record = Payment(
                        user_id=str(user.id),
                        paypal_order_id=payment.id,
                        amount=plan.price,
                        status="pending"
                    )
                    db.add(payment_record)
                    db.commit()
                    
                    # Get approval URL
                    approval_url = None
                    for link in payment.links:
                        if link.rel == "approval_url":
                            approval_url = link.href
                            break
                    
                    return {
                        "success": True,
                        "payment_id": payment.id,
                        "approval_url": approval_url,
                        "payment_record_id": payment_record.id
                    }
                finally:
                    db.close()
            else:
                logger.error(f"PayPal payment creation failed: {payment.error}")
                return {
                    "success": False,
                    "error": payment.error
                }
        except Exception as e:
            logger.error(f"Error creating PayPal payment: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_payment(
        self, 
        payment_id: str, 
        payer_id: str
    ) -> Dict[str, Any]:
        """Execute/capture a PayPal payment."""
        if not self.configured:
            return {
                "success": False,
                "error": "PayPal not configured. Please contact administrator."
            }
        
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            
            if payment.execute({"payer_id": payer_id}):
                logger.info(f"PayPal payment executed successfully: {payment_id}")
                
                # Update payment record in database
                db = next(get_db_sync())
                try:
                    payment_record = db.query(Payment).filter(
                        Payment.paypal_order_id == payment_id
                    ).first()
                    
                    if payment_record:
                        payment_record.status = "completed"
                        payment_record.completed_at = datetime.utcnow()
                        payment_record.paypal_payment_id = payment.id
                        
                        # Get transaction details
                        if payment.transactions and len(payment.transactions) > 0:
                            transaction = payment.transactions[0]
                            if hasattr(transaction, 'related_resources'):
                                for resource in transaction.related_resources:
                                    if hasattr(resource, 'sale'):
                                        payment_record.paypal_payment_id = resource.sale.id
                                        break
                        
                        db.commit()
                        
                        return {
                            "success": True,
                            "payment_record": payment_record,
                            "payment_details": payment.to_dict()
                        }
                    else:
                        logger.error(f"Payment record not found for PayPal ID: {payment_id}")
                        return {
                            "success": False,
                            "error": "Payment record not found"
                        }
                finally:
                    db.close()
            else:
                logger.error(f"PayPal payment execution failed: {payment.error}")
                return {
                    "success": False,
                    "error": payment.error
                }
        except Exception as e:
            logger.error(f"Error executing PayPal payment: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_payment_status(self, payment_id: str) -> Optional[str]:
        """Get the status of a PayPal payment."""
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            return payment.state if payment else None
        except Exception as e:
            logger.error(f"Error getting PayPal payment status: {e}", exc_info=True)
            return None
    
    def verify_webhook(self, headers: Dict[str, Any], body: str) -> bool:
        """Verify PayPal webhook signature (simplified version)."""
        # In production, you should implement proper webhook verification
        # using PayPal's webhook verification API
        # For now, we'll do basic validation
        try:
            return 'PAYPAL-TRANSMISSION-ID' in headers
        except Exception as e:
            logger.error(f"Error verifying webhook: {e}", exc_info=True)
            return False
    
    def process_webhook(self, event_type: str, resource: Dict[str, Any]) -> bool:
        """Process PayPal webhook events."""
        try:
            if event_type == "PAYMENT.SALE.COMPLETED":
                return self._handle_payment_completed(resource)
            elif event_type == "PAYMENT.SALE.DENIED":
                return self._handle_payment_denied(resource)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return True
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return False
    
    def _handle_payment_completed(self, resource: Dict[str, Any]) -> bool:
        """Handle payment completion webhook."""
        try:
            payment_id = resource.get('parent_payment')
            if not payment_id:
                return False
            
            db = next(get_db_sync())
            try:
                payment_record = db.query(Payment).filter(
                    Payment.paypal_order_id == payment_id
                ).first()
                
                if payment_record and payment_record.status != "completed":
                    payment_record.status = "completed"
                    payment_record.completed_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"Payment {payment_id} marked as completed via webhook")
                
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error handling payment completion webhook: {e}", exc_info=True)
            return False
    
    def _handle_payment_denied(self, resource: Dict[str, Any]) -> bool:
        """Handle payment denial webhook."""
        try:
            payment_id = resource.get('parent_payment')
            if not payment_id:
                return False
            
            db = next(get_db_sync())
            try:
                payment_record = db.query(Payment).filter(
                    Payment.paypal_order_id == payment_id
                ).first()
                
                if payment_record:
                    payment_record.status = "failed"
                    db.commit()
                    logger.info(f"Payment {payment_id} marked as failed via webhook")
                
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error handling payment denial webhook: {e}", exc_info=True)
            return False

# Global instance
paypal_service = PayPalService()