# app/services/slide_matching.py
import cv2
import numpy as np
import io
import base64
from typing import List, Dict, Any, Tuple, Optional
import logging
import time
import traceback

logger = logging.getLogger(__name__)

class SlideMatchingService:
    def __init__(self):
        # Configuration parameters - MODIFIED for better detection
        self.frame_interval = 3  # Check more frequently for slide changes
        self.min_inliers = 3  # Reduced for more permissive matching
        self.inlier_threshold = 4.0  # Slightly more generous threshold
        self.good_match_percent = 0.1  # Increased percentage
        self.min_confidence = 0.08  # Reduced to detect more transitions
        
        # Initialize feature detectors and matchers
        # ORB is faster than SIFT and works well for slides
        self.detector = cv2.ORB_create(nfeatures=4000)
        
        # BRISK is another good alternative with more features but still fast
        self.brisk_detector = cv2.BRISK_create()
        
        # For challenging matches, we'll also use SIFT as a fallback
        try:
            self.sift = cv2.SIFT_create(nfeatures=1750)
            self.has_sift = True
        except:
            self.has_sift = False
            logger.warning("SIFT detector not available - missing opencv-contrib-python")
        
        # Create feature matchers
        self.bf_matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        self.flann_matcher = cv2.FlannBasedMatcher({'algorithm': 0, 'trees': 5}, {'checks': 50})

    async def match_transcription_to_slides(
        self,
        video_path: str,
        slides: List[Dict[str, Any]],
        transcription_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Match transcription segments to slides based on video content analysis.
        Uses multiple advanced algorithms to handle different viewing angles and conditions.
        """
        try:
            # Add debug logging
            logger.info(f"Starting slide matching with {len(slides)} slides and {len(transcription_segments)} segments")
            
            # Convert base64 slides to images
            slide_images = []
            for slide in slides:
                # Remove data:image/png;base64, prefix if present
                image_data = slide['image_data'].split(',')[-1]
                image_bytes = base64.b64decode(image_data)
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is not None:
                    slide_images.append(img)
                else:
                    logger.warning(f"Failed to decode slide {slide['index']}")
            
            if not slide_images:
                logger.error("No valid slide images found")
                return [{**segment, 'slide_index': 0} for segment in transcription_segments]
                
            # Extract features from slides - precompute to save time
            slide_features = self._precompute_slide_features(slide_images)
            
            # Process video
            timeline = await self._process_video(video_path, slide_images, slide_features)
            
            # FALLBACK STRATEGY: If no transitions detected, create artificial ones
            if len(timeline) <= 1 and len(slide_images) > 1:
                logger.warning("No slide transitions detected - creating evenly distributed timeline")
                
                # Estimate total duration from transcription
                if transcription_segments:
                    max_time = max(segment['end_time'] for segment in transcription_segments)
                    logger.info(f"Estimated video duration: {max_time:.2f} seconds")
                    
                    # Distribute slides evenly throughout the duration
                    time_per_slide = max_time / len(slide_images)
                    
                    # Clear existing timeline and create a new one
                    timeline = [{'time': 0, 'slide_index': 0}]
                    
                    # Add transitions for remaining slides
                    for i in range(1, len(slide_images)):
                        timeline.append({
                            'time': i * time_per_slide, 
                            'slide_index': i
                        })
                        
                    logger.info(f"Created evenly distributed timeline with {len(timeline)} points")
            
            # Log the timeline for debugging
            logger.info(f"Generated timeline with {len(timeline)} points: {timeline}")
            
            # Match transcription segments to slides using timeline
            matched_segments = []
            for segment in transcription_segments:
                slide_index = self._find_slide_for_timestamp(segment['start_time'], timeline)
                matched_segments.append({
                    **segment,
                    'slide_index': slide_index
                })
            
            # Log the distribution of segments across slides
            segment_distribution = {}
            for segment in matched_segments:
                slide_idx = segment['slide_index']
                if slide_idx not in segment_distribution:
                    segment_distribution[slide_idx] = 0
                segment_distribution[slide_idx] += 1
                
            logger.info(f"Segment distribution across slides: {segment_distribution}")
                
            return matched_segments
                
        except Exception as e:
            logger.error(f"Error in slide matching: {str(e)}")
            logger.error(traceback.format_exc())
            # If anything fails, assign everything to the first slide
            return [{**segment, 'slide_index': 0} for segment in transcription_segments]

    def _precompute_slide_features(self, slide_images: List[np.ndarray]) -> List[Dict[str, Any]]:
        """Precompute features for all slides using multiple algorithms for robustness."""
        slide_features = []
        
        for idx, slide in enumerate(slide_images):
            # Convert to grayscale for feature detection
            gray = cv2.cvtColor(slide, cv2.COLOR_BGR2GRAY)
            
            # Perform basic preprocessing
            preprocessed = self._preprocess_image(gray)
            
            # Extract features using multiple algorithms for robustness
            features = {}
            
            # Primary: ORB features (fast and good for document-like images)
            orb_keypoints, orb_descriptors = self.detector.detectAndCompute(preprocessed, None)
            features['orb'] = {
                'keypoints': orb_keypoints,
                'descriptors': orb_descriptors
            }
            
            # Secondary: BRISK features (more features, still fast)
            brisk_keypoints, brisk_descriptors = self.brisk_detector.detectAndCompute(preprocessed, None)
            features['brisk'] = {
                'keypoints': brisk_keypoints,
                'descriptors': brisk_descriptors
            }
            
            # Fallback: SIFT features (slower but more robust)
            if self.has_sift:
                sift_keypoints, sift_descriptors = self.sift.detectAndCompute(preprocessed, None)
                features['sift'] = {
                    'keypoints': sift_keypoints,
                    'descriptors': sift_descriptors
                }
            
            slide_features.append({
                'index': idx,
                'features': features,
                'image': preprocessed  # Keep preprocessed image for template matching fallback
            })
            
            logger.info(f"Slide {idx}: Extracted {len(orb_keypoints)} ORB features, "
                        f"{len(brisk_keypoints)} BRISK features")
            
        return slide_features

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image to enhance features."""
        try:
            # Make sure we're working with grayscale
            if len(image.shape) > 2:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
                
            # Normalize brightness and increase contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Apply slight blur to reduce noise
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
            
            return blurred
        except Exception as e:
            logger.error(f"Error in preprocessing: {str(e)}")
            return image  # Return original image if preprocessing fails

    async def _process_video(
    self, 
    video_path: str, 
    slide_images: List[np.ndarray],
    slide_features: List[Dict[str, Any]]
) -> List[Dict[str, float]]:
        """Process video and detect slide transitions."""
        timeline = [{'time': 0, 'slide_index': 0}]  # Start with the first slide
        
        try:
            # Check if it's a URL or local file
            if video_path.startswith(('http://', 'https://')):
                logger.info(f"URL video detected. Creating estimated timeline for slides.")
                
                # For URL videos, we can't easily detect transitions with OpenCV,
                # so we'll create an estimated timeline based on number of slides
                num_slides = len(slide_images)
                
                if num_slides > 1:
                    # Estimate each slide gets equal time (basic fallback approach)
                    estimated_duration = 1200  # Assume 20 minutes if we don't know
                    time_per_slide = estimated_duration / (num_slides - 1)
                    
                    # Create timeline entries for each slide
                    for i in range(1, num_slides):
                        timeline.append({
                            'time': i * time_per_slide,
                            'slide_index': i
                        })
                        
                    logger.info(f"Created estimated timeline with {len(timeline)} points for {num_slides} slides")
                
                return timeline
                
            # Original code for local video files with modified parameters
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video: {video_path}")
                return timeline
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_step = max(1, int(fps * self.frame_interval))
            
            logger.info(f"Video FPS: {fps}, Total frames: {total_frames}, Frame step: {frame_step}")
            
            # Track current slide to detect changes
            current_slide_index = 0
            same_slide_count = 0
            last_detected_time = 0
            
            # Process frames at regular intervals
            frame_idx = 0
            last_logging_time = time.time()
            
            # IMPROVEMENT: Sample frames more dynamically for very long videos
            if total_frames > 10000:
                # For long videos, increase step to process a reasonable number of frames
                adaptive_step = max(frame_step, total_frames // 2000)
                logger.info(f"Long video detected, using adaptive step of {adaptive_step}")
                frame_step = adaptive_step
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Process every Nth frame
                if frame_idx % frame_step == 0:
                    # Convert to grayscale
                    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    frame_preprocessed = self._preprocess_image(frame_gray)
                    
                    # Find matching slide using hierarchical approach
                    best_match_idx, confidence = self._find_matching_slide(
                        frame_preprocessed, 
                        slide_features
                    )
                    
                    # Only accept a match if it meets our confidence threshold
                    if confidence >= self.min_confidence:
                        # Detect slide change
                        current_time = frame_idx / fps
                        time_since_last_detection = current_time - last_detected_time
                        
                        # MODIFIED: Be more permissive in accepting slide changes
                        # Only accept a new slide if either:
                        # 1. It's a different slide from current AND
                        # 2. Either it's been at least 1 second since last change OR the confidence is above threshold
                        if (best_match_idx != current_slide_index and 
                            (time_since_last_detection >= 1.0 or confidence > 0.4)):
                            
                            logger.info(f"Slide change at {current_time:.2f}s: {current_slide_index} -> "
                                        f"{best_match_idx} (confidence: {confidence:.2f})")
                            
                            timeline.append({
                                'time': current_time,
                                'slide_index': best_match_idx
                            })
                            
                            current_slide_index = best_match_idx
                            last_detected_time = current_time
                            same_slide_count = 0
                        elif best_match_idx == current_slide_index:
                            same_slide_count += 1
                            
                            # IMPROVEMENT: Occasionally log confidence for current slide
                            if same_slide_count % 30 == 0:
                                logger.debug(f"Same slide at {current_time:.2f}s: {current_slide_index} "
                                            f"(confidence: {confidence:.2f})")
                    
                # Log progress every 30 seconds to show we're still processing
                current_time = time.time()
                if current_time - last_logging_time > 30:
                    progress = (frame_idx / total_frames) * 100 if total_frames > 0 else 0
                    logger.info(f"Processing video: {progress:.1f}% complete")
                    last_logging_time = current_time
                    
                frame_idx += 1
                
            cap.release()
            
            # IMPROVEMENT: If only one slide was detected, try iterating with reduced confidence
            if len(timeline) <= 1 and len(slide_images) > 1 and total_frames > 100:
                logger.warning("No transitions detected in first pass, trying with reduced confidence")
                
                # Retry with lower confidence threshold
                lower_confidence = self.min_confidence * 0.6
                cap = cv2.VideoCapture(video_path)
                
                # Sample fewer frames for the second pass to save time
                second_pass_step = frame_step * 3
                
                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    if frame_idx % second_pass_step == 0:
                        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        frame_preprocessed = self._preprocess_image(frame_gray)
                        
                        # Try all slides, not just the next expected one
                        for slide_idx, slide_data in enumerate(slide_features):
                            if slide_idx == 0:  # Skip first slide, already in timeline
                                continue
                                
                            # Try direct template matching for improved detection
                            current_time = frame_idx / fps
                            slide_img = slide_data['image']
                            match_score = self._quick_template_match(frame_preprocessed, slide_img)
                            
                            if match_score > lower_confidence:
                                logger.info(f"Second pass: Detected slide {slide_idx} at {current_time:.2f}s "
                                          f"(score: {match_score:.2f})")
                                
                                # Add to timeline if not too close to existing points
                                too_close = False
                                for point in timeline:
                                    if abs(point['time'] - current_time) < 5.0:
                                        too_close = True
                                        break
                                        
                                if not too_close:
                                    timeline.append({
                                        'time': current_time,
                                        'slide_index': slide_idx
                                    })
                    
                    frame_idx += 1
                    
                cap.release()
                
                # Sort timeline by time
                timeline.sort(key=lambda x: x['time'])
            
            logger.info(f"Video processing complete. Found {len(timeline)} slide transitions.")
            return timeline
            
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            logger.error(traceback.format_exc())
            return timeline
            
    def _quick_template_match(self, frame: np.ndarray, slide: np.ndarray) -> float:
        """Quick template matching for second pass detection."""
        try:
            # Resize slide to match frame dimensions better
            h, w = frame.shape
            slide_h, slide_w = slide.shape
            
            # Determine scale to resize slide
            scale = min(h / slide_h, w / slide_w) * 0.8
            resized_slide = cv2.resize(slide, (int(slide_w * scale), int(slide_h * scale)))
            
            # Make sure resized slide is smaller than frame
            if resized_slide.shape[0] > frame.shape[0] or resized_slide.shape[1] > frame.shape[1]:
                return 0.0
                
            # Use template matching
            result = cv2.matchTemplate(frame, resized_slide, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            return max_val * 0.7  # Normalize score
        except Exception as e:
            logger.error(f"Error in quick template matching: {str(e)}")
            return 0.0

    def _find_matching_slide(
        self, 
        frame: np.ndarray, 
        slide_features: List[Dict[str, Any]]
    ) -> Tuple[int, float]:
        """
        Find the best matching slide using a hierarchical approach:
        1. Try ORB matching first (fast)
        2. If no good match, try BRISK (more features)
        3. If still no good match, try SIFT if available (most robust)
        4. If all fails, fall back to template matching
        """
        # Try feature-based matching first (ORB - fastest)
        best_match_idx, confidence = self._match_with_features(
            frame, slide_features, feature_type='orb'
        )
        
        # If confidence is low, try BRISK features
        if confidence < self.min_confidence:
            brisk_match_idx, brisk_confidence = self._match_with_features(
                frame, slide_features, feature_type='brisk'
            )
            
            if brisk_confidence > confidence:
                best_match_idx, confidence = brisk_match_idx, brisk_confidence
        
        # If still low confidence and SIFT is available, try SIFT
        if confidence < self.min_confidence and self.has_sift:
            sift_match_idx, sift_confidence = self._match_with_features(
                frame, slide_features, feature_type='sift'
            )
            
            if sift_confidence > confidence:
                best_match_idx, confidence = sift_match_idx, sift_confidence
                
        # If still low confidence, try template matching as last resort
        if confidence < self.min_confidence:
            template_match_idx, template_confidence = self._match_with_template(
                frame, slide_features
            )
            
            if template_confidence > confidence:
                best_match_idx, confidence = template_match_idx, template_confidence
                
        return best_match_idx, confidence

    def _match_with_features(
        self, 
        frame: np.ndarray, 
        slide_features: List[Dict[str, Any]],
        feature_type: str = 'orb'
    ) -> Tuple[int, float]:
        """Match using feature detection and homography."""
        best_match_idx = 0
        best_confidence = 0
        
        try:
            # Extract features from the frame
            if feature_type == 'orb':
                frame_keypoints, frame_descriptors = self.detector.detectAndCompute(frame, None)
                matcher = self.bf_matcher
            elif feature_type == 'brisk':
                frame_keypoints, frame_descriptors = self.brisk_detector.detectAndCompute(frame, None)
                matcher = self.bf_matcher
            elif feature_type == 'sift' and self.has_sift:
                frame_keypoints, frame_descriptors = self.sift.detectAndCompute(frame, None)
                matcher = self.flann_matcher
            else:
                return 0, 0
                
            if frame_descriptors is None or len(frame_descriptors) < 10:
                return 0, 0  # Not enough features in the frame
            
            # Check each slide
            for slide_data in slide_features:
                slide_idx = slide_data['index']
                slide_features_dict = slide_data['features']
                
                if feature_type not in slide_features_dict or slide_features_dict[feature_type]['descriptors'] is None:
                    continue
                    
                slide_keypoints = slide_features_dict[feature_type]['keypoints']
                slide_descriptors = slide_features_dict[feature_type]['descriptors']
                
                if len(slide_descriptors) < 10:
                    continue  # Not enough features in the slide
                
                # Match features
                if feature_type in ['orb', 'brisk']:
                    # Use k-nearest neighbors for binary descriptors
                    matches = matcher.knnMatch(frame_descriptors, slide_descriptors, k=2)
                    
                    # Filter good matches using Lowe's ratio test
                    good_matches = []
                    for match_pair in matches:
                        if len(match_pair) >= 2:
                            m, n = match_pair
                            if m.distance < 0.75 * n.distance:
                                good_matches.append(m)
                else:
                    # For SIFT, use ratio test with FLANN matcher
                    matches = matcher.knnMatch(frame_descriptors, slide_descriptors, k=2)
                    good_matches = []
                    for m, n in matches:
                        if m.distance < 0.7 * n.distance:
                            good_matches.append(m)
                
                # Need at least 4 points for homography
                if len(good_matches) < 4:
                    continue
                    
                # Extract locations of matched keypoints
                src_pts = np.float32([frame_keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([slide_keypoints[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                
                # Find homography and its inliers
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, self.inlier_threshold)
                
                if H is None:
                    continue
                    
                # Count inliers
                inliers = mask.ravel().sum()
                
                # Calculate confidence score based on inliers and match ratio
                inlier_ratio = inliers / len(good_matches) if good_matches else 0
                match_ratio = len(good_matches) / min(len(frame_keypoints), len(slide_keypoints))
                confidence = 0.7 * inlier_ratio + 0.3 * match_ratio
                
                # Make sure we have enough inliers
                if inliers >= self.min_inliers and confidence > best_confidence:
                    best_confidence = confidence
                    best_match_idx = slide_idx
            
            return best_match_idx, best_confidence
            
        except Exception as e:
            logger.error(f"Error in feature matching ({feature_type}): {str(e)}")
            return 0, 0

    def _match_with_template(
        self, 
        frame: np.ndarray, 
        slide_features: List[Dict[str, Any]]
    ) -> Tuple[int, float]:
        """
        Fallback template matching method trying multiple scale transformations.
        """
        best_match_idx = 0
        best_score = 0
        
        try:
            # Scales to try - simulate different viewing angles
            scales = [1.0, 0.8, 0.6, 0.5]
            
            for slide_data in slide_features:
                slide_idx = slide_data['index']
                slide_img = slide_data['image']
                
                # Try different scales
                for scale in scales:
                    # Resize slide
                    h, w = slide_img.shape
                    resized_slide = cv2.resize(slide_img, (int(w * scale), int(h * scale)))
                    
                    # Make sure resized slide is smaller than frame
                    if resized_slide.shape[0] > frame.shape[0] or resized_slide.shape[1] > frame.shape[1]:
                        continue
                    
                    # Apply template matching
                    result = cv2.matchTemplate(frame, resized_slide, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    
                    if max_val > best_score:
                        best_score = max_val
                        best_match_idx = slide_idx
            
            # Template matching scores tend to be higher, so normalize
            normalized_score = min(best_score * 0.7, 1.0)
            return best_match_idx, normalized_score
            
        except Exception as e:
            logger.error(f"Error in template matching: {str(e)}")
            return 0, 0

    def _find_slide_for_timestamp(
        self,
        timestamp: float,
        timeline: List[Dict[str, Any]]
    ) -> int:
        """Find the appropriate slide index for a given timestamp."""
        if not timeline:
            return 0
            
        for i in range(len(timeline) - 1):
            if timeline[i]['time'] <= timestamp < timeline[i + 1]['time']:
                return timeline[i]['slide_index']
                
        # If timestamp is after last change, return last slide
        if timestamp >= timeline[-1]['time']:
            return timeline[-1]['slide_index']
            
        # If timestamp is before first change or no match found, return first slide
        return timeline[0]['slide_index']