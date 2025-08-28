import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { APIService } from '../services';
import { useAuth } from './AuthContext';
import type { SubscriptionStatus } from '../types';

interface SubscriptionContextType {
  subscriptionStatus: SubscriptionStatus | null;
  loading: boolean;
  error: string | null;
  refreshSubscriptionStatus: () => Promise<void>;
}

const SubscriptionContext = createContext<SubscriptionContextType | undefined>(undefined);

export const useSubscription = () => {
  const context = useContext(SubscriptionContext);
  if (context === undefined) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
};

interface SubscriptionProviderProps {
  children: ReactNode;
}

export const SubscriptionProvider: React.FC<SubscriptionProviderProps> = ({ children }) => {
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth();

  const loadSubscriptionStatus = useCallback(async () => {
    if (!user) {
      setSubscriptionStatus(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const status = await APIService.getSubscriptionStatus();
      setSubscriptionStatus(status);
    } catch (err: any) {
      const errorMsg = err.detail || err.message || 'Failed to load subscription status';
      setError(errorMsg);
      console.error('Failed to load subscription status:', err);
    } finally {
      setLoading(false);
    }
  }, [user]);

  const refreshSubscriptionStatus = useCallback(async () => {
    await loadSubscriptionStatus();
  }, [loadSubscriptionStatus]);

  // Load subscription status when user changes
  useEffect(() => {
    loadSubscriptionStatus();
  }, [loadSubscriptionStatus]);

  const value: SubscriptionContextType = {
    subscriptionStatus,
    loading,
    error,
    refreshSubscriptionStatus,
  };

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  );
};