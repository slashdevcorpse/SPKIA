"""
Machine Learning-based AI media detection pipeline
Uses ResNeXt + LSTM for video deepfake detection (based on karthikurao/Deepfake-Detection)
Plus PRNU analysis and metadata forensics
"""
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms

from app.models.database import MLDetectionResult
from app.config import settings
from app.services.deepfake_detector import DeepfakeDetector
from app.services.enhanced_detection import EnhancedAIDetector

logger = logging.getLogger(__name__)


class CNNArtifactDetector:
    """
    ResNeXt + LSTM deepfake detector (video-based temporal analysis)
    Based on: https://github.com/karthikurao/Deepfake-Detection
    
    Uses ResNeXt-50 (32x4d) for spatial features + LSTM for temporal patterns
    Achieves 97.7% accuracy on FaceForensics++ dataset
    """
    
    def __init__(self, model_path: Path):
        """Initialize deepfake detector (lazy loading)"""
        self.model_path = model_path
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Model weights file
        model_file = model_path / f"resnext_lstm_{settings.cnn_model_version}.pth"
        
        # Initialize ResNeXt + LSTM detector
        self.detector = DeepfakeDetector(
            model_path=model_file if model_file.exists() else None,
            device=self.device
        )
        
        logger.info("ResNeXt+LSTM detector initialized (model will load on first use)")
    
    def detect(self, image_path: Path) -> float:
        """
        Detect deepfakes in video or image
        
        Args:
            image_path: Path to image or video file
            
        Returns:
            float: AI probability score (0-1)
                  0 = definitely real
                  1 = definitely AI/deepfake
        """
        try:
            file_ext = image_path.suffix.lower()
            
            # Video formats - use ResNeXt+LSTM temporal analysis
            if file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v']:
                logger.info(f"Analyzing video with ResNeXt+LSTM: {image_path.name}")
                # detect_score returns float (0-1) where 1 = definitely fake
                ai_score = self.detector.detect_score(str(image_path))
                logger.info(f"ResNeXt+LSTM AI score: {ai_score:.3f}")
                return ai_score
            
            # Image formats - single frame analysis
            else:
                logger.info(f"Analyzing image with ResNeXt (single frame): {image_path.name}")
                # detect_score returns float (0-1) where 1 = definitely fake
                ai_score = self.detector.detect_score(str(image_path))
                logger.info(f"ResNeXt AI score: {ai_score:.3f}")
                return ai_score
                    
        except Exception as e:
            logger.error(f"CNN artifact detection error: {e}", exc_info=True)
            return 0.5


