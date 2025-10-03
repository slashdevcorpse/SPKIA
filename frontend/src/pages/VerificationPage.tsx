import React, { useState, useEffect } from 'react';
import { Shield } from 'lucide-react';
import FileUpload from '@/components/FileUpload';
import ResultDisplay from '@/components/ResultDisplay';
import { api } from '@/services/api';
import { VerificationResult } from '@/types/api';

const VerificationPage: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (jobId) {
      // Poll for results
      const pollInterval = setInterval(async () => {
        try {
          const response = await api.getVerificationResult(jobId);
          setResult(response);

          if (response.status === 'completed' || response.status === 'failed') {
            clearInterval(pollInterval);
          }
        } catch (err) {
          console.error('Error fetching result:', err);
          setError('Failed to fetch verification result');
          clearInterval(pollInterval);
        }
      }, 2000);

      return () => clearInterval(pollInterval);
    }
  }, [jobId]);

  const handleFileSelect = async (file: File) => {
    setIsUploading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.verifyFile(file);
      setJobId(response.job_id);
      setResult({
        job_id: response.job_id,
        status: response.status,
        reasons: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!jobId) return;

    try {
      await api.deleteVerification(jobId);
      setJobId(null);
      setResult(null);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete verification');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <Shield className="w-16 h-16 text-primary-500" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">SPKIA</h1>
          <p className="text-xl text-gray-600 mb-2">
            Media Authenticity Verification
          </p>
          <p className="text-sm text-gray-500">
            Privacy-preserving verification via cryptography + machine learning
          </p>
        </div>

        {/* Main Content */}
        {error && (
          <div className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-lg">
            <p className="text-danger-700">{error}</p>
          </div>
        )}

        {!result ? (
          <FileUpload onFileSelect={handleFileSelect} isUploading={isUploading} />
        ) : (
          <ResultDisplay result={result} onDelete={handleDelete} />
        )}

        {/* Info Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-semibold text-gray-800 mb-2">
              ✅ Cryptographic Proofs
            </h3>
            <p className="text-sm text-gray-600">
              Validates C2PA credentials and sensor-level PKI signatures from real
              cameras
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-semibold text-gray-800 mb-2">🤖 ML Detection</h3>
            <p className="text-sm text-gray-600">
              Ensemble classifiers detect AI-generated media when cryptographic proofs
              are absent
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="font-semibold text-gray-800 mb-2">🔒 Privacy First</h3>
            <p className="text-sm text-gray-600">
              No content storage. All data automatically deleted after 24 hours
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-sm text-gray-500">
          <p>
            SPKIA v1.0 | Open Source |{' '}
            <a href="#" className="text-primary-500 hover:text-primary-600">
              Privacy Policy
            </a>
            {' | '}
            <a href="#" className="text-primary-500 hover:text-primary-600">
              Documentation
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default VerificationPage;
