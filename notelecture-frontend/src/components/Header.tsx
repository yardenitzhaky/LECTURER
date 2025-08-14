//src/components/Header.tsx
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, Upload, User, LogOut, Crown, CreditCard } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { APIService } from '../services';
import type { SubscriptionStatus } from '../types';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    if (user) {
      loadSubscriptionStatus();
    }
  }, [user]);

  const loadSubscriptionStatus = async () => {
    try {
      const status = await APIService.getSubscriptionStatus();
      setSubscriptionStatus(status);
    } catch (err) {
      console.error('Failed to load subscription status:', err);
    }
  };

  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault();
    const destination = user ? '/dashboard' : '/';
    setTimeout(() => navigate(destination), 0);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="w-full bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link 
              to="/" 
              onClick={handleLogoClick} 
              className="flex items-center group transition-all duration-300"
            >
              <BookOpen className="h-8 w-8 text-blue-600 group-hover:text-blue-800 group-hover:scale-110 transition-all duration-300" />
              <span className="ml-2 text-xl font-bold text-gray-900 group-hover:text-blue-800 transition-colors duration-300">
                NoteLecture.AI
              </span>
            </Link>
          </div>
          
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link 
                  to="/upload" 
                  className="flex items-center px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-all duration-200"
                >
                  <Upload className="h-4 w-4 mr-1" />
                  Upload Lecture
                </Link>
                
                {/* Subscription Status */}
                {subscriptionStatus && (
                  <Link 
                    to="/subscription" 
                    className="flex items-center px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-all duration-200"
                  >
                    {subscriptionStatus.has_subscription ? (
                      <>
                        <Crown className="h-4 w-4 mr-1 text-yellow-500" />
                        <span className="text-yellow-600 font-medium">{subscriptionStatus.plan_name}</span>
                      </>
                    ) : (
                      <>
                        <CreditCard className="h-4 w-4 mr-1" />
                        <span>Free ({subscriptionStatus.free_lectures_remaining}/3)</span>
                      </>
                    )}
                  </Link>
                )}
                
                <div className="flex items-center space-x-2">
                  <div className="flex items-center text-sm text-gray-700">
                    <User className="h-4 w-4 mr-1" />
                    {user.first_name || user.email}
                  </div>
                  
                  <button
                    onClick={handleLogout}
                    className="flex items-center px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-red-50 hover:text-red-700 transition-all duration-200"
                  >
                    <LogOut className="h-4 w-4 mr-1" />
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center space-x-2">
                <Link 
                  to="/login" 
                  className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-all duration-200"
                >
                  Sign In
                </Link>
                <Link 
                  to="/register" 
                  className="px-3 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-all duration-200"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};