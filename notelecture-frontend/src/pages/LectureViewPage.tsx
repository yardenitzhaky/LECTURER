// src/pages/LectureViewPage.tsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { APIService } from '../api';
import { Lecture, TranscriptionSegment } from '..';

const LectureViewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [slideTranscriptions, setSlideTranscriptions] = useState<TranscriptionSegment[]>([]);

  useEffect(() => {
    const fetchLecture = async () => {
      if (!id) return;
      try {
        setIsLoading(true);
        const lectureData = await APIService.getLecture(id);
        setLecture(lectureData);
        
        // Group transcriptions for the current slide
        const currentSlideTranscriptions = lectureData.transcription.filter(
          segment => segment.slideIndex === currentSlideIndex
        );
        setSlideTranscriptions(currentSlideTranscriptions);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load lecture');
      } finally {
        setIsLoading(false);
      }
    };

    fetchLecture();
  }, [id, currentSlideIndex]);

  const handlePreviousSlide = () => {
    setCurrentSlideIndex(prev => Math.max(0, prev - 1));
  };

  const handleNextSlide = () => {
    if (lecture) {
      setCurrentSlideIndex(prev => Math.min(lecture.slides.length - 1, prev + 1));
    }
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !lecture) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-600">{error || 'Lecture not found'}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto w-full space-y-4">
        {/* Title and Navigation */}
        <div className="flex items-center justify-between bg-white p-4 rounded-lg shadow-sm">
          <button
            onClick={handlePreviousSlide}
            disabled={currentSlideIndex === 0}
            className="p-2 rounded-full hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
          
          <div className="text-center">
            <h1 className="text-xl font-semibold">{lecture.title}</h1>
            <span className="text-sm text-gray-500">
              Slide {currentSlideIndex + 1} of {lecture.slides.length}
            </span>
          </div>
          
          <button
            onClick={handleNextSlide}
            disabled={currentSlideIndex === lecture.slides.length - 1}
            className="p-2 rounded-full hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Slide Display */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="p-4">
              {lecture.slides[currentSlideIndex] ? (
                <img
                  src={lecture.slides[currentSlideIndex].imageUrl}
                  alt={`Slide ${currentSlideIndex + 1}`}
                  className="w-full h-auto rounded-lg"
                />
              ) : (
                <div className="w-full h-64 bg-gray-100 flex items-center justify-center rounded-lg">
                  <p className="text-gray-500">No slide available</p>
                </div>
              )}
            </div>
          </div>

          {/* Transcription Panel - Modified for RTL */}
          <div className="bg-white rounded-lg shadow-sm">
            <div className="p-4">
              <h2 className="text-xl font-semibold mb-4 text-right">
                Transcription for Slide {currentSlideIndex + 1}
              </h2>
              <div dir="rtl" className="space-y-4 max-h-96 overflow-y-auto">
                {slideTranscriptions.length > 0 ? (
                  slideTranscriptions.map((segment) => (
                    <div 
                      key={segment.id}
                      className="flex items-start space-x-4 p-2 hover:bg-gray-50 rounded flex-row-reverse space-x-reverse"
                    >
                      <span className="text-sm text-gray-500 whitespace-nowrap">
                        {formatTime(segment.startTime)}
                      </span>
                      <p className="text-gray-700 flex-1 text-right">
                        {segment.text}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-500 py-4">
                    No transcriptions available for this slide
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LectureViewPage;