class PRNUAnalyzer:
    """
    Photo Response Non-Uniformity (PRNU) pattern analyzer
    
    Real camera sensors have unique noise fingerprints from manufacturing imperfections.
    AI-generated images lack these patterns or have synthetic/incorrect patterns.
    
    NOTE: All scipy dependencies replaced with numpy/PIL for performance
    """
    
    def __init__(self, model_path: Path):
        """Initialize PRNU analyzer"""
        self.model_path = model_path
        self.correlation_threshold = 0.05
        self.reference_patterns = {}
        self._patterns_loaded = False
    
    def _load_reference_patterns(self):
        """Load pre-computed PRNU reference patterns"""
        try:
            pattern_file = self.model_path / f"prnu_patterns_{settings.prnu_model_version}.npz"
            
            if pattern_file.exists():
                data = np.load(pattern_file, allow_pickle=True)
                self.reference_patterns = data['patterns'].item()
                logger.info(f"Loaded {len(self.reference_patterns)} PRNU reference patterns")
            else:
                logger.warning(f"PRNU patterns not found: {pattern_file}")
                # Generate synthetic reference patterns for common camera models
                self._generate_synthetic_patterns()
            
        except Exception as e:
            logger.error(f"Failed to load PRNU patterns: {e}")
            self._generate_synthetic_patterns()
    
    def _generate_synthetic_patterns(self):
        """
        Generate synthetic reference patterns for common camera sensors
        
        In production, these would be extracted from real camera images.
        For now, generating characteristic patterns based on sensor physics.
        """
        try:
            # Common camera sensor sizes and characteristics
            sensor_configs = {
                'iphone_13': {'size': (4032, 3024), 'noise_level': 0.02},
                'iphone_14': {'size': (4032, 3024), 'noise_level': 0.018},
                'canon_eos': {'size': (6000, 4000), 'noise_level': 0.015},
                'nikon_d850': {'size': (8256, 5504), 'noise_level': 0.012},
                'sony_a7': {'size': (6000, 4000), 'noise_level': 0.013},
            }
            
            self.reference_patterns = {}
            for camera, config in sensor_configs.items():
                # Generate fixed-pattern noise characteristic of real sensors
                # Real sensors have spatially correlated noise from photodiode non-uniformity
                np.random.seed(hash(camera) % 2**32)  # Deterministic per camera
                pattern = np.random.randn(512, 512) * config['noise_level']
                
                # Simple spatial correlation using numpy convolution (no scipy)
                # Create simple gaussian-like kernel
                kernel_size = 3
                kernel = np.ones((kernel_size, kernel_size)) / (kernel_size * kernel_size)
                
                # Apply convolution for smoothing
                from numpy.lib.stride_tricks import as_strided
                padded = np.pad(pattern, ((1, 1), (1, 1)), mode='edge')
                strided = as_strided(
                    padded,
                    shape=(pattern.shape[0], pattern.shape[1], kernel_size, kernel_size),
                    strides=padded.strides + padded.strides
                )
                pattern = np.einsum('ijkl,kl->ij', strided, kernel)
                
                self.reference_patterns[camera] = pattern
            
            logger.info(f"Generated {len(self.reference_patterns)} synthetic PRNU patterns")
            
        except Exception as e:
            logger.error(f"Failed to generate PRNU patterns: {e}", exc_info=True)
            # Create minimal patterns as fallback
            self.reference_patterns = {
                'generic': np.random.randn(512, 512) * 0.02
            }
            logger.info("Using minimal fallback PRNU pattern")
    
    def analyze(self, image_path: Path) -> float:
        """
        Analyze sensor noise pattern to determine camera authenticity
        
        Returns:
            Confidence score (0-1) that image is from a real camera sensor.
            High score = strong PRNU pattern (likely real camera)
            Low score = weak/no PRNU pattern (likely AI-generated)
        """
        try:
            # Lazy load patterns on first use
            if not self._patterns_loaded:
                logger.info("Loading PRNU patterns (first use)...")
                self._load_reference_patterns()
                self._patterns_loaded = True
            
            # Extract noise residual from image
            noise_pattern = self._extract_noise_pattern(image_path)
            
            if noise_pattern is None:
                return 0.5  # Uncertain
            
            # Compute PRNU pattern quality metrics
            prnu_strength = self._compute_prnu_strength(noise_pattern)
            
            # Check correlation with known camera patterns
            max_correlation = self._match_reference_patterns(noise_pattern)
            
            # Combine metrics for final score
            # Strong PRNU + high correlation = real camera
            # Weak PRNU + low correlation = AI-generated
            
            if max_correlation > self.correlation_threshold:
                # Strong match with known camera
                score = 0.2 + (max_correlation / 0.1) * 0.3  # 0.2-0.5 range
            else:
                # No match - evaluate PRNU strength
                # Real cameras have PRNU even if not in database
                score = 0.3 + prnu_strength * 0.4  # 0.3-0.7 range
            
            # Clamp to [0, 1]
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"PRNU analysis error: {e}")
            return 0.5
    
    def _compute_prnu_strength(self, noise_pattern: np.ndarray) -> float:
        """
        Compute strength of PRNU pattern
        
        Real camera sensors have non-random spatial structure in noise.
        AI-generated images typically have random or GAN-specific noise patterns.
        """
        try:
            # Measure spatial autocorrelation using numpy (no scipy needed)
            # Compute local variance to detect spatial structure
            h, w = noise_pattern.shape
            
            # Calculate local variance in 5x5 blocks
            block_size = 5
            local_vars = []
            for i in range(0, h - block_size, block_size):
                for j in range(0, w - block_size, block_size):
                    block = noise_pattern[i:i+block_size, j:j+block_size]
                    local_vars.append(np.var(block))
            
            # Real sensors have higher variation in local variance (spatial structure)
            # AI-generated images have more uniform noise
            local_var_std = np.std(local_vars) if local_vars else 0.0
            spatial_score = min(1.0, local_var_std * 10.0)
            
            # Measure frequency domain characteristics
            fft = np.fft.fft2(noise_pattern)
            power_spectrum = np.abs(fft) ** 2
            
            # Real PRNU has characteristic frequency distribution
            # AI noise tends to be more uniform in frequency domain
            freq_variance = np.var(power_spectrum)
            freq_score = min(1.0, freq_variance / 1000.0)
            
            # Combine metrics
            strength = (spatial_score * 0.6 + freq_score * 0.4)
            
            return min(1.0, strength)
            
        except Exception as e:
            logger.error(f"PRNU strength computation error: {e}", exc_info=True)
            return 0.5
    
    def _match_reference_patterns(self, noise_pattern: np.ndarray) -> float:
        """
        Match noise pattern against reference camera fingerprints
        
        Returns maximum correlation coefficient with any reference pattern.
        """
        try:
            if not self.reference_patterns:
                return 0.0
            
            # Resize query pattern to match reference size using PIL (no scipy needed)
            h, w = noise_pattern.shape
            
            # Convert to uint8 for PIL, resize, then back to float
            pattern_uint8 = ((noise_pattern - noise_pattern.min()) / 
                            (noise_pattern.max() - noise_pattern.min() + 1e-8) * 255).astype(np.uint8)
            pil_img = Image.fromarray(pattern_uint8, mode='L')
            pil_resized = pil_img.resize((512, 512), Image.BILINEAR)
            resized_pattern = np.array(pil_resized, dtype=np.float32) / 255.0
            
            # Normalize pattern
            normalized_query = (resized_pattern - np.mean(resized_pattern)) / (np.std(resized_pattern) + 1e-8)
            
            max_correlation = 0.0
            for camera_name, ref_pattern in self.reference_patterns.items():
                # Normalize reference
                normalized_ref = (ref_pattern - np.mean(ref_pattern)) / (np.std(ref_pattern) + 1e-8)
                
                # Compute normalized cross-correlation
                correlation = np.corrcoef(
                    normalized_query.flatten(), 
                    normalized_ref.flatten()
                )[0, 1]
                
                if correlation > max_correlation:
                    max_correlation = correlation
                    logger.debug(f"Best PRNU match: {camera_name} (correlation: {correlation:.4f})")
            
            return abs(max_correlation)  # Use absolute value
            
        except Exception as e:
            logger.error(f"Pattern matching error: {e}")
            return 0.0
    
    def _extract_noise_pattern(self, image_path: Path) -> Optional[np.ndarray]:
        """Extract sensor noise pattern from image or video"""
        try:
            # Check if file is a video
            if image_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']:
                # Extract first frame from video
                import imageio.v3 as iio
                frames = iio.imread(image_path, index=0)  # Read first frame
                image = np.array(Image.fromarray(frames).convert('L'), dtype=np.float32)
            else:
                # Open as image
                image = np.array(Image.open(image_path).convert('L'), dtype=np.float32)
            
            # Apply denoising filter to get residual noise (using numpy, no scipy)
            # Use simple box filter convolution with stride tricks
            kernel_size = 3
            pad = kernel_size // 2
            
            # Pad image
            padded = np.pad(image, ((pad, pad), (pad, pad)), mode='edge')
            
            # Apply mean filter using sliding window
            from numpy.lib.stride_tricks import as_strided
            h, w = image.shape
            strided = as_strided(
                padded,
                shape=(h, w, kernel_size, kernel_size),
                strides=padded.strides + padded.strides
            )
            denoised = np.mean(strided, axis=(2, 3))
            
            # Noise residual
            noise = image - denoised
            
            return noise
            
        except Exception as e:
            logger.error(f"Noise extraction error: {e}", exc_info=True)
            return None


