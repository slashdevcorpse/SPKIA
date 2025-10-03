/**
 * API client for SPKIA backend
 */
import axios from 'axios';
import { VerifyResponse, VerificationResult } from '@/types/api';

// Use environment variable or empty string for relative URLs (proxied by nginx)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL !== undefined 
  ? import.meta.env.VITE_API_BASE_URL 
  : 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  /**
   * Upload and verify a file
   */
  async verifyFile(file: File): Promise<VerifyResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<VerifyResponse>(
      '/api/verify',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Verify a file from URL
   */
  async verifyUrl(url: string): Promise<VerifyResponse> {
    const response = await apiClient.post<VerifyResponse>('/api/verify-url', {
      url,
    });

    return response.data;
  },

  /**
   * Get verification result
   */
  async getVerificationResult(jobId: string): Promise<VerificationResult> {
    const response = await apiClient.get<VerificationResult>(
      `/api/verify/${jobId}`
    );

    return response.data;
  },

  /**
   * Delete verification job
   */
  async deleteVerification(jobId: string): Promise<void> {
    await apiClient.delete(`/api/verify/${jobId}`);
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<any> {
    const response = await apiClient.get('/health');
    return response.data;
  },
};
