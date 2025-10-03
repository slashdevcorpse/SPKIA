/**
 * API types for SPKIA backend
 */

export type VerificationStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type AuthenticityLabel = 
  | 'authentic_camera'
  | 'authentic_c2pa'
  | 'likely_ai_generated'
  | 'unknown'
  | 'error';

export interface C2PAResult {
  valid: boolean;
  issuer?: string;
  trust_chain_valid: boolean;
  manifest_store?: any;
  edit_history?: string[];
  error?: string;
}

export interface SensorPKIResult {
  valid: boolean;
  manufacturer?: string;
  camera_model?: string;
  sensor_id?: string;
  signature_algorithm?: string;
  public_key_fingerprint?: string;
  error?: string;
}

export interface MLDetectionResult {
  ai_probability: number;
  cnn_score?: number;
  prnu_score?: number;
  metadata_anomaly_score?: number;
  transformer_score?: number;
  ensemble_confidence: number;
  detected_generator?: string;
  artifacts_found: string[];
}

export interface VerificationDetails {
  c2pa?: C2PAResult;
  sensor_pki?: SensorPKIResult;
  ml_detection?: MLDetectionResult;
}

export interface VerificationResult {
  job_id: string;
  status: VerificationStatus;
  label?: AuthenticityLabel;
  confidence?: number;
  reasons: string[];
  details?: VerificationDetails;
  created_at: string;
  updated_at: string;
  error_message?: string;
}

export interface VerifyResponse {
  job_id: string;
  status: VerificationStatus;
}
