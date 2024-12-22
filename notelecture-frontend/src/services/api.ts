import axios from 'axios';
import type { Lecture, UploadResponse, APIError } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:3000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Type guard for error handling
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
        formData.append('video', videoFile);
      } else if (videoUrl) {
        formData.append('videoUrl', videoUrl);
      }
      
      formData.append('presentation', presentationFile);

      const response = await api.post<UploadResponse>('/lectures', formData, {
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
      const response = await api.get<Lecture>(`/lectures/${id}`);
      return response.data;
    } catch (error: unknown) {
      if (isApiError(error)) {
        throw error.response.data;
      }
      throw new Error('An unexpected error occurred');
    }
  }
}