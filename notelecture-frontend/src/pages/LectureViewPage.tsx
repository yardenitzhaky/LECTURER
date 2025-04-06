// src/pages/LectureViewPage.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom'; // Added useNavigate
import { ChevronLeft, ChevronRight, AlertTriangle, Loader2, Home } from 'lucide-react'; // Added icons
import { APIService } from '../api';
import { Lecture, TranscriptionSegment } from '../'; // Assuming index.ts exports these types

const LectureViewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate(); // Hook for navigation
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Fetch lecture data when the component mounts or the ID changes
  useEffect(() => {
    let isMounted = true; // Flag to prevent state updates on unmounted component

    const fetchLecture = async () => {
      if (!id) {
        setError('Lecture ID is missing.');
        setIsLoading(false);
        return;
      }
      // Reset state for new fetch
      setIsLoading(true);
      setError('');
      setLecture(null); // Clear previous lecture data
      setCurrentSlideIndex(0); // Reset slide index

      try {
        const lectureData = await APIService.getLecture(id);
        if (isMounted) {
          setLecture(lectureData);
          // Check if lecture status indicates ongoing processing
          if (lectureData.status !== 'completed' && lectureData.status !== 'failed') {
             // Optional: Implement polling or refresh mechanism if status is 'processing', 'downloading', etc.
             console.warn(`Lecture status is ${lectureData.status}. Data might be incomplete.`);
             // You might want to show a different UI or auto-refresh here.
          }
        }
      } catch (err) {
        if (isMounted) {
           let errorMessage = 'Failed to load lecture.';
           if (err instanceof Error) {
               errorMessage = err.message;
           } else if (typeof err === 'object' && err !== null && 'detail' in err) {
               // Handle APIError structure if available
               errorMessage = (err as any).detail || errorMessage;
           }
           setError(errorMessage);
           console.error("Error fetching lecture:", err);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchLecture();

    // Cleanup function to run when component unmounts or ID changes
    return () => {
      isMounted = false;
    };
  }, [id]); // Dependency array only includes 'id'

  // Memoize the filtered transcription segments for the current slide
  const slideTranscriptions = useMemo(() => {
    // Return empty array if lecture data or transcriptions aren't available yet
    if (!lecture?.transcription) {
      return [];
    }
    // Filter segments based on the current slide index
    return lecture.transcription.filter(
      (segment) => segment.slideIndex === currentSlideIndex
    );
  }, [lecture, currentSlideIndex]); // Recalculate only when lecture data or slide index changes

  // Navigation handlers
  const handlePreviousSlide = () => {
    setCurrentSlideIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNextSlide = () => {
    if (lecture) {
      setCurrentSlideIndex((prev) => Math.min(lecture.slides.length - 1, prev + 1));
    }
  };

  // Time formatting utility
  const formatTime = (seconds: number): string => {
    if (isNaN(seconds) || seconds < 0) return '0:00';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // --- Render Logic ---

  if (isLoading) {
    return (
      <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-gray-600">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
        <p>Loading Lecture Data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-red-600 bg-red-50 p-6 rounded-lg shadow max-w-md mx-auto">
        <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
        <p className="text-lg font-semibold mb-2">Error Loading Lecture</p>
        <p className="text-center mb-4">{error}</p>
        <button
            onClick={() => navigate('/')}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 flex items-center"
        >
            <Home className="w-4 h-4 mr-2" /> Go Home
        </button>
      </div>
    );
  }

  if (!lecture) {
     // This state might occur briefly or if fetching fails without setting error explicitly
    return (
        <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-gray-500">
            <p>No lecture data available.</p>
             <button
                onClick={() => navigate('/')}
                className="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 flex items-center"
            >
                <Home className="w-4 h-4 mr-2" /> Go Home
            </button>
        </div>
    );
  }

  // Main lecture view content
  return (
    <div className="min-h-[calc(100vh-8rem)] flex flex-col bg-gray-50 p-4 md:p-6">
      <div className="max-w-7xl mx-auto w-full space-y-4 flex-grow flex flex-col">
        {/* Header/Navigation within the page */}
        <div className="flex items-center justify-between bg-white p-3 md:p-4 rounded-lg shadow-sm flex-shrink-0">
          <button
            onClick={handlePreviousSlide}
            disabled={currentSlideIndex === 0}
            aria-label="Previous Slide"
            className="p-2 rounded-full text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>

          <div className="text-center flex-grow mx-4 overflow-hidden">
            <h1 className="text-lg md:text-xl font-semibold truncate" title={lecture.title}>
              {lecture.title}
            </h1>
            <span className="text-sm text-gray-500">
              Slide {currentSlideIndex + 1} of {lecture.slides.length}
            </span>
            {/* Display lecture status if needed */}
            {/* <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${lecture.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>{lecture.status}</span> */}
          </div>

          <button
            onClick={handleNextSlide}
            disabled={currentSlideIndex === lecture.slides.length - 1}
            aria-label="Next Slide"
            className="p-2 rounded-full text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 flex-grow overflow-hidden">
          {/* Slide Display Area */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden flex flex-col">
            <div className="p-4 flex-grow flex items-center justify-center bg-gray-100 min-h-[300px] md:min-h-[400px]">
              {lecture.slides[currentSlideIndex]?.imageUrl ? (
                <img
                  // Use a key to force re-render if needed, though src change should suffice
                  key={lecture.slides[currentSlideIndex].index}
                  src={lecture.slides[currentSlideIndex].imageUrl}
                  alt={`Slide ${currentSlideIndex + 1}`}
                  className="max-w-full max-h-full object-contain rounded" // Use object-contain
                  loading="lazy" // Add lazy loading
                />
              ) : (
                <div className="text-gray-500">Slide Image Not Available</div>
              )}
            </div>
          </div>

          {/* Transcription Panel Area */}
          <div className="bg-white rounded-lg shadow-sm flex flex-col overflow-hidden">
             <h2 className="text-lg md:text-xl font-semibold p-4 border-b text-right flex-shrink-0">
                 תמלול שקופית {currentSlideIndex + 1}
              </h2>
            {/* Scrollable Transcription Content */}
            <div dir="rtl" className="space-y-1 overflow-y-auto flex-grow p-4 custom-scrollbar"> {/* Added custom-scrollbar class */}
              {slideTranscriptions.length > 0 ? (
                slideTranscriptions.map((segment) => (
                  <div
                    key={segment.id} // Ensure IDs are unique if coming from DB
                    className="flex items-start p-2 hover:bg-gray-50 rounded text-sm md:text-base"
                  >
                    {/* Timestamp aligned to the start (right in RTL) */}
                    <span className="ml-3 text-xs text-gray-500 whitespace-nowrap pt-1">
                      {formatTime(segment.startTime)}
                    </span>
                    {/* Text takes remaining space */}
                    <p className="text-gray-800 flex-1 text-right leading-relaxed">
                      {segment.text}
                    </p>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-10">
                  אין תמלול זמין עבור שקופית זו.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LectureViewPage;