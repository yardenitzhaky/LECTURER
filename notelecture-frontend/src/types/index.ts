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
  notes?: string;
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

export interface LectureSummary {
  id: number;
  title: string;
  status: string;
  video_path: string;
  notes?: string;
}

export interface SubscriptionPlan {
  id: number;
  name: string;
  duration_days: number;
  price: number;
  lecture_limit: number;
  description: string;
}

export interface SubscriptionStatus {
  has_subscription: boolean;
  plan_name?: string;
  plan_id?: number;
  start_date?: string;
  end_date?: string;
  lectures_used?: number;
  lectures_limit?: number;
  lectures_remaining?: number;
  days_remaining?: number;
  is_expired?: boolean;
  free_lectures_used?: number;
  free_lectures_remaining?: number;
  free_lectures_limit?: number;
}

export interface UsageStats {
  subscription_type: 'free' | 'premium';
  plan_name?: string;
  lectures_used_this_period?: number;
  lectures_limit?: number;
  lectures_remaining?: number;
  total_lectures_ever: number;
  days_remaining?: number;
  subscription_end?: string;
  free_lectures_used?: number;
  free_lectures_remaining?: number;
  needs_upgrade?: boolean;
}