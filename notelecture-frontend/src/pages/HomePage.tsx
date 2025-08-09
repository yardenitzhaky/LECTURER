//src/pages/HomePage.tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, FileText, Video, ArrowRight, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import axios from 'axios';

interface Lecture {
  id: number;
  title: string;
  status: string;
  video_path: string;
}

export const HomePage: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [isBouncing, setIsBouncing] = useState(true);
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setIsVisible(true);
    // Stop bouncing after 3 seconds
    const bounceTimer = setTimeout(() => {
      setIsBouncing(false);
    }, 3000);

    // Fetch user's lectures
    const fetchLectures = async () => {
      try {
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/lectures/`);
        setLectures(response.data.lectures);
      } catch (err: any) {
        setError('Failed to load lectures');
        console.error('Error fetching lectures:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLectures();

    return () => clearTimeout(bounceTimer);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'processing':
        return 'Processing';
      case 'transcribing':
        return 'Transcribing';
      case 'matching':
        return 'Matching slides';
      default:
        return 'Processing';
    }
  };

  return (
    <div className="min-h-[calc(100vh-8rem)] py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {lectures.length === 0 && !loading ? (
          // Welcome screen for new users
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
        ) : (
          // Dashboard for users with lectures
          <div>
            <div className="flex justify-between items-center mb-8">
              <h1 className="text-3xl font-bold text-gray-900">My Lectures</h1>
              <Link 
                to="/upload"
                className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
              >
                <Video className="h-4 w-4 mr-2" />
                New Lecture
              </Link>
            </div>

            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                <p className="text-red-600">{error}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {lectures.map((lecture) => (
                  <div key={lecture.id} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6">
                    <div className="flex items-start justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">{lecture.title}</h3>
                      <div className="flex items-center ml-2">
                        {getStatusIcon(lecture.status)}
                      </div>
                    </div>
                    
                    <div className="flex items-center mb-4">
                      <span className="text-sm text-gray-600">{getStatusText(lecture.status)}</span>
                    </div>

                    {lecture.status === 'completed' ? (
                      <Link 
                        to={`/lecture/${lecture.id}`}
                        className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View Lecture
                        <ArrowRight className="h-4 w-4 ml-1" />
                      </Link>
                    ) : (
                      <span className="text-gray-400">Processing...</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};