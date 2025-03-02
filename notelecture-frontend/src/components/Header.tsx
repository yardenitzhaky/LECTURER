//src/components/Header.tsx
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, Upload, FileText } from 'lucide-react';

export const Header: React.FC = () => {
  const navigate = useNavigate();

  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault();
    setTimeout(() => navigate('/'), 0);
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
          
          <div className="flex items-center">
            <Link 
              to="/upload" 
              className="flex items-center px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-all duration-200"
            >
              <Upload className="h-4 w-4 mr-1" />
              Upload Lecture
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};