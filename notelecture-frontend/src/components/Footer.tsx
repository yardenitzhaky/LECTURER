// src/components/Footer.tsx
import { 
    Linkedin, 
    Github, 
    Mail, 
    Globe, 
    Copyright 
  } from 'lucide-react';
  
  export const Footer: React.FC = () => {
    const currentYear = new Date().getFullYear();
  
    const socialLinks = [
      {
        icon: <Globe className="h-5 w-5" />,
        url: "https://yardenitzhaky.github.io/Portfolio/",
        label: "Portfolio"
      },
      {
        icon: <Linkedin className="h-5 w-5" />,
        url: "https://www.linkedin.com/in/yardenitzhaky",
        label: "LinkedIn"
      },
      {
        icon: <Github className="h-5 w-5" />,
        url: "https://github.com/yardenitzhaky",
        label: "GitHub"
      },
      {
        icon: <Mail className="h-5 w-5" />,
        url: "mailto:yardene015@gmail.com",
        label: "Email"
      }
    ];
  
    return (
      <footer className="w-full bg-white border-t border-gray-200 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center space-y-4">
            {/* Social Links */}
            <div className="flex space-x-6">
              {socialLinks.map((link, index) => (
                <a
                  key={index}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={link.label}
                  title={link.label}
                  className="text-gray-500 hover:text-blue-600 transition-colors"
                >
                  {link.icon}
                </a>
              ))}
            </div>
            
            {/* Copyright */}
            <div className="flex items-center text-gray-500 text-sm">
              <Copyright className="h-4 w-4 mr-1" />
              <span>{currentYear}</span>
              <span className="mx-2">|</span>
              <span>Created by Yarden Itzhaky</span>
            </div>
          </div>
        </div>
      </footer>
    );
  };