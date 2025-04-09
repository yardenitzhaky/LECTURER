// src/components/LectureHeader.tsx
import React from 'react';
import { ChevronLeft, ChevronRight, RefreshCw, Loader2 } from 'lucide-react';

interface LectureHeaderProps {
    title: string;
    status: string;
    currentSlideIndex: number;
    totalSlides: number;
    onPrev: () => void;
    onNext: () => void;
    onRefresh: () => void;
    isRefreshing: boolean;
}

// Internal Status Badge Logic (or could be a separate util function if preferred)
const renderStatusBadge = (status: string) => {
     switch (status) {
        case 'completed':
            return <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">Completed</span>;
        case 'failed':
            return <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Failed</span>;
        case 'pending':
        case 'processing':
        case 'processing_slides':
        case 'downloading':
        case 'transcribing':
        case 'matching':
        case 'saving_segments':
             return (
                <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 flex items-center">
                    <Loader2 className="w-3 h-3 animate-spin mr-1"/> Processing...
                </span>
             );
        default:
            return <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">{status}</span>;
    }
};

/**
 * Renders the top control bar for the lecture view. (Component 2 of 3)
 */
export const LectureHeader: React.FC<LectureHeaderProps> = ({
    title,
    status,
    currentSlideIndex,
    totalSlides,
    onPrev,
    onNext,
    onRefresh,
    isRefreshing,
}) => {
    const isProcessing = status !== 'completed' && status !== 'failed';

    return (
        <div className="flex items-center justify-between bg-white p-3 md:p-4 rounded-lg shadow-sm flex-shrink-0">
            {/* Previous Button */}
            <button
                onClick={onPrev}
                disabled={currentSlideIndex === 0}
                aria-label="Previous Slide"
                className="p-2 rounded-full text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
                <ChevronLeft className="w-6 h-6" />
            </button>

            {/* Center Info */}
            <div className="text-center flex-grow mx-4 overflow-hidden flex flex-col items-center">
                <h1 className="text-lg md:text-xl font-semibold truncate" title={title}>
                    {title}
                </h1>
                <div className="flex items-center justify-center mt-1">
                    <span className="text-sm text-gray-500">
                        Slide {currentSlideIndex + 1} of {totalSlides}
                    </span>
                    {renderStatusBadge(status)} {/* Use internal function */}
                    {isProcessing && (
                        <button
                            onClick={onRefresh}
                            disabled={isRefreshing}
                            title="Refresh Status"
                            className="ml-2 p-1 rounded-full text-gray-500 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-wait"
                        >
                            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                        </button>
                    )}
                </div>
            </div>

            {/* Next Button */}
            <button
                onClick={onNext}
                disabled={currentSlideIndex >= totalSlides - 1}
                aria-label="Next Slide"
                className="p-2 rounded-full text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
                <ChevronRight className="w-6 h-6" />
            </button>
        </div>
    );
};

export default LectureHeader;