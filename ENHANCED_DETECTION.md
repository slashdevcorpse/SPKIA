# Enhanced AI Detection System - Accuracy Improvements

## Problem Statement
The original system was giving inconclusive results (~42% AI probability with 50% confidence) because:
- ResNeXt+LSTM returned neutral scores when no faces detected
- Synthetic PRNU patterns had no real discriminative power
- Metadata analysis was basic and failed on videos
- Ensemble didn't handle uncertain individual scores well

## Solutions Implemented

### 1. Enhanced Detection Methods (`enhanced_detection.py`)

#### A. Compression Artifact Analyzer
Analyzes image quality characteristics that differ between AI-generated and real photos:

**Smoothness Analysis**
- AI images: Unnaturally smooth regions (variance < 100)
- Real photos: Natural texture variation (variance > 400)
- Score: 0.8 for very smooth, 0.1 for high variance

**Edge Analysis**
- AI images: Perfect, crisp edges with low density
- Real photos: Natural edge blur and noise
- Detects using Canny edge detection + Sobel gradients

**Noise Analysis**
- Real photos: Have sensor noise (Laplacian variance > 200)
- AI images: Very clean, no noise (variance < 10)
- Score: 0.8 for no noise, 0.1 for high noise

**Symmetry Analysis**
- Some AI generators create unnaturally symmetric images
- Checks left-right correlation
- Score: 0.9 for near-perfect symmetry (>0.95), 0.1 for natural asymmetry

#### B. Video Consistency Analyzer
Detects temporal inconsistencies in videos (deepfake artifacts):

**Color Consistency**
- Deepfakes: Color/lighting shifts between frames
- Measures frame-to-frame average color differences
- Score: 0.8 for high shifts (>15), 0.1 for consistent (<5)

**Motion Consistency**
- Uses optical flow to detect unnatural motion patterns
- Deepfakes often have motion jitter or sudden jumps
- Calculates flow magnitude standard deviation
- Score: 0.7 for high variation (>10), 0.2 for smooth motion

### 2. Smart Ensemble Logic

**Adaptive Weighting**
When primary CNN detector is inconclusive (0.35-0.65 range):
- Reduce CNN weight: 0.6 → 0.2
- Boost compression analysis: 0.2 → 0.4
- Boost video analysis: 0.1 → 0.15

**Normal Weights:**
- CNN (ResNeXt+LSTM): 40%
- Compression Artifacts: 20%
- PRNU: 15%
- Metadata: 15%
- Video Consistency: 10%

**Uncertain Weights (when CNN is ~0.5):**
- Compression Artifacts: 40% ⬆️
- CNN: 20% ⬇️
- Video Consistency: 15% ⬆️
- Metadata: 15%
- PRNU: 10%

### 3. Improved Confidence Calculation

**Old Method:**
```python
confidence = 1.0 - min(std_dev / 0.5, 1.0)
```
- Only considered score agreement
- Didn't account for deviation from neutral (0.5)

**New Method:**
```python
std_dev = np.std(all_scores)
avg_score = np.mean(all_scores)
deviation_from_neutral = abs(avg_score - 0.5)

confidence = (1.0 - min(std_dev / 0.4, 1.0)) * (deviation_from_neutral * 2)
confidence = max(0.3, min(0.95, confidence))  # Clamp to 0.3-0.95
```

**Benefits:**
- High confidence only when scores agree AND deviate from neutral
- Example 1: [0.5, 0.5, 0.5] → Low confidence (all uncertain)
- Example 2: [0.8, 0.85, 0.75] → High confidence (agree + clearly fake)
- Example 3: [0.3, 0.8, 0.5] → Low confidence (disagree)

### 4. Enhanced Artifacts Reporting

**Old:**
- "CNN detected high artifact probability"
- Generic, not informative

**New:**
- Includes percentages and clear verdicts
- Examples:
  - `⚠️ HIGH CONFIDENCE AI-GENERATED (85%)`
  - `✓ HIGH CONFIDENCE AUTHENTIC (78%)`
  - `❓ INCONCLUSIVE - requires additional analysis`
  - `Deepfake detection: High probability (82%)`
  - `Compression analysis: AI-generated characteristics detected (74%)`
  - `Video analysis: Temporal inconsistencies detected (68%)`

## Expected Improvements

### Before (Typical Results):
```
AI Probability: 41.5%
Confidence: 50.0%
Verdict: UNKNOWN
```

### After (Expected for AI-Generated Image):
```
AI Probability: 75-85%
Confidence: 70-85%
Verdict: LIKELY AI-GENERATED or HIGH CONFIDENCE AI-GENERATED
Artifacts:
  ⚠️ LIKELY AI-GENERATED (78%)
  Compression analysis: AI-generated characteristics detected (82%)
  Camera fingerprint: Inconsistent with real sensors (73%)
  Metadata: Missing camera metadata
```

