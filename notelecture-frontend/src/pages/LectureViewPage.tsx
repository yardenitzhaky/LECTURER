// src/pages/LectureViewPage.tsx
import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useParams } from 'react-router-dom';

export const LectureViewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [currentSlide, setCurrentSlide] = useState<number>(0);
  const [isFullscreenVideo, setIsFullscreenVideo] = useState<boolean>(false);

  return (
    <div className="h-screen flex flex-col">
      {/* Top Section: Video and Slides */}
      <div className={`flex flex-1 ${isFullscreenVideo ? 'flex-col' : 'flex-row'}`}>
        {/* Video Player */}
        <div className={`${isFullscreenVideo ? 'h-3/4' : 'w-1/2'} bg-black p-4`}>
          <div className="w-full h-full flex items-center justify-center">
            <div className="aspect-video bg-gray-800 w-full">
              {/* Video player component will go here */}
              <div className="w-full h-full flex items-center justify-center text-white">
                Video Player - Lecture ID: {id}
              </div>
            </div>
          </div>
        </div>

        {/* Slides */}
        <div className={`${isFullscreenVideo ? 'h-1/4' : 'w-1/2'} bg-gray-100 p-4`}>
          <div className="h-full flex flex-col">
            <div className="flex-1 bg-white rounded-lg shadow-sm p-4">
              {/* Slide content will go here */}
              <div className="w-full h-full flex items-center justify-center text-gray-500">
                Slide Content
              </div>
            </div>
            
            {/* Slide Navigation */}
            <div className="mt-4 flex items-center justify-between">
              <button
                onClick={() => setCurrentSlide(prev => Math.max(0, prev - 1))}
                className="p-2 rounded-full hover:bg-gray-200"
              >
                <ChevronLeft className="h-6 w-6" />
              </button>
              <span className="text-sm text-gray-600">
                Slide {currentSlide + 1} of X
              </span>
              <button
                onClick={() => setCurrentSlide(prev => prev + 1)}
                className="p-2 rounded-full hover:bg-gray-200"
              >
                <ChevronRight className="h-6 w-6" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: Transcription */}
      <div className="h-1/4 bg-white border-t">
        <div className="h-full p-4">
          <div className="bg-gray-50 h-full rounded-lg p-4 overflow-y-auto">
            {/* Transcription content will go here */}
            <div className="space-y-4">
              <div className="flex items-start space-x-4">
                <span className="text-sm text-gray-500 whitespace-nowrap">
                  00:00:00
                </span>
                <p className="text-gray-700">
                  Transcription text will appear here synchronized with the video playback...
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};