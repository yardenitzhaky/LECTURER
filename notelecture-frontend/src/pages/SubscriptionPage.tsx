import React, { useState, useEffect } from 'react';
import { APIService } from '../services/api';
import { PayPalButton } from '../components/PayPalButton';
import type { SubscriptionPlan, SubscriptionStatus } from '../types';

interface PlanCardProps {
  plan: SubscriptionPlan;
  currentPlanId?: number;
  onPaymentSuccess: (details: any) => void;
  onPaymentError: (error: any) => void;
  onPaymentCancel: () => void;
  isLoading: boolean;
}

const PlanCard: React.FC<PlanCardProps> = ({ 
  plan, 
  currentPlanId, 
  onPaymentSuccess, 
  onPaymentError, 
  onPaymentCancel, 
  isLoading 
}) => {
  const isCurrentPlan = currentPlanId === plan.id;
  
  return (
    <div className={`relative rounded-lg border-2 p-6 ${
      isCurrentPlan 
        ? 'border-blue-500 bg-blue-50' 
        : 'border-gray-200 hover:border-gray-300'
    }`}>
      {isCurrentPlan && (
        <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2">
          <span className="inline-flex items-center rounded-full bg-blue-500 px-2 py-1 text-xs font-medium text-white">
            Current Plan
          </span>
        </div>
      )}
      
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
        <div className="mt-2">
          <span className="text-3xl font-bold text-gray-900">${plan.price}</span>
          <span className="text-gray-500">/{plan.duration_days} days</span>
        </div>
        <p className="mt-2 text-sm text-gray-600">{plan.description}</p>
        
        <div className="mt-4">
          <div className="text-sm font-medium text-gray-900">Features:</div>
          <ul className="mt-2 space-y-1 text-sm text-gray-600">
            <li>• Up to {plan.lecture_limit} lectures</li>
            <li>• {plan.duration_days} days access</li>
            <li>• AI-powered transcription</li>
            <li>• Slide summarization</li>
            <li>• Video synchronization</li>
          </ul>
        </div>
        
        <div className="mt-6">
          {isCurrentPlan ? (
            <div className="w-full rounded-md px-4 py-2 text-sm font-medium bg-gray-100 text-gray-400 cursor-not-allowed text-center">
              Current Plan
            </div>
          ) : (
            <PayPalButton
              plan={plan}
              onSuccess={onPaymentSuccess}
              onError={onPaymentError}
              onCancel={onPaymentCancel}
              disabled={isLoading}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export const SubscriptionPage: React.FC = () => {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [plansResponse, statusResponse] = await Promise.all([
        APIService.getSubscriptionPlans(),
        APIService.getSubscriptionStatus()
      ]);
      setPlans(plansResponse.plans);
      setStatus(statusResponse);
    } catch (err: any) {
      setError(err.detail || 'Failed to load subscription data');
    } finally {
      setLoading(false);
    }
  };

  const handlePaymentSuccess = async (details: any) => {
    try {
      setProcessing(true);
      setError(null);
      
      // Payment has already been processed by PayPalButton component
      // Just reload data to reflect the new subscription
      await loadData();
      
      setSuccess(`Payment successful! Welcome to your new ${details.subscription?.plan_name} subscription.`);
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(null), 5000);
    } catch (err: any) {
      setError(err.detail || 'Failed to process successful payment');
    } finally {
      setProcessing(false);
    }
  };

  const handlePaymentError = (error: any) => {
    console.error('Payment error:', error);
    setError(error.detail || error.message || 'Payment failed. Please try again.');
    setProcessing(false);
  };

  const handlePaymentCancel = () => {
    console.log('Payment cancelled by user');
    // Could show a message or just ignore
    setProcessing(false);
  };

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription?')) {
      return;
    }
    
    try {
      setError(null);
      await APIService.cancelSubscription();
      await loadData();
    } catch (err: any) {
      setError(err.detail || 'Failed to cancel subscription');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Choose Your Plan</h1>
        <p className="mt-2 text-lg text-gray-600">
          Transform your lectures into interactive, searchable content
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-md bg-red-50 border border-red-200 p-4">
          <div className="text-sm text-red-600">{error}</div>
        </div>
      )}

      {success && (
        <div className="mb-6 rounded-md bg-green-50 border border-green-200 p-4">
          <div className="text-sm text-green-600">{success}</div>
        </div>
      )}

      {/* Current Subscription Status */}
      {status && (
        <div className="mb-8 rounded-lg border border-gray-200 p-6 bg-gray-50">
          <h2 className="text-lg font-semibold mb-4">Current Status</h2>
          {status.has_subscription ? (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>Plan: {status.plan_name}</span>
                <span className="text-green-600 font-medium">Active</span>
              </div>
              <div className="flex justify-between">
                <span>Lectures Used:</span>
                <span>{status.lectures_used} / {status.lectures_limit}</span>
              </div>
              <div className="flex justify-between">
                <span>Days Remaining:</span>
                <span>{status.days_remaining} days</span>
              </div>
              <button
                onClick={handleCancelSubscription}
                className="mt-4 text-red-600 hover:text-red-700 text-sm font-medium"
              >
                Cancel Subscription
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>Plan: Free Trial</span>
                <span className="text-blue-600 font-medium">Active</span>
              </div>
              <div className="flex justify-between">
                <span>Lectures Used:</span>
                <span>{status.free_lectures_used} / {status.free_lectures_limit}</span>
              </div>
              {(status.free_lectures_remaining || 0) <= 0 && (
                <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
                  <p className="text-sm text-yellow-800">
                    You've used all your free lectures. Subscribe to a plan to continue.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Subscription Plans */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            currentPlanId={status?.plan_id}
            onPaymentSuccess={handlePaymentSuccess}
            onPaymentError={handlePaymentError}
            onPaymentCancel={handlePaymentCancel}
            isLoading={processing}
          />
        ))}
      </div>

      {/* Free Plan Info */}
      <div className="mt-8 text-center">
        <div className="rounded-lg border border-gray-200 p-6 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Free Trial</h3>
          <p className="text-gray-600">
            Get started with 3 free lectures to explore our platform.
            No credit card required.
          </p>
        </div>
      </div>
    </div>
  );
};