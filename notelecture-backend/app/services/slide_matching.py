# app/services/slide_matching.py
import base64
import httpx
import json
from typing import List, Dict, Any, Tuple, Optional
import logging
import time
import traceback
import math
from app.core.config import settings

# Check if OpenCV is available
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None
    logging.warning("OpenCV not available - will use external service for slide matching")

logger = logging.getLogger(__name__)

class SlideMatchingService:
    def __init__(self):
        self.frame_interval_seconds = 5 
        self.lowe_ratio = 0.75     
        self.change_confirm_threshold = 2   

        if CV2_AVAILABLE:
            self.detector = cv2.ORB_create(nfeatures=2000)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            logger.info("SlideMatchingService initialized (Simplified - Best Score, ORB Only)")
        else:
            self.detector = None
            self.matcher = None
            logger.info("SlideMatchingService initialized (External Service Mode - OpenCV not available)")

    async def match_transcription_to_slides(
        self,
        video_path_or_url: str,
        slides: List[Dict[str, Any]],
        transcription_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Matches transcription segments to slides using computer vision or external service.
        """
        logger.info(f"Starting slide matching: {len(slides)} slides, {len(transcription_segments)} segments.")
        
        # Try external service first if OpenCV is not available or external service is configured
        if not CV2_AVAILABLE or settings.EXTERNAL_SERVICE_URL:
            try:
                return await self._match_slides_external(video_path_or_url, slides, transcription_segments)
            except Exception as e:
                logger.warning(f"External slide matching failed: {e}")
                if not CV2_AVAILABLE:
                    logger.warning("OpenCV not available, falling back to simple time-based matching")
                    return self._simple_time_based_matching(slides, transcription_segments)
        
        # Fallback to local processing if OpenCV is available
        if CV2_AVAILABLE:
            return await self._match_slides_local(video_path_or_url, slides, transcription_segments)
        else:
            logger.warning("No slide matching available, using simple time-based matching")
            return self._simple_time_based_matching(slides, transcription_segments)

    async def _match_slides_external(self, video_path_or_url: str, slides: List[Dict[str, Any]], transcription_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match slides using external service."""
        if not settings.EXTERNAL_SERVICE_URL:
            raise Exception("External service URL not configured")
        
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                # Prepare video file
                if video_path_or_url.startswith(('http://', 'https://')):
                    # For URLs, we can't send the video file directly
                    logger.warning("URL video detected for external service. Using simple time-based matching.")
                    return self._simple_time_based_matching(slides, transcription_segments)
                
                # Read video file
                with open(video_path_or_url, 'rb') as video_file:
                    files = {"video_file": (video_path_or_url, video_file, "video/mp4")}
                    data = {
                        "slides_data": json.dumps(slides),
                        "transcription_data": json.dumps(transcription_segments)
                    }
                    headers = {}
                    if settings.EXTERNAL_SERVICE_API_KEY:
                        headers["Authorization"] = f"Bearer {settings.EXTERNAL_SERVICE_API_KEY}"
                    
                    response = await client.post(
                        f"{settings.EXTERNAL_SERVICE_URL}/match-slides/",
                        files=files,
                        data=data,
                        headers=headers
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    matches = result.get("matches", [])
                    logger.info(f"External service returned {len(matches)} slide matches")
                    
                    # Apply matches to segments
                    matched_segments = []
                    for segment in transcription_segments:
                        # Find the best match for this segment based on time
                        best_slide = 0
                        for match in matches:
                            if (match["start_time"] <= segment["start_time"] <= match["end_time"]):
                                best_slide = match["slide_index"]
                                break
                        
                        matched_segments.append({**segment, 'slide_index': best_slide})
                    
                    return matched_segments
                    
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling external slide matching service: {e}")
            raise Exception(f"External slide matching failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling external slide matching service: {e}")
            raise

    def _simple_time_based_matching(self, slides: List[Dict[str, Any]], transcription_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple time-based slide matching as fallback."""
        logger.info("Using simple time-based slide matching")
        matched_segments = []
        
        if not slides or not transcription_segments:
            return [{**segment, 'slide_index': 0} for segment in transcription_segments]
        
        # Calculate duration per slide
        max_time = max(segment.get('end_time', 0) for segment in transcription_segments)
        time_per_slide = max_time / len(slides) if len(slides) > 0 else max_time
        
        for segment in transcription_segments:
            start_time = segment.get('start_time', 0)
            slide_index = min(int(start_time / time_per_slide) if time_per_slide > 0 else 0, len(slides) - 1)
            matched_segments.append({**segment, 'slide_index': slide_index})
        
        return matched_segments

    async def _match_slides_local(self, video_path_or_url: str, slides: List[Dict[str, Any]], transcription_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Local slide matching using OpenCV (original implementation)."""
        matched_segments = []

        try:
            # 1. Decode Slides
            slide_images_decoded = []
            for i, slide in enumerate(slides):
                try:
                    image_data = slide['image_data'].split(',')[-1]
                    image_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE) # Load as grayscale
                    if img is not None:
                        slide_images_decoded.append({'index': slide['index'], 'image': img})
                    else:
                        logger.warning(f"Failed to decode slide index {slide.get('index', i)}")
                except Exception as decode_err:
                     logger.error(f"Error decoding slide index {slide.get('index', i)}: {decode_err}")

            if not slide_images_decoded:
                logger.error("No valid slide images could be decoded. Using simple time-based matching.")
                return self._simple_time_based_matching(slides, transcription_segments)

            # 2. Precompute Slide Features (ORB only)
            logger.info("Precomputing ORB features for slides...")
            slide_features = self._precompute_slide_features_simple(slide_images_decoded)
            if not slide_features:
                 logger.error("Failed to compute features for any slide. Using simple time-based matching.")
                 return self._simple_time_based_matching(slides, transcription_segments)

            # 3. Generate Timeline (Process Video or Estimate for URL)
            logger.info("Generating match timeline by processing video...")
            timeline = await self._process_video_best_score(video_path_or_url, slide_features)

            # 4. Fallback: If processing failed or resulted in only the initial point, estimate.
            if len(timeline) <= 1 and len(slide_images_decoded) > 1:
                 logger.warning("Video processing yielded minimal timeline. Estimating based on transcription duration.")
                 timeline = self._estimate_timeline(transcription_segments, len(slide_images_decoded))

            logger.info(f"FINAL Generated Timeline (Points: {len(timeline)}):")
            for i, point in enumerate(timeline):
                logger.info(f"  Timeline[{i}]: Time={point['time']:.2f}s, SlideIndex={point['slide_index']}")

            # 5. Match Segments to Timeline
            logger.info("Assigning segments to slides based on timeline...")
            segment_distribution = {}
            for segment in transcription_segments:
                slide_index = self._find_slide_for_timestamp(segment['start_time'], timeline)
                matched_segments.append({**segment, 'slide_index': slide_index})
                segment_distribution[slide_index] = segment_distribution.get(slide_index, 0) + 1

            logger.info(f"Segment distribution across slides: {segment_distribution}")
            return matched_segments

        except Exception as e:
            logger.critical(f"CRITICAL error in slide matching process: {e}", exc_info=True)
            logger.critical("FALLBACK: Using simple time-based matching.")
            return self._simple_time_based_matching(slides, transcription_segments)

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Basic preprocessing for feature detection."""
        if len(image.shape) > 2: gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else: gray = image
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        return blurred

    def _precompute_slide_features_simple(self, slides_decoded: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Precomputes ORB features for each slide, without minimum threshold."""
        features_list = []
        for slide_data in slides_decoded:
            try:
                preprocessed = self._preprocess_image(slide_data['image'])
                keypoints, descriptors = self.detector.detectAndCompute(preprocessed, None)
                # Store features even if descriptors are few or None initially
                features_list.append({
                    'index': slide_data['index'],
                    'keypoints': keypoints if keypoints is not None else [],
                    'descriptors': descriptors
                })
                kp_count = len(keypoints) if keypoints is not None else 0
                desc_shape = descriptors.shape if descriptors is not None else "None"
                logger.debug(f"Computed features for slide {slide_data['index']}: Keypoints={kp_count}, Descriptors Shape={desc_shape}")
            except Exception as e:
                 logger.error(f"Error computing features for slide {slide_data['index']}: {e}")
        return features_list

    async def _process_video_best_score(
            self,
            video_path_or_url: str,
            slide_features: List[Dict[str, Any]]
        ) -> List[Dict[str, Any]]:
            """
            Samples video frames, finds highest ORB match score slide, applies temporal smoothing.
            """
            if video_path_or_url.startswith(('http://', 'https://')):
                logger.warning("URL video detected. Cannot process frames. Timeline estimation required.")
                return [{'time': 0, 'slide_index': 0}]

            timeline = [{'time': 0, 'slide_index': 0}] # Start with slide 0 at time 0
            cap = None
            potential_change = {'index': None, 'count': 0} # For temporal smoothing
            confirmed_slide_index = 0 # Tracks the index currently confirmed in the timeline

            try:
                cap = cv2.VideoCapture(video_path_or_url)
                if not cap.isOpened():
                    logger.error(f"Cannot open video file: {video_path_or_url}")
                    return timeline

                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if fps <= 0 or total_frames <= 0:
                    logger.warning(f"Video has invalid FPS ({fps}) or Frame Count ({total_frames}). Cannot process.")
                    return timeline

                frame_step = max(1, int(fps * self.frame_interval_seconds))
                logger.info(f"Processing video: FPS={fps:.2f}, Frames={total_frames}, Step={frame_step}, ConfirmThreshold={self.change_confirm_threshold}")

                processed_frames_count = 0
                last_logged_time = time.time()

                for frame_idx in range(0, total_frames, frame_step):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning(f"Could not read frame {frame_idx}")
                        continue

                    current_time = frame_idx / fps
                    frame_preprocessed = self._preprocess_image(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
                    best_match_idx, best_score = self._find_best_match_score(frame_preprocessed, slide_features, frame_idx)

                    # --- Timeline & Smoothing Logic ---
                    if frame_idx == 0:
                        # Handle the very first frame (t=0)
                        if best_match_idx is not None and best_match_idx != confirmed_slide_index:
                            logger.info(f"Timeline Update at t=0: Frame={frame_idx} -> Replacing initial index 0 with best match: Slide {best_match_idx} (Score: {best_score})")
                            timeline[0]['slide_index'] = best_match_idx
                            confirmed_slide_index = best_match_idx
                            potential_change = {'index': None, 'count': 0} # Reset potential change
                        # If no match or matches index 0, do nothing to the initial entry
                    else:
                        # Handle subsequent frames
                        if best_match_idx is not None:
                            if best_match_idx != confirmed_slide_index:
                                # Potential change detected
                                if best_match_idx == potential_change['index']:
                                    potential_change['count'] += 1
                                    logger.debug(f"Potential Change Confirmed: Time={current_time:.2f}s, Frame={frame_idx} -> Slide {best_match_idx} seen {potential_change['count']} times.")
                                else:
                                    # New potential change starts
                                    logger.debug(f"Potential Change Started: Time={current_time:.2f}s, Frame={frame_idx} -> Slide {best_match_idx} seen 1 time (Score: {best_score}). Resetting from {potential_change['index']}.")
                                    potential_change = {'index': best_match_idx, 'count': 1}

                                # Check if confirmation threshold is met
                                if potential_change['count'] >= self.change_confirm_threshold:
                                    logger.info(f"Timeline Change CONFIRMED: Time={current_time:.2f}s, Frame={frame_idx} -> Adding Slide {best_match_idx} (Confirmed {potential_change['count']} times)")
                                    timeline.append({'time': current_time, 'slide_index': best_match_idx})
                                    confirmed_slide_index = best_match_idx
                                    potential_change = {'index': None, 'count': 0} # Reset after confirmation

                            else: # Best match is the same as the confirmed slide
                                if potential_change['index'] is not None:
                                    logger.debug(f"Potential Change Reset: Time={current_time:.2f}s, Frame={frame_idx} -> Best match {best_match_idx} is same as confirmed. Resetting potential {potential_change['index']}.")
                                potential_change = {'index': None, 'count': 0} # Reset potential change
                        else: # No match found for this frame
                            if potential_change['index'] is not None:
                                logger.debug(f"Potential Change Reset: Time={current_time:.2f}s, Frame={frame_idx} -> No match found. Resetting potential {potential_change['index']}.")
                            potential_change = {'index': None, 'count': 0} # Reset potential change

                    processed_frames_count += 1
                    current_logged_time = time.time()
                    if current_logged_time - last_logged_time > 30:
                        progress_percent = (frame_idx / total_frames) * 100 if total_frames > 0 else 0
                        logger.info(f"Video processing progress: {progress_percent:.1f}% (Frame {frame_idx}/{total_frames})")
                        last_logged_time = current_logged_time

                logger.info(f"Finished processing {processed_frames_count} video frames.")
                timeline.sort(key=lambda x: x['time']) # Ensure sorted
                return timeline

            except Exception as e:
                logger.error(f"Error during video processing: {e}", exc_info=True)
                return timeline
            finally:
                if cap:
                    cap.release()

    def _find_best_match_score(
        self,
        frame_preprocessed: np.ndarray,
        slide_features: List[Dict[str, Any]],
        frame_idx: int # Added for logging context
    ) -> Tuple[Optional[int], int]:
        """
        Finds the slide with the highest number of good ORB feature matches to the frame.
        Returns (best_slide_index, max_good_matches_count).
        Returns (None, 0) if no matches are found for any slide.
        Logs detailed match counts per slide.
        """
        best_match_idx = None
        max_good_matches = 0 # Start with 0, any match is potentially the best

        try:
            frame_kp, frame_desc = self.detector.detectAndCompute(frame_preprocessed, None)

            # If frame has no descriptors, no matches are possible
            if frame_desc is None:
                logger.debug(f"Frame {frame_idx}: No keypoints/descriptors found in frame.")
                return None, 0

            logger.debug(f"--- Matching Frame {frame_idx} (Features: {len(frame_kp)}) ---")

            for slide_data in slide_features:
                slide_idx = slide_data['index']
                slide_desc = slide_data['descriptors']
                slide_kp_count = len(slide_data['keypoints'])

                # Skip slide if it has no descriptors
                if slide_desc is None:
                     logger.debug(f"  Slide {slide_idx}: Skipped (No descriptors precomputed).")
                     continue

                good_matches_count = 0
                try:
                    # KNN Match
                    matches = self.matcher.knnMatch(frame_desc, slide_desc, k=2)

                    # Apply Lowe's ratio test
                    for match_pair in matches:
                        if len(match_pair) == 2:
                             m, n = match_pair
                             if m.distance < self.lowe_ratio * n.distance:
                                 good_matches_count += 1

                    # --- DETAILED MATCH LOGGING ---
                    logger.debug(f"  Slide {slide_idx}: Found {good_matches_count} good matches (Slide KP: {slide_kp_count}, Frame KP: {len(frame_kp)}).")
                    # --- END DETAILED MATCH LOGGING ---

                    # Update best match if current slide has more good matches
                    if good_matches_count > max_good_matches:
                        max_good_matches = good_matches_count
                        best_match_idx = slide_idx

                except cv2.error as cv_err:
                     # Handle potential errors during the matching process for a specific pair
                     logger.warning(f"  Slide {slide_idx}: OpenCV error during matching: {cv_err}. Skipping comparison.")
                     continue # Skip to the next slide
                except Exception as match_err:
                     logger.warning(f"  Slide {slide_idx}: Unexpected error during matching: {match_err}. Skipping comparison.")
                     continue # Skip to the next slide


            logger.debug(f"--- Frame {frame_idx} Best Match Result: Index={best_match_idx}, Score(GoodMatches)={max_good_matches} ---")

            # Return None if no good matches were found for ANY slide
            if max_good_matches == 0:
                return None, 0
            else:
                return best_match_idx, max_good_matches

        except Exception as e:
            logger.error(f"Error finding best match for frame {frame_idx}: {e}", exc_info=True)
            return None, 0 # Indicate error / no match

    def _estimate_timeline(self, transcription_segments: List[Dict[str, Any]], num_slides: int) -> List[Dict[str, Any]]:
        """Estimates a timeline by distributing slides evenly over transcription duration."""
        if not transcription_segments or num_slides <= 1:
            return [{'time': 0, 'slide_index': 0}]
        try:
             max_time = max(segment['end_time'] for segment in transcription_segments if 'end_time' in segment and segment['end_time'] is not None)
             if max_time <= 0: max_time = 600 # Default if max time is invalid
        except (ValueError, TypeError):
             max_time = 600 # Default to 10 minutes if no valid end times
        logger.info(f"Estimating timeline based on max transcription time: {max_time:.2f}s for {num_slides} slides.")
        time_per_slide = max_time / num_slides
        timeline = [{'time': i * time_per_slide, 'slide_index': i} for i in range(num_slides)]
        logger.info(f"Created estimated timeline with {len(timeline)} points.")
        return timeline


    def _find_slide_for_timestamp(self, timestamp: float, timeline: List[Dict[str, Any]]) -> int:
        """Finds the slide index active at a given timestamp based on the timeline."""
        if not timeline: return 0
        active_slide_index = timeline[0]['slide_index']
        for entry in timeline:
            if entry['time'] <= timestamp:
                active_slide_index = entry['slide_index']
            else: break
        return active_slide_index