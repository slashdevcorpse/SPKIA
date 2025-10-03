"""
Enhanced AI Detection Methods
Improves accuracy when primary deepfake detection fails or is inconclusive
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger(__name__)


class CompressionArtifactAnalyzer:
    """
    Analyze compression artifacts and image quality metrics
    
    AI-generated images often have:
    - Unusual compression patterns
    - Unnaturally smooth regions
    - Lack of realistic noise
    - Perfect symmetry in unnatural ways
    """
    
    def analyze(self, image_path: Path) -> float:
        """
        Analyze compression artifacts
        
        Returns:
            Score 0-1 where 1 = likely AI-generated
        """
        try:
            # Read image
            if image_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']:
                # Extract first frame from video
                cap = cv2.VideoCapture(str(image_path))
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    return 0.5
                img_cv = frame
            else:
                img_cv = cv2.imread(str(image_path))
                if img_cv is None:
                    return 0.5
            
            # Convert to grayscale
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Analyze multiple factors
            smoothness_score = self._analyze_smoothness(gray)
            edge_score = self._analyze_edges(gray)
            noise_score = self._analyze_noise(gray)
            symmetry_score = self._analyze_symmetry(gray)
            
            # Combine scores
            ai_score = (
                smoothness_score * 0.3 +
                edge_score * 0.3 +
                noise_score * 0.25 +
                symmetry_score * 0.15
            )
            
            logger.info(f"Compression analysis - Smoothness: {smoothness_score:.2f}, "
                       f"Edges: {edge_score:.2f}, Noise: {noise_score:.2f}, "
                       f"Symmetry: {symmetry_score:.2f}, Final: {ai_score:.2f}")
            
            return ai_score
            
        except Exception as e:
            logger.error(f"Compression artifact analysis error: {e}", exc_info=True)
            return 0.5
    
    def _analyze_smoothness(self, gray: np.ndarray) -> float:
        """
        AI images often have unnaturally smooth regions
        Real photos have more texture variation
        """
        # Calculate local variance
        kernel_size = 5
        mean = cv2.blur(gray.astype(np.float32), (kernel_size, kernel_size))
        mean_sq = cv2.blur((gray.astype(np.float32) ** 2), (kernel_size, kernel_size))
        variance = mean_sq - mean ** 2
        
        # AI images have lower average variance (smoother)
        avg_variance = np.mean(variance)
        
        # Normalize (typical real photos: 200-1000, AI: 50-300)
        if avg_variance < 100:
            return 0.8  # Very smooth = likely AI
        elif avg_variance < 200:
            return 0.6
        elif avg_variance < 400:
            return 0.3
        else:
            return 0.1  # High variance = likely real
    
    def _analyze_edges(self, gray: np.ndarray) -> float:
        """
        AI images often have crisp, perfect edges
        Real photos have more natural edge blur and noise
        """
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Calculate edge sharpness
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(sobelx**2 + sobely**2)
        avg_edge_strength = np.mean(edge_magnitude[edge_magnitude > 10])
        
        # AI images tend to have very sharp, defined edges
        if avg_edge_strength > 80 and edge_density < 0.15:
            return 0.7  # Sharp edges, low density = likely AI
        elif avg_edge_strength > 60:
            return 0.5
        else:
            return 0.2
    
    def _analyze_noise(self, gray: np.ndarray) -> float:
        """
        Real photos have sensor noise
        AI images often have no noise or synthetic noise patterns
        """
        # Estimate noise using high-frequency components
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        noise_estimate = np.var(laplacian)
        
        # AI images have very low noise
        if noise_estimate < 10:
            return 0.8  # Almost no noise = likely AI
        elif noise_estimate < 50:
            return 0.6
        elif noise_estimate < 200:
            return 0.3
        else:
            return 0.1  # High noise = likely real camera
    
    def _analyze_symmetry(self, gray: np.ndarray) -> float:
        """
        Some AI generators create unnaturally symmetric images
        """
        h, w = gray.shape
        
        # Check vertical symmetry
        left_half = gray[:, :w//2]
        right_half = np.fliplr(gray[:, w//2:w//2 + left_half.shape[1]])
        
        # Resize if needed
        if left_half.shape != right_half.shape:
            min_w = min(left_half.shape[1], right_half.shape[1])
            left_half = left_half[:, :min_w]
            right_half = right_half[:, :min_w]
        
        # Calculate correlation
        correlation = np.corrcoef(left_half.flatten(), right_half.flatten())[0, 1]
        
        # Perfect symmetry is suspicious
        if correlation > 0.95:
            return 0.9  # Nearly perfect symmetry = likely AI
        elif correlation > 0.85:
            return 0.6
        else:
            return 0.1


class VideoConsistencyAnalyzer:
    """
    Analyze temporal consistency in videos
    
    Deepfakes often have:
    - Inconsistent lighting across frames
    - Face position jitter
    - Color shifts
    - Blending artifacts at boundaries
    """
    
    def analyze(self, video_path: Path, max_frames: int = 30) -> float:
        """
        Analyze video temporal consistency
        
        Returns:
            Score 0-1 where 1 = likely deepfake
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.warning(f"Could not open video: {video_path}")
                return 0.5
            
            # Extract frames uniformly
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                cap.release()
                return 0.5
            
            frame_indices = np.linspace(0, total_frames - 1, min(max_frames, total_frames), dtype=int)
            
            frames = []
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
            
            cap.release()
            
            if len(frames) < 2:
                return 0.5
            
            # Analyze consistency
            color_consistency = self._analyze_color_consistency(frames)
            motion_consistency = self._analyze_motion_consistency(frames)
            
            ai_score = (color_consistency * 0.6 + motion_consistency * 0.4)
            
            logger.info(f"Video consistency - Color: {color_consistency:.2f}, "
                       f"Motion: {motion_consistency:.2f}, Final: {ai_score:.2f}")
            
            return ai_score
            
        except Exception as e:
            logger.error(f"Video consistency analysis error: {e}", exc_info=True)
            return 0.5
    
    def _analyze_color_consistency(self, frames: List[np.ndarray]) -> float:
        """
        Deepfakes often have color/lighting shifts between frames
        """
        # Calculate average color for each frame
        avg_colors = []
        for frame in frames:
            avg_color = np.mean(frame, axis=(0, 1))  # Average RGB
            avg_colors.append(avg_color)
        
        avg_colors = np.array(avg_colors)
        
        # Calculate frame-to-frame differences
        diffs = np.diff(avg_colors, axis=0)
        avg_diff = np.mean(np.abs(diffs))
        
        # High differences suggest inconsistency
        if avg_diff > 15:
            return 0.8  # High color shift = likely deepfake
        elif avg_diff > 10:
            return 0.6
        elif avg_diff > 5:
            return 0.3
        else:
            return 0.1
    
    def _analyze_motion_consistency(self, frames: List[np.ndarray]) -> float:
        """
        Detect unnatural motion patterns
        """
        if len(frames) < 3:
            return 0.5
        
        # Calculate optical flow between consecutive frames
        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        flow_magnitudes = []
        
        for i in range(1, len(frames)):
            curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            
            # Calculate dense optical flow
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                0.5, 3, 15, 3, 5, 1.2, 0
            )
            
            # Calculate average flow magnitude
            magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
            avg_magnitude = np.mean(magnitude)
            flow_magnitudes.append(avg_magnitude)
            
            prev_gray = curr_gray
        
        # Check for sudden jumps (deepfake artifacts)
        flow_magnitudes = np.array(flow_magnitudes)
        flow_std = np.std(flow_magnitudes)
        
        # High variation suggests inconsistent motion
        if flow_std > 10:
            return 0.7  # High motion inconsistency = likely deepfake
        elif flow_std > 5:
            return 0.5
        else:
            return 0.2


class EnhancedAIDetector:
    """
    Enhanced AI detection combining multiple methods
    Used when primary deepfake detector is inconclusive
    """
    
    def __init__(self):
        self.compression_analyzer = CompressionArtifactAnalyzer()
        self.video_analyzer = VideoConsistencyAnalyzer()
    
    def analyze(self, file_path: Path) -> Dict[str, float]:
        """
        Run enhanced analysis
        
        Returns:
            Dict with scores from different methods
        """
        results = {}
        
        # Compression artifact analysis (works for images and videos)
        results['compression_artifacts'] = self.compression_analyzer.analyze(file_path)
        
        # Video-specific analysis
        if file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']:
            results['video_consistency'] = self.video_analyzer.analyze(file_path)
        else:
            results['video_consistency'] = None
        
        return results
