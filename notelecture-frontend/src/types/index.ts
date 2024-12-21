// src/types/index.ts

export interface Lecture {
    id: string;
    title: string;
    videoUrl: string;
    videoType: 'file' | 'url';
    presentationUrl: string;
    createdAt: string;
    status: 'processing' | 'completed' | 'error';
    slides: Slide[];
    transcription: TranscriptionSegment[];
  }
  
  export interface Slide {
    id: string;
    imageUrl: string;
    pageNumber: number;
    timestamp: number;
    notes: string[];
  }
  
  export interface TranscriptionSegment {
    id: string;
    startTime: number;
    endTime: number;
    text: string;
    slideId: string;
    confidence: number;
  }
  
  export interface UploadResponse {
    lectureId: string;
    status: 'processing';
    estimatedTime: number;
  }
  
  export interface APIError {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  }