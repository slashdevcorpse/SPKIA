# ML Models Directory

This directory contains trained machine learning models for AI media detection.

## Required Models

### 1. CNN Artifact Detector
- **File**: `cnn_artifact_detector_v1.0.pth`
- **Description**: Convolutional Neural Network trained to detect AI-generated artifacts
- **Training**: Train on benchmark datasets of real vs AI-generated images
- **Framework**: PyTorch

### 2. PRNU Patterns
- **File**: `prnu_patterns_v1.0.npz`
- **Description**: Photo Response Non-Uniformity reference patterns for known cameras
- **Format**: NumPy compressed array
- **Contents**: Dictionary mapping camera models to PRNU noise patterns

### 3. Metadata Anomaly Detector (Optional)
- **File**: `metadata_classifier_v1.0.pkl`
- **Description**: ML model for detecting metadata inconsistencies
- **Framework**: scikit-learn

## Model Training

### CNN Artifact Detector

```python
import torch
import torch.nn as nn
from torchvision import models, transforms

# Example training script
class ArtifactDetector(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = models.resnet50(pretrained=True)
        self.backbone.fc = nn.Linear(2048, 1)
    
    def forward(self, x):
        return self.backbone(x)

# Train model on dataset
# Save trained model
torch.save(model.state_dict(), 'cnn_artifact_detector_v1.0.pth')
```

### PRNU Patterns

```python
import numpy as np

# Extract PRNU patterns from reference images
patterns = {
    'Sony_IMX989': prnu_pattern_1,
    'Canon_EOS_R5': prnu_pattern_2,
    # ... more cameras
}

# Save patterns
np.savez_compressed('prnu_patterns_v1.0.npz', patterns=patterns)
```

## Benchmark Datasets

Recommended datasets for training:

1. **Real Images**:
   - COCO dataset
   - ImageNet
   - Camera-specific datasets

2. **AI-Generated Images**:
   - DiffusionDB (Stable Diffusion)
   - DALL·E samples
   - Midjourney exports
   - Custom generations from latest models

3. **C2PA Datasets**:
   - Adobe Content Authenticity Initiative samples
   - CAI benchmark set

## Model Performance

Target metrics:
- **Precision**: > 92%
- **Recall**: > 90%
- **F1-Score**: > 91%
- **False Positive Rate**: < 5%

## Continuous Retraining

- Retrain models quarterly with new AI generators
- Monitor performance degradation
- Add new generator signatures to training data
- Version models clearly (v1.0, v1.1, etc.)

## License

Models should comply with training dataset licenses and usage restrictions.
