// src/services/api.ts
import axios from 'axios';
import type { Lecture, UploadResponse, APIError, Slide as SlideType, TranscriptionSegment as SegmentType, SummarizeResponse } from './index';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add request interceptor to include auth token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
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
        formData: FormData
    ): Promise<UploadResponse> {
        try {
            const response = await api.post<UploadResponse>('/api/transcribe/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            return response.data;
        } catch (error: unknown) {
            if (isApiError(error)) {
                throw error.response.data;
            }
            throw new Error('An unexpected error occurred');
        }
    }

    static async getLecture(id: string): Promise<Lecture> {
        try {
            const response = await api.get<any>(`/api/lectures/${id}/transcription`);


            // Map slides, including the new summary field
            const formattedSlides: SlideType[] = (response.data.slides || []).map((slide: any) => ({
                imageUrl: slide.imageUrl,
                index: slide.index,
                summary: slide.summary || undefined, // Map summary, default to undefined if null/missing
            }));

            // Map transcription segments (no change needed here unless backend format changed)
            const formattedSegments: SegmentType[] = (response.data.transcription || []).map((segment: any) => ({
                id: segment.id.toString(),
                startTime: segment.startTime,
                endTime: segment.endTime,
                text: segment.text,
                confidence: segment.confidence,
                slideIndex: segment.slideIndex,
            }));
            

            return {
                lecture_id: parseInt(id),
                title: response.data.title || `Lecture ${id}`,
                status: response.data.status || 'completed',
                slides: response.data.slides || [],
                transcription: formattedSegments,
            };
        } catch (error: unknown) {
            if (isApiError(error)) {
                console.error("API Error fetching lecture:", error.response.data.detail);
                throw error.response.data;
            }
            console.error("Unexpected error fetching lecture:", error);
            throw new Error('An unexpected error occurred');
        }
    }

    static async summarizeSlide(lectureId: string, slideIndex: number, customPrompt?: string): Promise<SummarizeResponse> {
        try {
            const requestBody = customPrompt ? { custom_prompt: customPrompt } : {};
            const response = await api.post<SummarizeResponse>(
                `/api/lectures/${lectureId}/slides/${slideIndex}/summarize`,
                requestBody
            );
            // --- ADD CONSOLE LOG HERE ---
            console.log(`[APIService.summarizeSlide] Raw Response Data (Lecture ${lectureId}, Slide ${slideIndex}):`, response.data);
            console.log(`[APIService.summarizeSlide] FULL Summary Received:\n---\n${response.data.summary}\n---`);
            // --- END CONSOLE LOG ---
            return response.data;
        } catch (error: unknown) {
             // ... (error handling remains the same) ...
             console.error(`Summarize Slide API Error (Lecture ${lectureId}, Slide ${slideIndex}):`, error);
             if (isApiError(error)) { throw new Error(error.response.data.detail || `Failed to summarize slide ${slideIndex}.`); }
             throw new Error(`An unexpected network or server error occurred while summarizing slide ${slideIndex}.`);
        }
    }
}