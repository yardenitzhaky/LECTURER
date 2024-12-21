import { Link, useNavigate } from 'react-router-dom';
import { BookOpen } from 'lucide-react';

export const Header: React.FC = () => {
  const navigate = useNavigate();

  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault();
    // Force a reload of the home page by navigating away and back
    navigate('/temp');
    setTimeout(() => navigate('/'), 0);
  };

  return (
    <nav className="w-full bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link to="/" onClick={handleLogoClick} className="flex items-center">
              <BookOpen className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-xl font-bold text-gray-900">NoteLecture.AI</span>
            </Link>
          </div>
          <div className="flex items-center">
            <Link 
              to="/upload" 
              className="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Upload
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};