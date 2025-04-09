// src/pages/LectureViewPage.tsx
import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Home, AlertTriangle, Loader2 } from 'lucide-react';
import { APIService } from '../api';
import { useLectureData } from './useLectureData'; // Custom hook for data logic
import { LectureHeader } from '../components/LectureHeader'; // Component 2
import { LectureContent } from '../components/LectureContent'; // Component 3
// Assuming Lecture type is imported via '../index'

/**
 * Main page component for viewing a processed lecture. (Component 1 of 3)
 */
const LectureViewPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    // Hook manages: lecture, isLoading, isRefreshing, error, refetch
    const { lecture, isLoading, isRefreshing, error, refetch } = useLectureData(id);

    // State specific to the page's orchestration logic
    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
    const [isSummarizing, setIsSummarizing] = useState<boolean>(false);
    const [summaryError, setSummaryError] = useState<string>('');

    // --- Event Handlers ---
    const handlePreviousSlide = () => {
        setCurrentSlideIndex((prev) => Math.max(0, prev - 1));
        setSummaryError(''); // Clear summary error on navigation
    };

    const handleNextSlide = () => {
        // Ensure lecture and slides exist before trying to access length
        if (lecture?.slides) {
            setCurrentSlideIndex((prev) => Math.min(lecture.slides.length - 1, prev + 1));
            setSummaryError(''); // Clear summary error on navigation
        }
    };

    const handleSummarizeClick = async () => {
        // Check conditions before proceeding
        const currentSlideExists = lecture?.slides?.[currentSlideIndex];
        if (!id || lecture?.status !== 'completed' || isSummarizing || !currentSlideExists) {
            console.warn("Summarization blocked:", { id, status: lecture?.status, isSummarizing, currentSlideExists });
            return;
        }

        setIsSummarizing(true);
        setSummaryError(''); // Clear previous summary error

        try {
            const result = await APIService.summarizeSlide(id, currentSlideIndex);
            // Refetch the entire lecture data to ensure consistency, especially with summary updates
            await refetch();

            // Optionally, show a message if the API indicates no summary was possible (e.g., no text)
            if (result.summary === null && result.message) {
                 setSummaryError(result.message);
            }
        } catch (err) {
            console.error("Summarization API call failed:", err);
            setSummaryError(err instanceof Error ? err.message : "An unknown error occurred during summarization.");
        } finally {
            setIsSummarizing(false); // Ensure loading state is turned off
        }
    };

    // --- Conditional Rendering for Loading/Error/NoData States ---
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
                <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 flex items-center">
                    <Home className="w-4 h-4 mr-2" /> Go Home
                </button>
            </div>
        );
    }

    // Handle case where loading is finished but lecture data is still null
    if (!lecture) {
        return (
            <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-gray-500">
                <p>No lecture data found.</p>
                 <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 flex items-center">
                    <Home className="w-4 h-4 mr-2" /> Go Home
                </button>
            </div>
        );
    }

    // --- Render Main Lecture View ---
    return (
        <div className="min-h-[calc(100vh-8rem)] flex flex-col bg-gray-50 p-4 md:p-6">
            {/* Max width container */}
            <div className="max-w-7xl mx-auto w-full space-y-4 flex-grow flex flex-col">

                {/* Component 2: Header/Controls */}
                <LectureHeader
                    title={lecture.title}
                    status={lecture.status}
                    currentSlideIndex={currentSlideIndex}
                    totalSlides={lecture.slides.length}
                    onPrev={handlePreviousSlide}
                    onNext={handleNextSlide}
                    onRefresh={refetch} // Pass the refetch function from the hook
                    isRefreshing={isRefreshing}
                />

                {/* Component 3: Main Content Display */}
                <LectureContent
                    currentSlide={lecture.slides[currentSlideIndex]}
                    allSegments={lecture.transcription}
                    lectureStatus={lecture.status}
                    currentSlideIndex={currentSlideIndex}
                    isSummarizing={isSummarizing}
                    summaryError={summaryError}
                    onSummarize={handleSummarizeClick}
                />

            </div> {/* End Max Width Container */}
        </div> // End Page Container
    );
};

export default LectureViewPage;

