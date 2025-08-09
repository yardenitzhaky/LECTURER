import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { BookOpen, FileText, Video, ArrowRight, User, LogIn } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export const WelcomePage: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [isBouncing, setIsBouncing] = useState(true);
  const { user, loading } = useAuth();

  useEffect(() => {
    setIsVisible(true);
    const bounceTimer = setTimeout(() => {
      setIsBouncing(false);
    }, 3000);

    return () => clearTimeout(bounceTimer);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-[calc(100vh-8rem)] py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-center min-h-[calc(100vh-12rem)]">
          <div className={`transform transition-all duration-1000 ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
            <div className="text-center space-y-6 max-w-4xl mx-auto">
              <div className="flex justify-center mb-8">
                <BookOpen 
                  className={`h-20 w-20 text-blue-600 ${isBouncing ? 'animate-bounce' : 'transform transition-transform hover:scale-110'}`} 
                />
              </div>
              
              <h1 className="text-5xl font-extrabold text-gray-900 mb-4">
                NoteLecture.AI
              </h1>
              
              <p className="text-2xl text-gray-600 mb-8">
                Transform Your Lectures Into Interactive, Searchable Content
              </p>

              <p className="text-lg text-gray-500 mb-8 max-w-2xl mx-auto">
                Upload video lectures and presentation slides to get AI-powered transcriptions, 
                synchronized content, and intelligent summaries. Perfect for students, educators, and professionals.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                <div className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
                  <Video className="h-8 w-8 text-blue-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Upload Lecture</h3>
                  <p className="text-gray-600">Share your recorded lecture or presentation video from files or YouTube URLs</p>
                </div>

                <div className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
                  <FileText className="h-8 w-8 text-blue-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Add Slides</h3>
                  <p className="text-gray-600">Include your presentation slides (PDF/PowerPoint) for enhanced analysis</p>
                </div>

                <div className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
                  <BookOpen className="h-8 w-8 text-blue-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Get AI Summary</h3>
                  <p className="text-gray-600">Receive organized, searchable content with synchronized transcription</p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link 
                  to="/register"
                  className="inline-flex items-center px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white text-lg font-semibold rounded-lg transition-colors group"
                >
                  <User className="mr-2 h-5 w-5" />
                  Get Started Free
                  <ArrowRight className="ml-2 group-hover:translate-x-1 transition-transform" />
                </Link>
                
                <Link 
                  to="/login"
                  className="inline-flex items-center px-8 py-4 bg-white hover:bg-gray-50 text-blue-600 text-lg font-semibold rounded-lg border-2 border-blue-600 transition-colors group"
                >
                  <LogIn className="mr-2 h-5 w-5" />
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};