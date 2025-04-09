// src/components/LectureContent.tsx
import React, { useMemo } from 'react';
import { FileText, Sparkles, Loader2 } from 'lucide-react';
import { Slide, TranscriptionSegment } from '../index';
import { formatTime } from '../format';

interface LectureContentProps {
    currentSlide: Slide | undefined;
    allSegments: TranscriptionSegment[];
    lectureStatus: string;
    currentSlideIndex: number;
    isSummarizing: boolean;
    summaryError: string;
    onSummarize: () => void;
}

/**
 * Renders the main display area including the slide, summary, and transcription. (Component 3 of 3)
 */
export const LectureContent: React.FC<LectureContentProps> = ({
    currentSlide,
    allSegments,
    lectureStatus,
    currentSlideIndex,
    isSummarizing,
    summaryError,
    onSummarize,
}) => {
    // --- Derived State & Memoization ---
    const slideTranscriptions = useMemo(() => {
        return allSegments.filter(
            (segment) => segment.slideIndex === currentSlideIndex
        );
    }, [allSegments, currentSlideIndex]);

    const canSummarize = lectureStatus === 'completed' && !isSummarizing;
    const showSummarizeButton = canSummarize && !currentSlide?.summary && !summaryError;
    const isProcessingTranscription = lectureStatus !== 'completed' && lectureStatus !== 'failed';

    // --- Render ---
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 flex-grow overflow-hidden">

            {/* --- Left Panel: Slide Image + Summary --- */}
            <div className="bg-white rounded-lg shadow-sm overflow-hidden flex flex-col">
                {/* Slide Image Display */}
                <div className="p-4 flex-grow flex items-center justify-center bg-gray-100 min-h-[300px] md:min-h-[400px]">
                    {currentSlide?.imageUrl ? (
                        <img
                            key={currentSlide.index} // Key helps React update image correctly
                            src={currentSlide.imageUrl}
                            alt={`Slide ${currentSlide.index + 1}`}
                            className="max-w-full max-h-full object-contain rounded"
                            loading="lazy"
                        />
                    ) : (
                        <div className="text-gray-500">Slide Image Not Available</div>
                    )}
                </div>

                {/* Summary Section */}
                <div
                    dir="rtl" // Right-to-left for Hebrew
                    className="p-4 border-t border-gray-200 bg-gray-50 flex-shrink-0 min-h-[8rem] overflow-y-auto custom-scrollbar relative"
                >
                    {/* Sticky Header for Title and Button */}
                    <div className="flex justify-between items-center mb-2 sticky top-0 bg-gray-50 py-1 z-10">
                        <h3 className="text-md font-semibold flex items-center text-gray-700">
                            <FileText className="w-5 h-5 ml-2"/>
                            סיכום שקופית
                        </h3>
                        {/* Conditional Button: Summarize or Loading */}
                        {isSummarizing ? (
                             <button disabled={true} className="px-3 py-1 text-xs bg-gray-400 text-white rounded-md cursor-wait flex items-center">
                                 <Loader2 className="w-3 h-3 mr-1 animate-spin" /> מעבד...
                             </button>
                        ) : showSummarizeButton ? (
                            <button onClick={onSummarize} className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-md flex items-center transition-opacity duration-200">
                                <Sparkles className="w-3 h-3 mr-1" /> צור סיכום
                            </button>
                        ) : null}
                    </div>

                    {/* Summary Error Display */}
                    {summaryError && !isSummarizing && (
                       <div className="text-red-600 text-sm p-2 bg-red-50 rounded my-2">
                          <strong>שגיאה:</strong> {summaryError}
                       </div>
                    )}

                    {/* Summary Text Display */}
                    {currentSlide?.summary && !isSummarizing && (
                        <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                           {currentSlide.summary}
                        </p>
                    )}

                    {/* Placeholder Text */}
                    {!currentSlide?.summary && !isSummarizing && !summaryError && (
                        <p className="text-sm text-gray-500 italic mt-2">
                            {lectureStatus === 'completed'
                                ? "(לחץ על 'צור סיכום' אם זמין, או שאין טקסט לסכם)"
                                : "(סיכום יהיה זמין לאחר השלמת העיבוד)"
                            }
                        </p>
                    )}
                </div> {/* End Summary Section */}
            </div> {/* End Left Panel */}

            {/* --- Right Panel: Transcription --- */}
            <div className="bg-white rounded-lg shadow-sm flex flex-col overflow-hidden">
                <h2 className="text-lg md:text-xl font-semibold p-4 border-b text-right flex-shrink-0">
                    תמלול שקופית {currentSlideIndex + 1}
                </h2>
                <div dir="rtl" className="space-y-1 overflow-y-auto flex-grow p-4 custom-scrollbar">
                    {/* Transcription Segments or Loading/Empty State */}
                    {slideTranscriptions.length > 0 ? (
                        slideTranscriptions.map((segment) => (
                            <div key={segment.id} className="flex items-start p-2 hover:bg-gray-50 rounded text-sm md:text-base">
                                <span className="ml-3 text-xs text-gray-500 whitespace-nowrap pt-1">
                                    {formatTime(segment.startTime)}
                                </span>
                                <p className="text-gray-800 flex-1 text-right leading-relaxed">
                                    {segment.text}
                                </p>
                            </div>
                        ))
                    ) : isProcessingTranscription ? ( // Check if lecture is still processing
                        <div className="text-center text-gray-500 py-10 flex flex-col items-center">
                            <Loader2 className="w-5 h-5 animate-spin mb-2" />
                            <span>התמלול נוצר כעת...</span>
                        </div>
                    ) : ( // Lecture is completed/failed, but no segments for this slide
                        <div className="text-center text-gray-500 py-10">
                            אין תמלול זמין עבור שקופית זו.
                        </div>
                    )}
                </div>
            </div> {/* End Right Panel */}

        </div> // End Grid Layout
    );
};

export default LectureContent;