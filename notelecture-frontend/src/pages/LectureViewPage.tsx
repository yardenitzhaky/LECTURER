// src/pages/LectureViewPage.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    ChevronLeft, ChevronRight, AlertTriangle, Loader2, Home, FileText, RefreshCw, Sparkles // Added Sparkles
} from 'lucide-react';
import { APIService } from '../api';
import { Lecture, Slide, TranscriptionSegment } from '../'; // Assuming index.ts exports these types

const LectureViewPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [lecture, setLecture] = useState<Lecture | null>(null);
    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState<string>('');
    const [pollingIntervalId, setPollingIntervalId] = useState<number | null>(null);

    // --- State for Summarization ---
    const [isSummarizing, setIsSummarizing] = useState<boolean>(false);
    const [summaryError, setSummaryError] = useState<string>('');
    // --- End State for Summarization ---


    // Fetch lecture data function
    const fetchLecture = async (showLoadingSpinner = true) => {
        if (!id) {
            setError('Lecture ID is missing.');
            setIsLoading(false);
            return;
        }
        if (showLoadingSpinner) setIsLoading(true);
        else setIsRefreshing(true);
        setError(''); // Clear previous errors on fetch attempt
        // Only clear lecture data on initial load, not refresh
        if (showLoadingSpinner) {
            setLecture(null);
            setCurrentSlideIndex(0);
        }

        let lectureData: Lecture | null = null;
        try {
            lectureData = await APIService.getLecture(id);
            setLecture(lectureData); // Update lecture state

            // Stop polling if completed or failed
            if (lectureData.status === 'completed' || lectureData.status === 'failed') {
                if (pollingIntervalId) {
                    console.log(`Polling stopped for lecture ${id}. Status: ${lectureData.status}`);
                    clearInterval(pollingIntervalId);
                    setPollingIntervalId(null);
                }
            } else {
                // Start or continue polling if status indicates ongoing processing
                if (!pollingIntervalId && showLoadingSpinner) { // Only start polling on initial load if needed
                    console.log(`Polling started for lecture ${id}. Status: ${lectureData.status}`);
                    const intervalId = window.setInterval(() => { // Use window.setInterval for clarity
                        console.log(`Polling lecture ${id}...`);
                        fetchLecture(false); // Fetch without main loading spinner
                    }, 15000); // Poll every 15 seconds
                    setPollingIntervalId(intervalId);
                }
            }

        } catch (err) {
            let errorMessage = 'Failed to load lecture data.';
            if (err instanceof Error) errorMessage = err.message;
            else if (typeof err === 'object' && err !== null && 'detail' in err) errorMessage = (err as any).detail || errorMessage;
            setError(errorMessage);
            setLecture(null); // Clear data on error
            setCurrentSlideIndex(0);
            console.error("Error fetching lecture:", err);
            // Stop polling on error
            if (pollingIntervalId) {
                clearInterval(pollingIntervalId);
                setPollingIntervalId(null);
            }
        } finally {
            setIsLoading(false);
            setIsRefreshing(false);
        }
    };

    // useEffect for initial fetch and cleanup polling on unmount
    useEffect(() => {
        fetchLecture(); // Initial fetch

        return () => {
            if (pollingIntervalId) {
                console.log(`Clearing polling interval ${pollingIntervalId} on unmount`);
                clearInterval(pollingIntervalId);
                // No need to setPollingIntervalId(null) here as component is unmounting
            }
        };
    }, [id]); // Re-run only if ID changes

    // Memoize the filtered transcription segments for the current slide
    const slideTranscriptions = useMemo(() => {
        if (!lecture?.transcription) return [];
        return lecture.transcription.filter(
            (segment) => segment.slideIndex === currentSlideIndex
        );
    }, [lecture?.transcription, currentSlideIndex]);

    // Get the current slide data
    const currentSlideData = useMemo(() => {
        return lecture?.slides[currentSlideIndex];
    }, [lecture?.slides, currentSlideIndex]);

    // Navigation handlers
    const handlePreviousSlide = () => {
        setCurrentSlideIndex((prev) => Math.max(0, prev - 1));
        setSummaryError(''); // Clear summary error when changing slides
    };
    const handleNextSlide = () => {
        if (lecture) {
            setCurrentSlideIndex((prev) => Math.min(lecture.slides.length - 1, prev + 1));
            setSummaryError(''); // Clear summary error when changing slides
        }
    };

    // Time formatting utility
    const formatTime = (seconds: number): string => {
        if (isNaN(seconds) || seconds < 0) return '0:00';
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    };

    // --- Summarization Handler ---
    const handleSummarizeClick = async () => {
        if (!id || lecture?.status !== 'completed' || isSummarizing || !currentSlideData) {
            console.warn("Summarization blocked:", { id, status: lecture?.status, isSummarizing, currentSlideData });
            return;
        }

        setIsSummarizing(true);
        setSummaryError(''); // Clear previous error

        try {
            console.log(`Requesting summary for lecture ${id}, slide ${currentSlideIndex}`);
            const result = await APIService.summarizeSlide(id, currentSlideIndex);
            console.log("Summarization API result:", result);

            // Update local lecture state immutably
            setLecture(prevLecture => {
                if (!prevLecture) return null;
                const updatedSlides = prevLecture.slides.map(slide =>
                    slide.index === currentSlideIndex
                        ? { ...slide, summary: result.summary ?? undefined } // Use result.summary, default to undefined
                        : slide
                );
                return { ...prevLecture, slides: updatedSlides };
            });

            // If summary is explicitly null from API (e.g., no text), show message
            if (result.summary === null && result.message) {
                 setSummaryError(result.message);
            }

        } catch (error) {
            console.error("Summarization failed:", error);
            setSummaryError(error instanceof Error ? error.message : "An unknown error occurred during summarization.");
        } finally {
            setIsSummarizing(false);
        }
    };
    // --- End Summarization Handler ---


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
                <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 flex items-center">
                    <Home className="w-4 h-4 mr-2" /> Go Home
                </button>
            </div>
        );
    }

    if (!lecture) {
        return (
            <div className="min-h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-gray-500">
                <p>No lecture data available.</p>
                <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 flex items-center">
                    <Home className="w-4 h-4 mr-2" /> Go Home
                </button>
            </div>
        );
    }

    // Status Badge Component/Function
    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'completed': return <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">Completed</span>;
            case 'failed': return <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Failed</span>;
            // case 'summarizing': // This status might not be set if on-demand
            case 'saving_segments': case 'matching': case 'transcribing':
            case 'downloading': case 'processing_slides': case 'processing': case 'pending':
                 return <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 flex items-center"><Loader2 className="w-3 h-3 animate-spin mr-1"/>Processing...</span>;
            default: return <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">{status}</span>;
        }
    }

    // Determine if the summarize button should be shown/enabled
    const showSummarizeButton = lecture.status === 'completed' && !currentSlideData?.summary && !isSummarizing;
    const canSummarize = lecture.status === 'completed' && !isSummarizing; // Button enabled if completed and not busy

    return (
        <div className="min-h-[calc(100vh-8rem)] flex flex-col bg-gray-50 p-4 md:p-6">
            <div className="max-w-7xl mx-auto w-full space-y-4 flex-grow flex flex-col">
                {/* Header/Navigation */}
                <div className="flex items-center justify-between bg-white p-3 md:p-4 rounded-lg shadow-sm flex-shrink-0">
                    <button onClick={handlePreviousSlide} disabled={currentSlideIndex === 0} aria-label="Previous Slide" className="p-2 rounded-full text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"> <ChevronLeft className="w-6 h-6" /> </button>
                    <div className="text-center flex-grow mx-4 overflow-hidden flex flex-col items-center">
                       <h1 className="text-lg md:text-xl font-semibold truncate" title={lecture.title}> {lecture.title} </h1>
                       <div className="flex items-center justify-center mt-1">
                          <span className="text-sm text-gray-500"> Slide {currentSlideIndex + 1} of {lecture.slides.length} </span>
                          {getStatusBadge(lecture.status)}
                          {/* Refresh button for non-final states */}
                          {(lecture.status !== 'completed' && lecture.status !== 'failed') && (
                              <button onClick={() => fetchLecture(false)} disabled={isRefreshing} title="Refresh Status" className="ml-2 p-1 rounded-full text-gray-500 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-wait"> <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} /> </button>
                          )}
                       </div>
                    </div>
                    <button onClick={handleNextSlide} disabled={currentSlideIndex === lecture.slides.length - 1} aria-label="Next Slide" className="p-2 rounded-full text-gray-700 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"> <ChevronRight className="w-6 h-6" /> </button>
                </div>


                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 flex-grow overflow-hidden">
                    {/* Slide Display & Summary Area */}
                    <div className="bg-white rounded-lg shadow-sm overflow-hidden flex flex-col">
                        {/* Slide Image */}
                        <div className="p-4 flex-grow flex items-center justify-center bg-gray-100 min-h-[300px] md:min-h-[400px]">
                            {currentSlideData?.imageUrl ? <img key={currentSlideData.index} src={currentSlideData.imageUrl} alt={`Slide ${currentSlideIndex + 1}`} className="max-w-full max-h-full object-contain rounded" loading="lazy"/> : <div className="text-gray-500">Slide Image Not Available</div>}
                        </div>

                        {/* --- Summary Section --- */}
                        {/* REMOVED max-h-48 from this div to allow expansion */}
                        <div
                            dir="rtl"
                            className="p-4 border-t border-gray-200 bg-gray-50 flex-shrink-0 min-h-[8rem] overflow-y-auto custom-scrollbar relative"
                         >
                            <div className="flex justify-between items-center mb-2 sticky top-0 bg-gray-50 py-1 z-10">
                                <h3 className="text-md font-semibold flex items-center text-gray-700">
                                   <FileText className="w-5 h-5 ml-2"/>
                                   סיכום שקופית
                                </h3>
                                {/* Show Summarize button if applicable */}
                                {showSummarizeButton && (
                                   <button
                                       onClick={handleSummarizeClick}
                                       disabled={!canSummarize}
                                       className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center transition-opacity duration-200"
                                   >
                                       <Sparkles className="w-3 h-3 mr-1" />
                                       צור סיכום
                                   </button>
                                )}
                                 {/* Show loading state specifically for the button when needed */}
                                {isSummarizing && (
                                      <button
                                        disabled={true}
                                        className="px-3 py-1 text-xs bg-gray-400 text-white rounded-md cursor-wait flex items-center"
                                    >
                                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                        מעבד...
                                    </button>
                                )}
                            </div>

                            {/* Display Summary Error */}
                            {summaryError && !isSummarizing && (
                               <div className="text-red-600 text-sm p-2 bg-red-50 rounded my-2">
                                  <strong>שגיאה:</strong> {summaryError}
                               </div>
                            )}

                            {/* Display Existing Summary */}
                            {currentSlideData?.summary && !isSummarizing && (
                                <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                                   {currentSlideData.summary}
                                </p>
                            )}

                             {/* Placeholder if no summary and button not shown/clicked/loading */}
                            {!currentSlideData?.summary && !showSummarizeButton && !isSummarizing && !summaryError && (
                                <p className="text-sm text-gray-500 italic mt-2">
                                    {lecture.status === 'completed' ? "(לחץ על 'צור סיכום' כדי ליצור סיכום עבור שקופית זו)" : "(סיכום יהיה זמין לאחר השלמת העיבוד ולחיצה על הכפתור)"}
                                </p>
                            )}

                        </div>
                        {/* --- End Summary Section --- */}

                    </div> {/* End Slide Display & Summary Area */}


                    {/* Transcription Panel Area */}
                    <div className="bg-white rounded-lg shadow-sm flex flex-col overflow-hidden">
                         <h2 className="text-lg md:text-xl font-semibold p-4 border-b text-right flex-shrink-0"> תמלול שקופית {currentSlideIndex + 1} </h2>
                        <div dir="rtl" className="space-y-1 overflow-y-auto flex-grow p-4 custom-scrollbar">
                           {slideTranscriptions.length > 0 ? ( slideTranscriptions.map((segment) => ( <div key={segment.id} className="flex items-start p-2 hover:bg-gray-50 rounded text-sm md:text-base"> <span className="ml-3 text-xs text-gray-500 whitespace-nowrap pt-1"> {formatTime(segment.startTime)} </span> <p className="text-gray-800 flex-1 text-right leading-relaxed"> {segment.text} </p> </div> )) ) : ( lecture.status === 'completed' || lecture.status === 'failed' ? ( <div className="text-center text-gray-500 py-10"> אין תמלול זמין עבור שקופית זו. </div> ) : ( <div className="text-center text-gray-500 py-10 flex flex-col items-center"> <Loader2 className="w-5 h-5 animate-spin mb-2" /> <span>התמלול נוצר כעת...</span> </div> ) )}
                        </div>
                    </div> {/* End Transcription Panel Area */}

                </div> {/* End Main Content Grid */}
            </div> {/* End Max Width Container */}
        </div> // End Page Container
    );
};

export default LectureViewPage;

// Scrollbar styles (can be kept or moved)
const styles = `
.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #ccc; border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #aaa; }
.custom-scrollbar { scrollbar-width: thin; scrollbar-color: #ccc #f1f1f1; }
`;
const styleSheet = document.createElement("style");
styleSheet.type = "text/css";
styleSheet.innerText = styles;
document.head.appendChild(styleSheet);