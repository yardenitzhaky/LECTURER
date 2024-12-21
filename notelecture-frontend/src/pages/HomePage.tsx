import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, FileText, Video, ArrowRight } from 'lucide-react';

export const HomePage: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [isBouncing, setIsBouncing] = useState(true);

  useEffect(() => {
    setIsVisible(true);
    // Stop bouncing after 3 seconds
    const bounceTimer = setTimeout(() => {
      setIsBouncing(false);
    }, 3000);

    return () => clearTimeout(bounceTimer);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] py-16">
      <div className={`transform transition-all duration-1000 ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
        <div className="text-center space-y-6 max-w-4xl mx-auto px-4">
          <div className="flex justify-center mb-8">
            <BookOpen 
              className={`h-20 w-20 text-blue-600 ${isBouncing ? 'animate-bounce' : 'transform transition-transform hover:scale-110'}`} 
            />
          </div>
          
          <h1 className="text-5xl font-extrabold text-gray-900 mb-4">
            NoteLecture.AI
          </h1>
          
          <p className="text-2xl text-gray-600 mb-8">
            Your Lecture, Intelligently Noted
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
            <div className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
              <Video className="h-8 w-8 text-blue-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Upload Lecture</h3>
              <p className="text-gray-600">Share your recorded lecture or presentation video</p>
            </div>

            <div className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
              <FileText className="h-8 w-8 text-blue-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Add Slides</h3>
              <p className="text-gray-600">Include your presentation slides for enhanced analysis</p>
            </div>

            <div className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow">
              <BookOpen className="h-8 w-8 text-blue-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Get Summary</h3>
              <p className="text-gray-600">Receive organized, searchable content instantly</p>
            </div>
          </div>

          <Link 
            to="/upload"
            className="inline-flex items-center px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white text-lg font-semibold rounded-lg transition-colors group"
          >
            Start Processing
            <ArrowRight className="ml-2 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </div>
  );
};