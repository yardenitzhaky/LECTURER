import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircleIcon } from '@heroicons/react/24/outline';
import { APIService } from '../services/api';

export const PaymentSuccessPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [subscriptionDetails, setSubscriptionDetails] = useState<any>(null);

  useEffect(() => {
    const processPayment = async () => {
      try {
        const paymentId = searchParams.get('paymentId');
        const payerId = searchParams.get('PayerID');

        if (!paymentId || !payerId) {
          setError('Missing payment information');
          return;
        }

        // Execute the payment
        const result = await APIService.executePayment({
          payment_id: paymentId,
          payer_id: payerId
        });

        if (result.success) {
          setSubscriptionDetails(result.subscription);
        } else {
          setError(result.message || 'Payment processing failed');
        }
      } catch (err: any) {
        setError(err.detail || err.message || 'An error occurred processing your payment');
      } finally {
        setLoading(false);
      }
    };

    processPayment();
  }, [searchParams]);

  const handleContinue = () => {
    navigate('/dashboard');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Processing your payment...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="max-w-md mx-auto text-center">
          <div className="rounded-full bg-red-100 p-3 mx-auto mb-4 w-16 h-16 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Error</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/subscription')}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md mx-auto text-center bg-white rounded-lg shadow-lg p-8">
        <CheckCircleIcon className="w-16 h-16 text-green-600 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h1>
        
        {subscriptionDetails && (
          <div className="mb-6 text-left bg-gray-50 rounded-lg p-4">
            <h2 className="font-semibold text-gray-900 mb-2">Subscription Details:</h2>
            <div className="space-y-1 text-sm text-gray-600">
              <div>Plan: <span className="font-medium">{subscriptionDetails.plan_name}</span></div>
              <div>Lectures: <span className="font-medium">{subscriptionDetails.lectures_limit}</span></div>
              <div>Valid until: <span className="font-medium">{new Date(subscriptionDetails.end_date).toLocaleDateString()}</span></div>
            </div>
          </div>
        )}
        
        <p className="text-gray-600 mb-6">
          Your subscription has been activated successfully. You can now upload and process lectures.
        </p>
        
        <button
          onClick={handleContinue}
          className="w-full bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
        >
          Continue to Dashboard
        </button>
      </div>
    </div>
  );
};