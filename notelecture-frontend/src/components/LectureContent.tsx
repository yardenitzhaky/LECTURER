// src/components/LectureContent.tsx
import React, { useMemo, useState } from 'react';
import { FileText, Sparkles, Loader2, Copy, Check, Edit3 } from 'lucide-react';
import { Slide, TranscriptionSegment } from '../types';
import { formatTime } from '../utils/utils';
import { Modal } from './Modal';

interface LectureContentProps {
    currentSlide: Slide | undefined;
    allSegments: TranscriptionSegment[];
    lectureStatus: string;
    currentSlideIndex: number;
    isSummarizing: boolean;
    summaryError: string;
    onSummarize: () => void;
    onCustomSummarize: (customPrompt: string) => void;
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
    onCustomSummarize,
}) => {
    // --- Local State ---
    const [isCopied, setIsCopied] = useState(false);
    const [copyError, setCopyError] = useState('');
    const [isCustomPromptModalOpen, setIsCustomPromptModalOpen] = useState(false);
    const [customPrompt, setCustomPrompt] = useState('');

    // --- Derived State & Memoization ---
    const slideTranscriptions = useMemo(() => {
        return allSegments.filter(
            (segment) => segment.slideIndex === currentSlideIndex
        );
    }, [allSegments, currentSlideIndex]);

    const canSummarize = lectureStatus === 'completed' && !isSummarizing;
    const showSummarizeButton = canSummarize && !currentSlide?.summary && !summaryError;
    const isProcessingTranscription = lectureStatus !== 'completed' && lectureStatus !== 'failed';

    // --- Copy Functionality ---
    const handleCopyTranscription = async () => {
        const fullText = slideTranscriptions.map(segment => segment.text).join(' ');
        
        if (!fullText.trim()) {
            setCopyError('אין טקסט להעתקה');
            setTimeout(() => setCopyError(''), 3000);
            return;
        }

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(fullText);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = fullText;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
            
            setIsCopied(true);
            setCopyError('');
            setTimeout(() => setIsCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy text:', err);
            setCopyError('שגיאה בהעתקה');
            setTimeout(() => setCopyError(''), 3000);
        }
    };

    const handleCopyAllTranscription = async () => {
        // Group all segments by slide index and create a formatted text
        const segmentsBySlide = allSegments.reduce((acc, segment) => {
            if (!acc[segment.slideIndex]) {
                acc[segment.slideIndex] = [];
            }
            acc[segment.slideIndex].push(segment);
            return acc;
        }, {} as Record<number, TranscriptionSegment[]>);

        const sortedSlideIndexes = Object.keys(segmentsBySlide).map(Number).sort((a, b) => a - b);
        
        const fullText = sortedSlideIndexes.map(slideIndex => {
            const slideSegments = segmentsBySlide[slideIndex].sort((a, b) => a.startTime - b.startTime);
            const slideText = slideSegments.map(segment => segment.text).join(' ');
            return `שקופית ${slideIndex + 1}:\n${slideText}\n`;
        }).join('\n');

        if (!fullText.trim()) {
            setCopyError('אין תמלול להעתקה');
            setTimeout(() => setCopyError(''), 3000);
            return;
        }

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(fullText);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = fullText;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
            
            setIsCopied(true);
            setCopyError('');
            setTimeout(() => setIsCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy full text:', err);
            setCopyError('שגיאה בהעתקה');
            setTimeout(() => setCopyError(''), 3000);
        }
    };

    // --- Custom Prompt Functionality ---
    const handleCustomPromptSubmit = () => {
        if (!customPrompt.trim()) {
            return;
        }
        
        onCustomSummarize(customPrompt.trim());
        setIsCustomPromptModalOpen(false);
        setCustomPrompt('');
    };

    const handleOpenCustomPrompt = () => {
        setCustomPrompt('');
        setIsCustomPromptModalOpen(true);
    };

    // --- Render ---
    return (
        <>
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
                        {/* Conditional Buttons: Summarize or Loading */}
                        {isSummarizing ? (
                             <button disabled={true} className="px-3 py-1 text-xs bg-gray-400 text-white rounded-md cursor-wait flex items-center">
                                 <Loader2 className="w-3 h-3 mr-1 animate-spin" /> מעבד...
                             </button>
                        ) : showSummarizeButton ? (
                            <div className="flex space-x-2">
                                <button onClick={handleOpenCustomPrompt} className="px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600 text-white rounded-md flex items-center transition-opacity duration-200">
                                    <Edit3 className="w-3 h-3 mr-1" /> סיכום מותאם
                                </button>
                                <button onClick={onSummarize} className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-md flex items-center transition-opacity duration-200">
                                    <Sparkles className="w-3 h-3 mr-1" /> צור סיכום
                                </button>
                            </div>
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
                <div className="p-4 border-b flex-shrink-0 flex justify-between items-center">
                    <h2 className="text-lg md:text-xl font-semibold text-right">
                        תמלול שקופית {currentSlideIndex + 1}
                    </h2>
                    
                    {/* Copy Buttons */}
                    <div className="flex items-center space-x-2">
                        {copyError && (
                            <span className="text-red-500 text-sm">{copyError}</span>
                        )}
                        <button
                            onClick={handleCopyAllTranscription}
                            disabled={allSegments.length === 0 || isProcessingTranscription}
                            className={`px-3 py-2 text-sm rounded-md flex items-center transition-all duration-200 ${
                                isCopied 
                                    ? 'bg-green-500 text-white'
                                    : allSegments.length === 0 || isProcessingTranscription
                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                        : 'bg-purple-500 hover:bg-purple-600 text-white'
                            }`}
                        >
                            {isCopied ? (
                                <>
                                    <Check className="w-4 h-4 mr-1" />
                                    הועתק!
                                </>
                            ) : (
                                <>
                                    <Copy className="w-4 h-4 mr-1" />
                                    העתק הכל
                                </>
                            )}
                        </button>
                        <button
                            onClick={handleCopyTranscription}
                            disabled={slideTranscriptions.length === 0 || isProcessingTranscription}
                            className={`px-3 py-2 text-sm rounded-md flex items-center transition-all duration-200 ${
                                isCopied 
                                    ? 'bg-green-500 text-white'
                                    : slideTranscriptions.length === 0 || isProcessingTranscription
                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                            }`}
                        >
                            {isCopied ? (
                                <>
                                    <Check className="w-4 h-4 mr-1" />
                                    הועתק!
                                </>
                            ) : (
                                <>
                                    <Copy className="w-4 h-4 mr-1" />
                                    העתק שקופית
                                </>
                            )}
                        </button>
                    </div>
                </div>
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

        </div> {/* End Grid Layout */}
        
        {/* Custom Prompt Modal */}
        <Modal
            isOpen={isCustomPromptModalOpen}
            onClose={() => setIsCustomPromptModalOpen(false)}
            title="סיכום מותאם אישית"
            maxWidth="max-w-lg"
        >
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        הכנס הנחיות לסיכום:
                    </label>
                    <textarea
                        value={customPrompt}
                        onChange={(e) => setCustomPrompt(e.target.value)}
                        className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        placeholder="לדוגמה: צור רשימה של נקודות המפתח העיקריות בפורמט של תקציבי מהנושא..."
                        dir="rtl"
                    />
                </div>
                
                <div className="flex justify-end space-x-3 pt-4">
                    <button
                        onClick={() => setIsCustomPromptModalOpen(false)}
                        className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                    >
                        ביטול
                    </button>
                    <button
                        onClick={handleCustomPromptSubmit}
                        disabled={!customPrompt.trim()}
                        className={`px-4 py-2 rounded-md transition-colors ${
                            customPrompt.trim()
                                ? 'bg-purple-500 hover:bg-purple-600 text-white'
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        }`}
                    >
                        צור סיכום
                    </button>
                </div>
            </div>
        </Modal>
        </>
    );
};

export default LectureContent;