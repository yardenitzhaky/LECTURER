import React from 'react';
import { Navigate } from 'react-router-dom';
import { RegisterForm } from '../components/RegisterForm';
import { useAuth } from '../contexts/AuthContext';

export const RegisterPage: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <RegisterForm />
    </div>
  );
};