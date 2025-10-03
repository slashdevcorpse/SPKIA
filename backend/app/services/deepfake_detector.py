"""
ResNeXt + LSTM Deepfake Detection Model
Based on approach from: https://github.com/karthikurao/Deepfake-Detection

Architecture:
1. ResNeXt-50 (32x4d) for spatial feature extraction (2048-dim per frame)
2. LSTM for temporal sequence analysis
3. Softmax classifier for binary classification (Real/Fake)

Achieves 97.7% accuracy on FaceForensics++ dataset
"""
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import resnext50_32x4d, ResNeXt50_32X4D_Weights
from PIL import Image
import cv2

logger = logging.getLogger(__name__)


class ResNextLSTM(nn.Module):
    """
    ResNeXt-50 + LSTM model for deepfake detection
    
    Architecture:
    - ResNeXt-50 backbone (pretrained on ImageNet) for spatial feature extraction
    - LSTM layer for temporal feature learning across video frames
    - Fully connected layers for classification
    """
    
    def __init__(self, num_classes=2, hidden_dim=2048, lstm_layers=2, dropout=0.4):
        """
        Args:
            num_classes: Number of output classes (2 for Real/Fake)
            hidden_dim: Hidden dimension for LSTM
            lstm_layers: Number of LSTM layers
            dropout: Dropout probability
        """
        super(ResNextLSTM, self).__init__()
        
        # Load pretrained ResNeXt-50 (32x4d)
        self.feature_extractor = resnext50_32x4d(weights=ResNeXt50_32X4D_Weights.IMAGENET1K_V2)
        
        # Remove the final FC layer to get 2048-dim features
        num_features = self.feature_extractor.fc.in_features
        self.feature_extractor.fc = nn.Identity()  # Remove classification head
        
        # LSTM for temporal modeling
        self.lstm = nn.LSTM(
            input_size=num_features,
            hidden_size=hidden_dim,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0,
            bidirectional=True
        )
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 512),  # *2 for bidirectional
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(128, num_classes)
        )
        
        # Freeze ResNeXt backbone for initial training (optional)
        # self._freeze_backbone()
    
    def _freeze_backbone(self):
        """Freeze ResNeXt backbone to speed up training"""
        for param in self.feature_extractor.parameters():
            param.requires_grad = False
    
    def _unfreeze_backbone(self):
        """Unfreeze for fine-tuning"""
        for param in self.feature_extractor.parameters():
            param.requires_grad = True
    
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: Input tensor of shape (batch_size, seq_len, channels, height, width)
               seq_len is number of frames per video
        
        Returns:
            Output tensor of shape (batch_size, num_classes)
        """
        batch_size, seq_len, c, h, w = x.size()
        
        # Reshape to process all frames through CNN
        # (batch_size * seq_len, channels, height, width)
        x = x.view(batch_size * seq_len, c, h, w)
        
        # Extract spatial features with ResNeXt
        # Output: (batch_size * seq_len, 2048)
        features = self.feature_extractor(x)
        
        # Reshape for LSTM
        # (batch_size, seq_len, 2048)
        features = features.view(batch_size, seq_len, -1)
        
        # LSTM for temporal modeling
        # lstm_out: (batch_size, seq_len, hidden_dim * 2)
        lstm_out, (hidden, cell) = self.lstm(features)
        
        # Use the last hidden state for classification
        # For bidirectional, concatenate final states from both directions
        # hidden: (num_layers * 2, batch_size, hidden_dim)
        forward_hidden = hidden[-2, :, :]  # Last layer, forward direction
        backward_hidden = hidden[-1, :, :]  # Last layer, backward direction
        final_hidden = torch.cat([forward_hidden, backward_hidden], dim=1)
        
        # Classification
        # output: (batch_size, num_classes)
        output = self.classifier(final_hidden)
        
        return output


class DeepfakeDetector:
    """
    High-level deepfake detection interface using ResNeXt + LSTM
    
    Handles video preprocessing, face detection, frame extraction, and prediction
    """
    
    def __init__(self, model_path: Optional[Path] = None, device: str = 'cpu'):
        """
        Initialize detector
        
        Args:
            model_path: Path to pretrained model weights (.pth file)
            device: 'cpu' or 'cuda'
        """
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_path = model_path
        self._model_loaded = False
        
        # Image preprocessing for ResNeXt (ImageNet normalization)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        # Face detection cascade (for face cropping)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        logger.info(f"Deepfake detector initialized on {self.device}")
    
    def _load_model(self):
        """Load model weights (lazy loading)"""
        try:
            self.model = ResNextLSTM(num_classes=2)
            
            if self.model_path and self.model_path.exists():
                # Load pretrained weights
                logger.info(f"Loading model weights from {self.model_path}")
                checkpoint = torch.load(self.model_path, map_location=self.device)
                
                if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                else:
                    self.model.load_state_dict(checkpoint)
                
                logger.info("Loaded fine-tuned deepfake detection model")
            else:
                logger.warning(f"Model weights not found at {self.model_path}, using pretrained ResNeXt-50 + LSTM")
            
            self.model.to(self.device)
            self.model.eval()
            self._model_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def extract_faces_from_video(self, video_path: Path, max_frames: int = 20) -> List[np.ndarray]:
        """
        Extract face regions from video frames
        
        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to extract
        
        Returns:
            List of face images as numpy arrays
        """
        faces = []
        
        try:
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return []
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Sample frames uniformly across video
            if total_frames > max_frames:
                frame_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            else:
                frame_indices = range(total_frames)
            
            current_frame = 0
            for target_idx in frame_indices:
                # Skip to target frame
                while current_frame < target_idx:
                    ret = cap.grab()
                    if not ret:
                        break
                    current_frame += 1
                
                ret, frame = cap.retrieve()
                if not ret:
                    break
                
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detected_faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                
                # Take the largest face
                if len(detected_faces) > 0:
                    # Sort by area (largest first)
                    detected_faces = sorted(detected_faces, key=lambda f: f[2] * f[3], reverse=True)
                    x, y, w, h = detected_faces[0]
                    
                    # Crop face with some padding
                    padding = int(0.2 * w)
                    x1 = max(0, x - padding)
                    y1 = max(0, y - padding)
                    x2 = min(frame_rgb.shape[1], x + w + padding)
                    y2 = min(frame_rgb.shape[0], y + h + padding)
                    
                    face = frame_rgb[y1:y2, x1:x2]
                    faces.append(face)
                else:
                    # No face detected, use full frame
                    faces.append(frame_rgb)
                
                current_frame += 1
            
            cap.release()
            logger.info(f"Extracted {len(faces)} faces from video")
            
        except Exception as e:
            logger.error(f"Face extraction error: {e}")
        
        return faces
    
    def preprocess_faces(self, faces: List[np.ndarray]) -> torch.Tensor:
        """
        Preprocess face images for model input
        
        Args:
            faces: List of face images as numpy arrays
        
        Returns:
            Tensor of shape (1, seq_len, 3, 224, 224)
        """
        processed_frames = []
        
        for face in faces:
            # Convert numpy array to PIL Image
            pil_img = Image.fromarray(face.astype('uint8'), 'RGB')
            
            # Apply transformations
            tensor = self.transform(pil_img)
            processed_frames.append(tensor)
        
        # Stack into sequence
        # (seq_len, 3, 224, 224)
        sequence = torch.stack(processed_frames, dim=0)
        
        # Add batch dimension
        # (1, seq_len, 3, 224, 224)
        sequence = sequence.unsqueeze(0)
        
        return sequence
    
    def predict(self, video_path: Path, max_frames: int = 20) -> Tuple[str, float]:
        """
        Predict whether video is real or fake
        
        Args:
            video_path: Path to video file
            max_frames: Number of frames to analyze
        
        Returns:
            Tuple of (prediction, confidence)
            prediction: 'REAL' or 'FAKE'
            confidence: float between 0 and 1
        """
        # Lazy load model
        if not self._model_loaded:
            logger.info("Loading model (first use)...")
            self._load_model()
        
        try:
            # Extract faces from video
            faces = self.extract_faces_from_video(video_path, max_frames)
            
            if len(faces) == 0:
                logger.warning("No faces detected in video")
                return 'UNKNOWN', 0.5
            
            # Preprocess faces
            input_tensor = self.preprocess_faces(faces).to(self.device)
            
            # Inference
            with torch.no_grad():
                output = self.model(input_tensor)
                probabilities = torch.softmax(output, dim=1)
                
                # probabilities: [prob_real, prob_fake]
                prob_real = probabilities[0, 0].item()
                prob_fake = probabilities[0, 1].item()
                
                if prob_fake > prob_real:
                    prediction = 'FAKE'
                    confidence = prob_fake
                else:
                    prediction = 'REAL'
                    confidence = prob_real
            
            logger.info(f"Prediction: {prediction} (confidence: {confidence:.4f})")
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 'ERROR', 0.0
    
    def detect_score(self, video_path: Path, max_frames: int = 20) -> float:
        """
        Get deepfake score (0-1) where 1 means definitely fake
        
        Args:
            video_path: Path to video file
            max_frames: Number of frames to analyze
        
        Returns:
            Score between 0 and 1 (higher = more likely fake)
        """
        prediction, confidence = self.predict(video_path, max_frames)
        
        if prediction == 'FAKE':
            return confidence
        elif prediction == 'REAL':
            return 1.0 - confidence
        else:
            return 0.5  # Unknown
