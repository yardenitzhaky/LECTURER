# app/services/slide_matching.py
import cv2
import numpy as np
from PIL import Image
import io
import base64
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SlideMatchingService:
    def __init__(self):
        self.frame_interval = 1  # Check every second for slide changes
        self.similarity_threshold = 0.7  # Minimum similarity score to consider a match

    async def match_transcription_to_slides(
        self,
        video_path: str,
        slides: List[Dict[str, Any]],
        transcription_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Match transcription segments to slides based on video content analysis.
        If no match is found, assigns to first slide (index 0).
        """
        try:
            # Convert base64 slides to OpenCV images
            slide_images = []
            for slide in slides:
                # Remove data:image/png;base64, prefix if present
                image_data = slide['image_data'].split(',')[-1]
                image_bytes = base64.b64decode(image_data)
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                slide_images.append(img)

            if not slide_images:
                # If no slides, assign everything to index 0
                return [{**segment, 'slide_index': 0} for segment in transcription_segments]

            # Process video frames
            try:
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    logger.error("Could not open video file")
                    return [{**segment, 'slide_index': 0} for segment in transcription_segments]

                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_interval_frames = int(fps * self.frame_interval)
                
                # Initialize timeline of slide changes
                timeline = []
                frame_count = 0
                current_slide_index = 0
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    if frame_count % frame_interval_frames == 0:
                        # Check for slide change
                        best_match_index, similarity_score = self._find_best_matching_slide(frame, slide_images)
                        
                        # Only record changes if we have a good match
                        if similarity_score >= self.similarity_threshold:
                            if best_match_index != current_slide_index:
                                timestamp = frame_count / fps
                                timeline.append({
                                    'time': timestamp,
                                    'slide_index': best_match_index
                                })
                                current_slide_index = best_match_index
                            
                    frame_count += 1
                    
                cap.release()

                # Match transcription segments to slides using timeline
                matched_segments = []
                for segment in transcription_segments:
                    slide_index = self._find_slide_for_timestamp(segment['start_time'], timeline)
                    matched_segments.append({
                        **segment,
                        'slide_index': slide_index if slide_index is not None else 0
                    })
                    
                return matched_segments

            except Exception as video_error:
                logger.error(f"Error processing video: {str(video_error)}")
                return [{**segment, 'slide_index': 0} for segment in transcription_segments]
                
        except Exception as e:
            logger.error(f"Error in slide matching: {str(e)}")
            # If anything fails, assign everything to the first slide
            return [{**segment, 'slide_index': 0} for segment in transcription_segments]

    def _find_best_matching_slide(self, frame: np.ndarray, slide_images: List[np.ndarray]) -> tuple[int, float]:
        """Find the best matching slide for a given frame and return its index and similarity score."""
        best_match_score = float('-inf')
        best_match_index = 0
        
        # Resize frame to match slide dimensions for comparison
        frame_resized = cv2.resize(frame, (slide_images[0].shape[1], slide_images[0].shape[0]))
        
        for idx, slide in enumerate(slide_images):
            # Calculate similarity score using structural similarity index
            score = self._calculate_similarity(frame_resized, slide)
            
            if score > best_match_score:
                best_match_score = score
                best_match_index = idx
                
        return best_match_index, best_match_score

    def _calculate_similarity(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculate similarity between two images."""
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            
            # Calculate histogram similarity
            hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
            
            score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return score
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return -float('inf')

    def _find_slide_for_timestamp(
        self,
        timestamp: float,
        timeline: List[Dict[str, Any]]
    ) -> int:
        """Find the appropriate slide index for a given timestamp. Returns 0 if no match found."""
        if not timeline:
            return 0
            
        for i in range(len(timeline) - 1):
            if timeline[i]['time'] <= timestamp < timeline[i + 1]['time']:
                return timeline[i]['slide_index']
                
        # If timestamp is after last change, return last slide
        if timestamp >= timeline[-1]['time']:
            return timeline[-1]['slide_index']
            
        # If timestamp is before first change or no match found, return first slide
        return 0