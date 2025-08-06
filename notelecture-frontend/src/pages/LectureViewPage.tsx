// src/pages/LectureViewPage.tsx
import React, { useState, useRef, useEffect, useCallback } from 'react'; // Import useRef, useEffect, useCallback
import { useParams, useNavigate } from 'react-router-dom';
import { Home, AlertTriangle, Loader2 } from 'lucide-react';
import { APIService } from '../api';
import { useLectureData } from './useLectureData'; // Custom hook for data logic
import { LectureHeader } from '../components/LectureHeader'; // Component 2
import { LectureContent } from '../components/LectureContent'; // Component 3

const DEBOUNCE_DELAY_MS = 750; // Debounce time for refresh button

/**
 * Main page component for viewing a processed lecture. (Component 1 of 3)
 */
const LectureViewPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const { lecture, isLoading, isRefreshing, error, refetch } = useLectureData(id);

    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
    const [isSummarizing, setIsSummarizing] = useState<boolean>(false);
    const [summaryError, setSummaryError] = useState<string>('');

    // Ref for debounce timeout
    const debounceTimeoutRef = useRef<number | null>(null);

    // Cleanup debounce timer on unmount
    useEffect(() => {
        return () => {
            if (debounceTimeoutRef.current) {
                clearTimeout(debounceTimeoutRef.current);
            }
        };
    }, []);

    // Debounced refresh handler
    const handleDebouncedRefresh = useCallback(() => {
        if (isRefreshing) return; // Don't queue another refresh if one is in progress

        if (debounceTimeoutRef.current) {
            clearTimeout(debounceTimeoutRef.current);
        }
        debounceTimeoutRef.current = window.setTimeout(() => {
            console.log('Executing debounced refresh...');
            refetch();
        }, DEBOUNCE_DELAY_MS);
        console.log('Refresh debounced...'); // Log that debounce is active
    }, [refetch, isRefreshing]); // Depend on refetch and isRefreshing


    const handlePreviousSlide = () => {
        if (isRefreshing) return; // Prevent navigation during refresh
        setCurrentSlideIndex((prev) => Math.max(0, prev - 1));
        setSummaryError('');
    };

    const handleNextSlide = () => {
        if (isRefreshing) return; // Prevent navigation during refresh
        if (lecture?.slides) {
            setCurrentSlideIndex((prev) => Math.min(lecture.slides.length - 1, prev + 1));
            setSummaryError('');
        }
    };

    const handleSummarizeClick = async (customPrompt?: string) => {
        const currentSlideExists = lecture?.slides?.[currentSlideIndex];
        if (!id || lecture?.status !== 'completed' || isSummarizing || !currentSlideExists) {
            console.warn("Summarization blocked:", { id, status: lecture?.status, isSummarizing, currentSlideExists });
            return;
        }

        setIsSummarizing(true);
        setSummaryError('');

        try {
            const result = await APIService.summarizeSlide(id, currentSlideIndex, customPrompt);
            await refetch(); // Refetch data after summarizing
            if (result.summary === null && result.message) {
                 setSummaryError(result.message);
            }
        } catch (err) {
            console.error("Summarization API call failed:", err);
            setSummaryError(err instanceof Error ? err.message : "An unknown error occurred during summarization.");
        } finally {
            setIsSummarizing(false);
        }
    };

    const handleCustomSummarizeClick = (customPrompt: string) => {
        handleSummarizeClick(customPrompt);
    };

    // --- Conditional Rendering ---
    if (isLoading) {
        // ... loading state ...
        return (
            <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-gray-600">
                <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
                <p>Loading Lecture Data...</p>
            </div>
        );
    }

    if (error) {
        // ... error state ...
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

    if (!lecture) {
        // ... no lecture data state ...
         return (
            <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-gray-500">
                <p>No lecture data found for this ID.</p>
                 <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 flex items-center">
                    <Home className="w-4 h-4 mr-2" /> Go Home
                </button>
            </div>
        );
    }

    // --- Render Main Lecture View ---
    return (
        <div className="min-h-[calc(100vh-8rem)] flex flex-col bg-gray-50 p-4 md:p-6">
            <div className="max-w-7xl mx-auto w-full space-y-4 flex-grow flex flex-col">
                {/* Pass the debounced handler to the header */}
                <LectureHeader
                    title={lecture.title}
                    status={lecture.status}
                    currentSlideIndex={currentSlideIndex}
                    totalSlides={lecture.slides.length}
                    onPrev={handlePreviousSlide}
                    onNext={handleNextSlide}
                    onRefresh={handleDebouncedRefresh} // Use debounced handler
                    isRefreshing={isRefreshing}
                />

                <LectureContent
                    currentSlide={lecture.slides[currentSlideIndex]}
                    allSegments={lecture.transcription}
                    lectureStatus={lecture.status}
                    currentSlideIndex={currentSlideIndex}
                    isSummarizing={isSummarizing}
                    summaryError={summaryError}
                    onSummarize={() => handleSummarizeClick()}
                    onCustomSummarize={handleCustomSummarizeClick}
                />
            </div>
        </div>
    );
};

export default LectureViewPage;