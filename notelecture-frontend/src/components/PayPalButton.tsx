import React, { useState } from 'react';
import { APIService } from '../services/api';
import type { SubscriptionPlan } from '../types';

interface PayPalButtonProps {
  plan: SubscriptionPlan;
  onSuccess: (details: any) => void;
  onError: (error: any) => void;
  onCancel: () => void;
  disabled?: boolean;
}

export const PayPalButton: React.FC<PayPalButtonProps> = ({
  plan,
  onSuccess,
  onError,
  onCancel,
  disabled = false
}) => {
  const [processing, setProcessing] = useState(false);

  const handlePayPalPayment = async () => {
    try {
      setProcessing(true);
      
      const returnUrl = `${window.location.origin}/payment-success`;
      const cancelUrl = `${window.location.origin}/payment-cancel`;
      
      const response = await APIService.createPaymentOrder(plan.id, {
        return_url: returnUrl,
        cancel_url: cancelUrl
      });

      if (response.success && response.approval_url) {
        // Redirect to PayPal for payment approval
        window.location.href = response.approval_url;
      } else {
        throw new Error('Failed to create payment order');
      }
    } catch (error: any) {
      console.error('Error creating payment order:', error);
      onError(error);
      setProcessing(false);
    }
  };

  if (processing) {
    return (
      <div className="flex justify-center items-center h-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-3">
      {/* PayPal Button */}
      <button
        onClick={handlePayPalPayment}
        disabled={disabled || processing}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a9.124 9.124 0 0 1-.499 1.607c-1.23 4.65-5.18 6.459-10.252 6.459H8.3l-1.681 10.66H2.47L5.577 1.346h7.46c2.229 0 3.956.404 4.901 1.449.86.95 1.147 2.056.896 3.468-.023.129-.045.261-.07.394l-.542 2.26z"/>
        </svg>
        Pay with PayPal
      </button>

      {/* Credit Card Button */}
      <button
        onClick={handlePayPalPayment}
        disabled={disabled || processing}
        className="w-full bg-gray-800 hover:bg-gray-900 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
        Pay with Credit Card
      </button>

      <div className="text-xs text-center text-gray-500">
        Both options use secure PayPal checkout. No PayPal account required for credit card payments.
      </div>

      {processing && (
        <div className="mt-2 text-center text-sm text-gray-600">
          Redirecting to secure checkout...
        </div>
      )}
    </div>
  );
};