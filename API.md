# SPKIA API Documentation

## Base URL

```
Development: http://localhost:8000
Production: https://api.spkia.org
```

## Authentication

No authentication required. The service is publicly accessible.

## Rate Limits

- **General API**: 10 requests/second
- **Upload endpoint**: 2 requests/second

## Endpoints

### 1. Upload File for Verification

**POST** `/api/verify`

Upload a media file for authenticity verification.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (image or video file)

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

**Status Codes:**
- `200 OK`: File accepted
- `413 Payload Too Large`: File exceeds 100MB limit
- `400 Bad Request`: Invalid file type
- `500 Internal Server Error`: Server error

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/verify \
  -F "file=@/path/to/image.jpg"
```

---

### 2. Verify URL

**POST** `/api/verify-url`

Verify a media file from a URL.

**Request:**
```json
{
  "url": "https://example.com/image.jpg"
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

**Status Codes:**
- `200 OK`: URL accepted
- `400 Bad Request`: Invalid URL or download failed
- `413 Payload Too Large`: File exceeds 100MB limit
- `500 Internal Server Error`: Server error

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/verify-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/image.jpg"}'
```

---

### 3. Get Verification Result

**GET** `/api/verify/{job_id}`

Retrieve verification results for a job.

**Parameters:**
- `job_id` (path): Job identifier from upload response

**Response (Processing):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "reasons": [],
  "created_at": "2025-10-02T10:30:00Z",
  "updated_at": "2025-10-02T10:30:05Z"
}
```

**Response (Completed - Authentic Camera):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "label": "authentic_camera",
  "confidence": 0.95,
  "reasons": [
    "Valid sensor-PKI signature from Sony Alpha 7R V",
    "C2PA manifest verified"
  ],
  "details": {
    "c2pa": {
      "valid": true,
      "issuer": "Sony",
      "trust_chain_valid": true
    },
    "sensor_pki": {
      "valid": true,
      "manufacturer": "Sony",
      "camera_model": "Alpha 7R V",
      "sensor_id": "IMX989-12345",
      "signature_algorithm": "ES256"
    },
    "ml_detection": null
  },
  "created_at": "2025-10-02T10:30:00Z",
  "updated_at": "2025-10-02T10:30:08Z"
}
```

**Response (Completed - AI Generated):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "label": "likely_ai_generated",
  "confidence": 0.88,
  "reasons": [
    "ML classifiers indicate AI-generated (probability: 0.85)",
    "CNN detected high artifact probability",
    "PRNU pattern inconsistent with real camera"
  ],
  "details": {
    "c2pa": {
      "valid": false,
      "error": "No C2PA manifest found"
    },
    "sensor_pki": {
      "valid": false,
      "error": "No sensor-PKI signature found"
    },
    "ml_detection": {
      "ai_probability": 0.85,
      "cnn_score": 0.92,
      "prnu_score": 0.78,
      "metadata_anomaly_score": 0.65,
      "ensemble_confidence": 0.88,
      "detected_generator": "Stable Diffusion",
      "artifacts_found": [
        "CNN detected high artifact probability",
        "PRNU pattern inconsistent with real camera"
      ]
    }
  },
  "created_at": "2025-10-02T10:30:00Z",
  "updated_at": "2025-10-02T10:30:12Z"
}
```

**Status Codes:**
- `200 OK`: Results retrieved
- `404 Not Found`: Job not found
- `500 Internal Server Error`: Server error

**cURL Example:**
```bash
curl -X GET http://localhost:8000/api/verify/550e8400-e29b-41d4-a716-446655440000
```

**Polling Recommendation:**
Poll every 2-3 seconds until `status` is `completed` or `failed`.

---

### 4. Delete Verification

**DELETE** `/api/verify/{job_id}`

Force immediate deletion of verification job and data.

**Parameters:**
- `job_id` (path): Job identifier

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted": true,
  "message": "Job and associated data deleted successfully"
}
```

**Status Codes:**
- `200 OK`: Successfully deleted
- `404 Not Found`: Job not found
- `500 Internal Server Error`: Server error

**cURL Example:**
```bash
curl -X DELETE http://localhost:8000/api/verify/550e8400-e29b-41d4-a716-446655440000
```

---

### 5. Health Check

**GET** `/health`

Check service health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-02T10:30:00Z",
  "database": "connected",
  "ml_models_loaded": true
}
```

**Status Codes:**
- `200 OK`: Service is healthy

**cURL Example:**
```bash
curl -X GET http://localhost:8000/health
```

---

### 6. Get Metrics

**GET** `/api/metrics?days=7`

Get aggregated anonymized metrics.

**Parameters:**
- `days` (query, optional): Number of days to aggregate (default: 7)

**Response:**
```json
{
  "total_verifications": 1523,
  "authentic_camera": 892,
  "authentic_c2pa": 245,
  "ai_generated": 312,
  "unknown": 74,
  "avg_processing_time": 1847.5
}
```

**Status Codes:**
- `200 OK`: Metrics retrieved

---

## Data Models

### VerificationStatus

```typescript
type VerificationStatus = 'pending' | 'processing' | 'completed' | 'failed';
```

### AuthenticityLabel

```typescript
type AuthenticityLabel = 
  | 'authentic_camera'    // Sensor-PKI verified
  | 'authentic_c2pa'      // C2PA verified (no sensor-PKI)
  | 'likely_ai_generated' // ML detection > threshold
  | 'unknown'             // Inconclusive
  | 'error';              // Verification error
```

### Confidence Score

- Range: `0.0` to `1.0`
- Higher values indicate stronger confidence
- `authentic_camera` typically: 0.95-0.98
- `authentic_c2pa` typically: 0.85-0.92
- `likely_ai_generated` typically: 0.70-0.95
- `unknown` typically: 0.40-0.60

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message",
  "detail": "Detailed explanation (optional)",
  "job_id": "job_id (optional)"
}
```

**Common Errors:**
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: File exceeds size limit
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Best Practices

1. **Polling**: Poll `/api/verify/{job_id}` every 2-3 seconds
2. **Cleanup**: Call `DELETE /api/verify/{job_id}` after retrieving results
3. **File Size**: Keep files under 100MB
4. **Rate Limiting**: Respect rate limits (2 req/s for uploads)
5. **Error Handling**: Implement retry logic with exponential backoff

---

## Interactive API Documentation

**Swagger UI**: http://localhost:8000/docs  
**ReDoc**: http://localhost:8000/redoc

---

## Support

- 📧 **Email**: api@spkia.org
- 🐛 **Issues**: https://github.com/your-org/spkia/issues
- 📖 **Docs**: https://docs.spkia.org
