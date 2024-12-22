// src/pages/LectureViewPage.tsx
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { APIService } from '../services/api';
import { Lecture, TranscriptionSegment } from '../types/index.ts';
import { formatTime } from '../utils/format';

export const LectureViewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [lecture, setLecture] = useState<Lecture | null>(null);

  useEffect(() => {
    const fetchLecture = async () => {
      if (!id) return;
      try {
        const lectureData = await APIService.getLecture(id);
        setLecture(lectureData);
      } catch (error) {
        console.error('Error fetching lecture:', error);
      }
    };

    fetchLecture();
  }, [id]);

  return (
    <div className="min-h-screen flex flex-col">
        {/* Presentation Section */}
        <div className="flex-1 bg-gray-100 p-4">
            <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-sm p-4">
                {lecture?.slides[0]?.imageUrl ? (
                    <img 
                        src={lecture.slides[0].imageUrl} 
                        alt="Presentation slide"
                        className="w-full h-full object-contain"
                    />
                ) : (
                    <div className="w-full h-64 bg-gray-200 flex items-center justify-center">
                        <p className="text-gray-500">No presentation available</p>
                    </div>
                )}
            </div>
        </div>

        {/* Transcription Section */}
        <div className="bg-white border-t">
            <div className="max-w-4xl mx-auto p-4">
                <h2 className="text-xl font-semibold mb-4">Transcription</h2>
                <div className="bg-gray-50 rounded-lg p-4 space-y-4">
                    {lecture?.transcription.map((segment) => (
                        <div 
                            key={segment.id}
                            className="flex items-start space-x-4 p-2"
                        >
                            <span className="text-sm text-gray-500 whitespace-nowrap">
                                {formatTime(segment.startTime)}
                            </span>
                            <p className="text-gray-700">
                                {segment.text}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    </div>
);
};