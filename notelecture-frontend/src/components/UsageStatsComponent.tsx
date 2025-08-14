import React, { useState, useEffect } from 'react';
import { APIService } from '../services/api';
import type { UsageStats } from '../types';

interface UsageStatsComponentProps {
  className?: string;
}

export const UsageStatsComponent: React.FC<UsageStatsComponentProps> = ({ className = '' }) => {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await APIService.getUsageStats();
      setStats(data);
    } catch (err: any) {
      setError(err.detail || 'Failed to load usage stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={`animate-pulse ${className}`}>
        <div className="h-24 bg-gray-200 rounded-lg"></div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className={`rounded-lg border border-red-200 bg-red-50 p-4 ${className}`}>
        <p className="text-sm text-red-600">Failed to load usage statistics</p>
      </div>
    );
  }

  const getProgressColor = (used: number, limit: number) => {
    const percentage = (used / limit) * 100;
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getProgressWidth = (used: number, limit: number) => {
    return Math.min((used / limit) * 100, 100);
  };

  return (
    <div className={`rounded-lg border border-gray-200 bg-white p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-900">Usage Statistics</h3>
        {stats.subscription_type === 'premium' && stats.plan_name && (
          <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
            {stats.plan_name}
          </span>
        )}
      </div>

      {stats.subscription_type === 'premium' ? (
        <div className="space-y-3">
          {/* Current period usage */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">This Period</span>
              <span className="text-gray-900">
                {stats.lectures_used_this_period} / {stats.lectures_limit}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${getProgressColor(
                  stats.lectures_used_this_period || 0,
                  stats.lectures_limit || 1
                )}`}
                style={{
                  width: `${getProgressWidth(
                    stats.lectures_used_this_period || 0,
                    stats.lectures_limit || 1
                  )}%`
                }}
              ></div>
            </div>
          </div>

          {/* Days remaining */}
          {stats.days_remaining !== undefined && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Days Remaining</span>
              <span className="text-gray-900">{stats.days_remaining}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Free trial usage */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">Free Lectures</span>
              <span className="text-gray-900">
                {stats.free_lectures_used} / 3
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${getProgressColor(
                  stats.free_lectures_used || 0,
                  3
                )}`}
                style={{
                  width: `${getProgressWidth(stats.free_lectures_used || 0, 3)}%`
                }}
              ></div>
            </div>
          </div>

          {stats.needs_upgrade && (
            <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-xs text-yellow-800">
                You've used all free lectures. 
                <a href="/subscription" className="font-medium text-yellow-900 hover:underline ml-1">
                  Upgrade now
                </a>
              </p>
            </div>
          )}
        </div>
      )}

      {/* Total lectures created */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Total Lectures</span>
          <span className="text-gray-900 font-medium">{stats.total_lectures_ever}</span>
        </div>
      </div>
    </div>
  );
};