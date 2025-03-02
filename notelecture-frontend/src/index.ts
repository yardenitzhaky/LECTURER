// src/index.ts
export interface TranscriptionSegment {
  id: string;
  startTime: number;
  endTime: number;
  text: string;
  confidence: number;
  slideIndex: number;
}

export interface Slide {
  imageUrl: string;
  index: number;
}

export interface Lecture {
  lecture_id: number;  // Changed from id to match backend
  title: string;
  status: string;
  slides: Slide[];     // Simplified slides interface
  transcription: TranscriptionSegment[];
}

export interface UploadResponse {
  lecture_id: number;  // Changed from lectureId to match backend
  message: string;
}

export interface APIError {
  detail: string;
}