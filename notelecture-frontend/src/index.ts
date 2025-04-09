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
  summary?: string;
}

export interface Lecture {
  lecture_id: number;  
  title: string;
  status: string;
  slides: Slide[];     
  transcription: TranscriptionSegment[];
}

export interface UploadResponse {
  lecture_id: number; 
  message: string;
}

export interface APIError {
  detail: string;
}


export interface SummarizeResponse {
  summary: string | null;
  message?: string; // Optional message for cases like "no text"
}