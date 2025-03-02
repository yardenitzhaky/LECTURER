// src/services/api.ts
import axios from 'axios';
import type { Lecture, UploadResponse, APIError } from './index';

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
        formData: FormData
    ): Promise<UploadResponse> {
        try {
            const response = await api.post<UploadResponse>('/transcribe/', formData, {
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
            const response = await api.get<any>(`/lectures/${id}/transcription`);
            
            return {
                lecture_id: parseInt(id),
                title: response.data.title || `Lecture ${id}`,
                status: response.data.status || 'completed',
                slides: response.data.slides || [],
                transcription: response.data.transcription.map((segment: any) => ({
                    id: segment.id.toString(),
                    startTime: segment.startTime,
                    endTime: segment.endTime,
                    text: segment.text,
                    confidence: segment.confidence,
                    slideIndex: segment.slideIndex,
                })),
            };
        } catch (error: unknown) {
            if (isApiError(error)) {
                throw error.response.data;
            }
            throw new Error('An unexpected error occurred');
        }
    }
}