class MetadataAnomalyDetector:
    """
    Detect AI-generated content through metadata analysis
    
    Checks for:
    1. Known AI generator signatures (ChatGPT, Midjourney, DALL-E, etc.)
    2. Missing EXIF data that real cameras would have
    3. Inconsistent or impossible metadata values
    """
    
    # Known AI image generator signatures
    AI_GENERATORS = {
        'midjourney': ['midjourney', 'mj'],
        'dall-e': ['dall-e', 'dall·e', 'openai'],
        'stable_diffusion': ['stable diffusion', 'sd', 'automatic1111'],
        'leonardo': ['leonardo.ai', 'leonardo'],
        'firefly': ['adobe firefly', 'firefly'],
        'bluewillow': ['bluewillow'],
        'craiyon': ['craiyon', 'dall-e mini'],
        'artbreeder': ['artbreeder'],
        'nightcafe': ['nightcafe'],
        'dreamstudio': ['dreamstudio', 'stability.ai'],
    }
    
    # Critical EXIF fields that real cameras typically have
    CRITICAL_EXIF_FIELDS = {
        'camera': ['Make', 'Model', 'LensModel'],
        'capture': ['DateTimeOriginal', 'ExposureTime', 'FNumber', 'ISO'],
        'technical': ['FocalLength', 'WhiteBalance', 'Flash']
    }
    
    def __init__(self):
        """Initialize metadata detector"""
        self.critical_exif_fields = self.CRITICAL_EXIF_FIELDS
        self.ai_generators = self.AI_GENERATORS
    
    def detect(self, image_path: Path) -> Dict[str, Any]:
        """
        Analyze image metadata for AI generation indicators
        
        Returns:
            Dict with 'score' (0-1) and 'anomalies' (List[str])
            High score = likely AI-generated
        """
        try:
            # Extract metadata
            metadata = self._extract_metadata(image_path)
            
            # Check for AI generator signatures
            ai_score, generator = self._check_ai_signatures(metadata)
            if ai_score > 0.8:
                return {
                    'score': ai_score,
                    'anomalies': [f"AI generator detected: {generator}"]
                }
            
            # Check for missing critical fields
            missing_score, missing_anomalies = self._check_missing_fields(metadata)
            
            # Check for metadata inconsistencies
            consistency_score, consistency_anomalies = self._check_consistency(metadata)
            
            # Combine scores (weighted average)
            final_score = (
                ai_score * 0.5 +
                missing_score * 0.3 +
                consistency_score * 0.2
            )
            
            all_anomalies = []
            if ai_score > 0.5:
                all_anomalies.append(f"AI signature score: {ai_score:.2f}")
            all_anomalies.extend(missing_anomalies)
            all_anomalies.extend(consistency_anomalies)
            
            return {
                'score': final_score,
                'anomalies': all_anomalies
            }
            
        except Exception as e:
            logger.error(f"Metadata detection error: {e}")
            return {'score': 0.5, 'anomalies': [f"Analysis error: {str(e)}"]}
    
    def _extract_metadata(self, image_path: Path) -> Dict[str, str]:
        """Extract EXIF and other metadata from image"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            with Image.open(image_path) as img:
                metadata = {}
                
                # Extract EXIF data
                exif = img.getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        metadata[str(tag)] = str(value)
                
                # Extract other metadata
                metadata['format'] = img.format
                metadata['mode'] = img.mode
                metadata['size'] = f"{img.width}x{img.height}"
                
                # Check for AI-specific metadata fields
                if hasattr(img, 'info'):
                    for key, value in img.info.items():
                        metadata[key] = str(value)
                
                return metadata
                
        except Exception as e:
            logger.error(f"Metadata extraction error: {e}")
            return {}
    
    def _check_ai_signatures(self, metadata: Dict[str, str]) -> tuple[float, Optional[str]]:
        """Check for known AI generator signatures in metadata"""
        metadata_str = ' '.join(metadata.values()).lower()
        
        for generator, signatures in self.ai_generators.items():
            for sig in signatures:
                if sig in metadata_str:
                    # Check which metadata field contains the signature
                    for field, value in metadata.items():
                        if sig in value.lower():
                            logger.info(f"AI generator detected: {generator} (field: {field})")
                            return 0.95, generator
        
        return 0.0, None
    
    def _check_missing_fields(self, metadata: Dict[str, str]) -> tuple[float, List[str]]:
        """Analyze missing EXIF fields that real cameras should have"""
        anomalies = []
        
        # Count missing fields per category
        missing_counts = {}
        for category, fields in self.critical_exif_fields.items():
            missing = [f for f in fields if f not in metadata]
            missing_counts[category] = len(missing)
            
            if missing and category != 'technical':  # Technical fields are somewhat optional
                anomalies.append(f"Missing {category} metadata: {', '.join(missing)}")
        
        # Calculate score based on missing fields
        total_critical = len(self.critical_exif_fields['camera']) + len(self.critical_exif_fields['capture'])
        missing_critical = missing_counts.get('camera', 0) + missing_counts.get('capture', 0)
        
        if missing_critical >= total_critical:
            # All critical fields missing - highly suspicious
            return 0.9, anomalies
        elif missing_critical > 0:
            # Some critical fields missing
            score = 0.4 + (missing_critical / total_critical) * 0.4
            return score, anomalies
        else:
            return 0.0, []
    
    def _check_consistency(self, metadata: Dict[str, str]) -> tuple[float, List[str]]:
        """Check for internal metadata inconsistencies"""
        anomalies = []
        score = 0.0
        
        # Check make/model consistency
        if 'Make' in metadata and 'Model' in metadata:
            make = metadata['Make'].lower()
            model = metadata['Model'].lower()
            
            # Common camera make/model pairs
            expected_pairs = {
                'canon': ['eos', 'powershot', 'rebel'],
                'nikon': ['d\\d+', 'z\\d+', 'coolpix'],
                'sony': ['alpha', 'a\\d+', 'ilce', 'dsc'],
                'apple': ['iphone', 'ipad'],
            }
            
            matched = False
            for brand, models in expected_pairs.items():
                if brand in make:
                    import re
                    for model_pattern in models:
                        if re.search(model_pattern, model):
                            matched = True
                            break
            
            if not matched and make and model:
                anomalies.append(f"Unusual make/model combination: {metadata['Make']} {metadata['Model']}")
                score += 0.3
        
        # Check date consistency
        if 'DateTime' in metadata and 'DateTimeOriginal' in metadata:
            if metadata['DateTime'] != metadata['DateTimeOriginal']:
                # Small differences are normal for edited photos
                # Large differences suggest fabrication
                anomalies.append("DateTime mismatch between created and original")
                score += 0.2
        
        return min(1.0, score), anomalies


class MLDetector:
    """
    Ensemble ML detector combining multiple approaches:
    1. ResNeXt+LSTM deepfake detection (temporal patterns)
    2. PRNU sensor fingerprint analysis
    3. Metadata forensics
    """
    
    def __init__(self):
        """Initialize ensemble detector"""
        model_path = Path(__file__).parent.parent / "models"
        model_path.mkdir(parents=True, exist_ok=True)
        
        self.cnn_detector = CNNArtifactDetector(model_path)
        self.prnu_analyzer = PRNUAnalyzer(model_path)
        self.metadata_detector = MetadataAnomalyDetector()
        self.enhanced_detector = EnhancedAIDetector()
        
        # Ensemble weights (sum to 1.0)
        self.weights = {
            'cnn': 0.4,             # Primary: ResNeXt+LSTM deepfake detection
            'prnu': 0.15,           # Secondary: Camera sensor fingerprinting
            'metadata': 0.15,       # Tertiary: Metadata forensics
            'compression': 0.2,     # Enhanced: Compression artifacts
            'video_consistency': 0.1 # Enhanced: Video temporal consistency
        }
        
        logger.info("ML detector ensemble initialized (with enhanced detection)")
    
    async def detect(self, file_path: Path) -> MLDetectionResult:
        """
        Run ensemble ML detection
        
        Args:
            file_path: Path to media file
            
        Returns:
            MLDetectionResult with detection scores
        """
        try:
            # Run individual detectors
            cnn_score = self.cnn_detector.detect(file_path)
            
            # PRNU analysis (now scipy-free, uses pure numpy/PIL)
            prnu_score = 1.0 - self.prnu_analyzer.analyze(file_path)  # Invert (high = AI)
            logger.info(f"PRNU analysis complete: {prnu_score:.3f}")
            
            metadata_result = self.metadata_detector.detect(file_path)
            metadata_score = metadata_result['score']
            
            # Enhanced detection (compression artifacts, video consistency)
            enhanced_results = self.enhanced_detector.analyze(file_path)
            compression_score = enhanced_results.get('compression_artifacts', 0.5)
            video_consistency_score = enhanced_results.get('video_consistency', None)
            
            logger.info(f"Detection scores - CNN: {cnn_score:.3f}, PRNU: {prnu_score:.3f}, "
                       f"Metadata: {metadata_score:.3f}, Compression: {compression_score:.3f}, "
                       f"Video: {video_consistency_score if video_consistency_score else 'N/A'}")
            
            # Smart ensemble: use enhanced detection when primary is inconclusive
            if abs(cnn_score - 0.5) < 0.15:  # CNN is uncertain (0.35-0.65)
                logger.info("CNN uncertain, boosting enhanced detection weights")
                # Boost enhanced detection weights
                effective_weights = {
                    'cnn': 0.2,
                    'prnu': 0.1,
                    'metadata': 0.15,
                    'compression': 0.4,
                    'video_consistency': 0.15 if video_consistency_score is not None else 0.0
                }
            else:
                effective_weights = self.weights.copy()
            
            # Normalize weights if video analysis not available
            if video_consistency_score is None:
                total = sum(v for k, v in effective_weights.items() if k != 'video_consistency')
                for key in effective_weights:
                    if key != 'video_consistency':
                        effective_weights[key] = effective_weights[key] / total
                effective_weights['video_consistency'] = 0.0
                video_consistency_score = 0.5  # Neutral default
            
            # Compute ensemble score
            ensemble_score = (
                effective_weights['cnn'] * cnn_score +
                effective_weights['prnu'] * prnu_score +
                effective_weights['metadata'] * metadata_score +
                effective_weights['compression'] * compression_score +
                effective_weights['video_consistency'] * video_consistency_score
            )
            
            # Determine confidence based on agreement between detectors
            all_scores = [s for s in [cnn_score, prnu_score, metadata_score, 
                                      compression_score, video_consistency_score] 
                         if s is not None and s != 0.5]
            
            if len(all_scores) < 2:
                confidence = 0.3  # Low confidence if not enough detectors agree
            else:
                std_dev = np.std(all_scores)
                # Lower std = higher confidence, but require meaningful deviation from 0.5
                avg_score = np.mean(all_scores)
                deviation_from_neutral = abs(avg_score - 0.5)
                
                confidence = (1.0 - min(std_dev / 0.4, 1.0)) * (deviation_from_neutral * 2)
                confidence = max(0.3, min(0.95, confidence))  # Clamp to 0.3-0.95
            
            # Detect specific generator if metadata indicates AI
            detected_generator = None
            if metadata_score > 0.8 and metadata_result['anomalies']:
                for anomaly in metadata_result['anomalies']:
                    if 'generator detected' in anomaly.lower():
                        detected_generator = anomaly.split(':')[-1].strip()
                        break
            
            # Compile artifacts found
            artifacts = []
            
            # CNN artifacts
            if cnn_score > 0.7:
                artifacts.append(f"Deepfake detection: High probability ({cnn_score:.1%})")
            elif cnn_score < 0.3:
                artifacts.append(f"Deepfake detection: Likely authentic ({1-cnn_score:.1%} confidence)")
            
            # PRNU artifacts
            if prnu_score > 0.7:
                artifacts.append(f"Camera fingerprint: Inconsistent with real sensors ({prnu_score:.1%})")
            elif prnu_score < 0.3:
                artifacts.append(f"Camera fingerprint: Matches real camera patterns ({1-prnu_score:.1%})")
            
            # Metadata artifacts
            if metadata_score > 0.5:
                artifacts.extend(metadata_result['anomalies'])
            
            # Compression artifacts
            if compression_score > 0.7:
                artifacts.append(f"Compression analysis: AI-generated characteristics detected ({compression_score:.1%})")
            elif compression_score < 0.3:
                artifacts.append(f"Compression analysis: Natural photo characteristics ({1-compression_score:.1%})")
            
            # Video consistency
            if video_consistency_score is not None:
                if video_consistency_score > 0.7:
                    artifacts.append(f"Video analysis: Temporal inconsistencies detected ({video_consistency_score:.1%})")
                elif video_consistency_score < 0.3:
                    artifacts.append(f"Video analysis: Consistent temporal patterns ({1-video_consistency_score:.1%})")
            
            # Summary verdict
            if ensemble_score > 0.7:
                artifacts.insert(0, f"⚠️ HIGH CONFIDENCE AI-GENERATED ({ensemble_score:.1%})")
            elif ensemble_score > 0.55:
                artifacts.insert(0, f"⚠️ LIKELY AI-GENERATED ({ensemble_score:.1%})")
            elif ensemble_score < 0.3:
                artifacts.insert(0, f"✓ HIGH CONFIDENCE AUTHENTIC ({1-ensemble_score:.1%})")
            elif ensemble_score < 0.45:
                artifacts.insert(0, f"✓ LIKELY AUTHENTIC ({1-ensemble_score:.1%})")
            else:
                artifacts.insert(0, f"❓ INCONCLUSIVE - requires additional analysis")
            
            return MLDetectionResult(
                ai_probability=ensemble_score,
                cnn_score=cnn_score,
                prnu_score=prnu_score,
                metadata_anomaly_score=metadata_score,
                transformer_score=compression_score,  # Repurpose for compression score
                ensemble_confidence=confidence,
                detected_generator=detected_generator,
                artifacts_found=artifacts
            )
            
        except Exception as e:
            logger.error(f"ML detection pipeline error: {e}", exc_info=True)
            return MLDetectionResult(
                ai_probability=0.5,
                ensemble_confidence=0.0,
                artifacts_found=[f"Detection error: {str(e)}"]
            )


# Global singleton instance
ml_detector = MLDetector()
