import React from 'react';
import { useNavigate } from 'react-router-dom';
import { XCircleIcon } from '@heroicons/react/24/outline';

export const PaymentCancelPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md mx-auto text-center bg-white rounded-lg shadow-lg p-8">
        <XCircleIcon className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
        
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Payment Cancelled</h1>
        
        <p className="text-gray-600 mb-6">
          Your payment was cancelled. No charges have been made to your account.
        </p>
        
        <div className="space-y-3">
          <button
            onClick={() => navigate('/subscription')}
            className="w-full bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
          >
            Try Again
          </button>
          
          <button
            onClick={() => navigate('/dashboard')}
            className="w-full bg-gray-300 text-gray-700 px-6 py-2 rounded-md hover:bg-gray-400"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};