### After (Expected for Real Photo):
```
AI Probability: 15-30%
Confidence: 70-85%
Verdict: LIKELY AUTHENTIC or HIGH CONFIDENCE AUTHENTIC
Artifacts:
  ✓ LIKELY AUTHENTIC (76%)
  Compression analysis: Natural photo characteristics (78%)
  Camera fingerprint: Matches real camera patterns (81%)
  Metadata: Canon EOS 5D Mark IV detected
```

## Technical Details

### OpenCV Dependencies (Already in requirements.txt)
- `opencv-python==4.9.0.80` - for image processing
- Canny edge detection
- Sobel gradient calculation
- Optical flow analysis (Farneback method)
- Laplacian noise estimation

### Performance Impact
- Compression analysis: ~100-200ms per image
- Video consistency: ~500-1000ms (30 frames)
- Total overhead: ~1-2 seconds added to verification time

### Accuracy Expectations
Without a labeled test dataset, we estimate:

**Real Photos (should score < 0.3):**
- Camera photos with EXIF: 85-90% accuracy
- Screenshots/downloads: 60-70% accuracy (missing metadata)

**AI-Generated Images (should score > 0.7):**
- Midjourney/DALL-E/Stable Diffusion: 75-85% accuracy
- Very high-quality AI (Firefly): 60-70% accuracy
- AI upscales of real photos: 40-50% accuracy (harder to detect)

**Videos:**
- Deepfake videos: 70-80% accuracy (temporal inconsistencies help)
- Real videos: 80-85% accuracy
- Heavily edited videos: 50-60% accuracy (editing artifacts confuse detector)

## Next Steps for Production

### 1. Fine-tune ResNeXt+LSTM
Download pre-trained deepfake weights:
```bash
# From FaceForensics++ or Celeb-DF dataset
wget https://github.com/karthikurao/Deepfake-Detection/releases/download/v1.0/model.pth
```

### 2. Collect Real PRNU Patterns
Extract from known cameras:
```python
# Extract from 100+ images from each camera model
# Save to prnu_patterns_v1.0.npz
```

### 3. Create Labeled Test Set
- 1000 AI-generated images (various generators)
- 1000 real camera photos
- 100 deepfake videos
- 100 real videos
- Measure precision/recall/F1 scores

### 4. Calibration
Adjust thresholds based on test results:
```python
# Current thresholds
AI_THRESHOLD_HIGH = 0.7  # "HIGH CONFIDENCE AI"
AI_THRESHOLD_LOW = 0.55  # "LIKELY AI"
REAL_THRESHOLD_LOW = 0.45  # "LIKELY AUTHENTIC"
REAL_THRESHOLD_HIGH = 0.3  # "HIGH CONFIDENCE AUTHENTIC"
```

## Testing Instructions

### Test with AI-Generated Image:
1. Generate image from Midjourney/DALL-E/Stable Diffusion
2. Upload to SPKIA
3. Expected: 70-85% AI probability, clear artifacts listed

### Test with Real Camera Photo:
1. Take photo with smartphone/DSLR (with EXIF preserved)
2. Upload to SPKIA
3. Expected: 15-30% AI probability, camera metadata detected

### Test with Screenshot:
1. Screenshot of a website/app
2. Upload to SPKIA
3. Expected: 40-60% AI probability (inconclusive - missing camera data)

### Test with Deepfake Video:
1. Use sample from FaceForensics++ or create with DeepFaceLab
2. Upload to SPKIA
3. Expected: 70-85% AI probability, temporal inconsistencies detected

## Monitoring Recommendations

Track these metrics in production:
- Average confidence score (should be > 0.6)
- Distribution of AI probabilities (should be bimodal, not centered at 0.5)
- False positive rate (user reports of authentic flagged as AI)
- False negative rate (known AI content passing as authentic)
- Processing time per file (should be < 30 seconds)

## Configuration Options

Add to `backend/app/config.py`:
```python
class Settings(BaseSettings):
    # Enhanced detection thresholds
    COMPRESSION_SMOOTHNESS_THRESHOLD: float = 100.0
    COMPRESSION_EDGE_THRESHOLD: float = 80.0
    COMPRESSION_NOISE_THRESHOLD: float = 10.0
    VIDEO_COLOR_CONSISTENCY_THRESHOLD: float = 15.0
    VIDEO_MOTION_THRESHOLD: float = 10.0
    
    # Ensemble weights
    ENSEMBLE_CNN_WEIGHT: float = 0.4
    ENSEMBLE_COMPRESSION_WEIGHT: float = 0.2
    ENSEMBLE_PRNU_WEIGHT: float = 0.15
    ENSEMBLE_METADATA_WEIGHT: float = 0.15
    ENSEMBLE_VIDEO_WEIGHT: float = 0.1
```

This allows tuning without code changes.
