import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, HelpCircle, Loader } from 'lucide-react';
import { AuthenticityLabel, VerificationResult } from '@/types/api';

interface ResultDisplayProps {
  result: VerificationResult;
  onDelete: () => void;
}

const ResultDisplay: React.FC<ResultDisplayProps> = ({ result, onDelete }) => {
  const getStatusIcon = () => {
    if (result.status === 'processing' || result.status === 'pending') {
      return <Loader className="w-12 h-12 animate-spin text-primary-500" />;
    }

    if (result.status === 'failed' || result.label === 'error') {
      return <XCircle className="w-12 h-12 text-danger-500" />;
    }

    switch (result.label) {
      case 'authentic_camera':
      case 'authentic_c2pa':
        return <CheckCircle className="w-12 h-12 text-success-500" />;
      case 'likely_ai_generated':
        return <AlertTriangle className="w-12 h-12 text-warning-500" />;
      case 'unknown':
        return <HelpCircle className="w-12 h-12 text-gray-500" />;
      default:
        return null;
    }
  };

  const getLabelText = (label?: AuthenticityLabel) => {
    switch (label) {
      case 'authentic_camera':
        return 'Authentic (Camera)';
      case 'authentic_c2pa':
        return 'Authentic (C2PA)';
      case 'likely_ai_generated':
        return 'Likely AI-Generated';
      case 'unknown':
        return 'Unknown';
      case 'error':
        return 'Error';
      default:
        return 'Processing...';
    }
  };

  const getLabelColor = (label?: AuthenticityLabel) => {
    switch (label) {
      case 'authentic_camera':
      case 'authentic_c2pa':
        return 'text-success-600';
      case 'likely_ai_generated':
        return 'text-warning-600';
      case 'unknown':
        return 'text-gray-600';
      case 'error':
        return 'text-danger-600';
      default:
        return 'text-primary-600';
    }
  };

  const isProcessing = result.status === 'processing' || result.status === 'pending';

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <div className="flex flex-col items-center mb-6">
        {getStatusIcon()}
        <h2 className={`text-2xl font-bold mt-4 ${getLabelColor(result.label)}`}>
          {getLabelText(result.label)}
        </h2>
        {result.confidence !== undefined && !isProcessing && (
          <p className="text-sm text-gray-600 mt-2">
            Confidence: {(result.confidence * 100).toFixed(1)}%
          </p>
        )}
      </div>

      {isProcessing && (
        <p className="text-center text-gray-600 mb-4">
          Analyzing media file... This may take a few seconds.
        </p>
      )}

      {result.status === 'completed' && result.reasons.length > 0 && (
        <div className="mb-6">
          <h3 className="font-semibold text-gray-700 mb-2">Verification Details:</h3>
          <ul className="space-y-2">
            {result.reasons.map((reason, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2 text-primary-500">•</span>
                <span className="text-gray-700">{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.error_message && (
        <div className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded">
          <p className="text-danger-700">
            <strong>Error:</strong> {result.error_message}
          </p>
        </div>
      )}

      {result.details && result.status === 'completed' && (
        <div className="mt-6 border-t pt-6">
          <h3 className="font-semibold text-gray-700 mb-4">Technical Details:</h3>

          {result.details.c2pa && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2">C2PA Verification:</h4>
              <div className="bg-gray-50 p-3 rounded text-sm">
                <p>
                  <strong>Valid:</strong> {result.details.c2pa.valid ? 'Yes' : 'No'}
                </p>
                {result.details.c2pa.issuer && (
                  <p>
                    <strong>Issuer:</strong> {result.details.c2pa.issuer}
                  </p>
                )}
                <p>
                  <strong>Trust Chain:</strong>{' '}
                  {result.details.c2pa.trust_chain_valid ? 'Valid' : 'Invalid'}
                </p>
              </div>
            </div>
          )}

          {result.details.sensor_pki && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2">Sensor-PKI Verification:</h4>
              <div className="bg-gray-50 p-3 rounded text-sm">
                <p>
                  <strong>Valid:</strong> {result.details.sensor_pki.valid ? 'Yes' : 'No'}
                </p>
                {result.details.sensor_pki.manufacturer && (
                  <p>
                    <strong>Manufacturer:</strong> {result.details.sensor_pki.manufacturer}
                  </p>
                )}
                {result.details.sensor_pki.camera_model && (
                  <p>
                    <strong>Camera Model:</strong> {result.details.sensor_pki.camera_model}
                  </p>
                )}
              </div>
            </div>
          )}

          {result.details.ml_detection && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2">ML Detection:</h4>
              <div className="bg-gray-50 p-3 rounded text-sm">
                <p>
                  <strong>AI Probability:</strong>{' '}
                  {(result.details.ml_detection.ai_probability * 100).toFixed(1)}%
                </p>
                <p>
                  <strong>Ensemble Confidence:</strong>{' '}
                  {(result.details.ml_detection.ensemble_confidence * 100).toFixed(1)}%
                </p>
                {result.details.ml_detection.detected_generator && (
                  <p>
                    <strong>Detected Generator:</strong>{' '}
                    {result.details.ml_detection.detected_generator}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-6 flex gap-4">
        <button
          onClick={onDelete}
          className="flex-1 px-6 py-3 bg-danger-500 text-white rounded-lg hover:bg-danger-600 transition-colors"
        >
          Delete Data Now
        </button>
        <button
          onClick={() => window.location.reload()}
          className="flex-1 px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          Verify Another File
        </button>
      </div>

      <p className="text-xs text-gray-500 mt-4 text-center">
        All data will be automatically deleted after 24 hours
      </p>
    </div>
  );
};

export default ResultDisplay;
