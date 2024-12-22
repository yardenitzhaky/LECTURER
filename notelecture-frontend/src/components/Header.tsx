//src/components/Header.tsx
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen } from 'lucide-react';

export const Header: React.FC = () => {
  const navigate = useNavigate();

  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault();
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
        </div>
      </div>
    </nav>
  );
};