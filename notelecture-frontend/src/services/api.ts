// src/services/api.ts
import axios from 'axios';
import type { Lecture, UploadResponse, APIError } from '../types';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

function isApiError(error: unknown): error is { response: { data: APIError } } {
    return (
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        typeof error.response === 'object' &&
        error.response !== null &&
        'data' in error.response
    );
}

export class APIService {
    static async uploadLecture(
        videoFile: File | null,
        presentationFile: File,
        videoUrl?: string
    ): Promise<UploadResponse> {
        try {
            const formData = new FormData();
            if (videoFile) {
                formData.append('file', videoFile);
            } else if (videoUrl) {
                formData.append('video_url', videoUrl);
            }

            const response = await api.post<UploadResponse>('/transcribe/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            return {
                lecture_id: response.data.lecture_id,
                message: response.data.message
            };
        } catch (error: unknown) {
            if (isApiError(error)) {
                throw error.response.data;
            }
            throw new Error('An unexpected error occurred');
        }
    }

    static async getLecture(id: string): Promise<Lecture> {
      try {
          const response = await api.get<any>(`/lectures/${id}/transcription`);
          console.log('Backend response:', response.data); // Add this for debugging
              
          // Transform the FastAPI response to match our frontend types
          const transformedData: Lecture = {
              lecture_id: parseInt(id),
              title: response.data.title || `Lecture ${id}`,
              status: response.data.status || 'completed',
              slides: [
                  {
                      imageUrl: '/placeholder-slide.png'
                  }
              ],
              transcription: response.data.transcription.map((segment: any) => ({
                  id: segment.id.toString(),
                  startTime: segment.startTime,
                  endTime: segment.endTime,
                  text: segment.text,
                  confidence: segment.confidence,
              })),
          };
  
          console.log('Transformed data:', transformedData); // Add this for debugging
          return transformedData;
      } catch (error: unknown) {
          if (isApiError(error)) {
              throw error.response.data;
          }
          console.error('Error details:', error); // Add this for debugging
          throw new Error('An unexpected error occurred');
      }
  }
}