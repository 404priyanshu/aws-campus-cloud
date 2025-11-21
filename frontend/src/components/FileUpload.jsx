// FileUpload.jsx - React Component for File Upload with Presigned URLs
// Demonstrates how to upload files using the Campus Cloud API

import React, { useState, useCallback } from 'react';
import { uploadFile } from '../services/api';
import { config } from '../config';

const FileUpload = ({ onUploadComplete, onError }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Handle file selection
  const handleFileSelect = useCallback((event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size
    if (file.size > config.app.maxFileSize) {
      setError(
        `File size (${(file.size / 1024 / 1024).toFixed(2)}MB) exceeds maximum allowed size (${config.app.maxFileSize / 1024 / 1024}MB)`
      );
      return;
    }

    // Validate file type
    if (!config.app.allowedFileTypes.includes(file.type)) {
      setError(`File type ${file.type} is not allowed`);
      return;
    }

    setSelectedFile(file);
    setError(null);
    setSuccess(false);
  }, []);

  // Handle drag and drop
  const handleDrop = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();

    const file = event.dataTransfer.files[0];
    if (file) {
      handleFileSelect({ target: { files: [file] } });
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  // Handle upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file to upload');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress(0);

    try {
      // Prepare metadata
      const metadata = {
        description: description.trim(),
        tags: tags
          .split(',')
          .map((tag) => tag.trim())
          .filter((tag) => tag.length > 0),
      };

      // Upload file with progress tracking
      const result = await uploadFile(
        selectedFile,
        metadata,
        (progress) => {
          setUploadProgress(progress);
        }
      );

      setSuccess(true);
      setUploadProgress(100);

      // Notify parent component
      if (onUploadComplete) {
        onUploadComplete(result.file);
      }

      // Reset form after 2 seconds
      setTimeout(() => {
        setSelectedFile(null);
        setDescription('');
        setTags('');
        setUploadProgress(0);
        setSuccess(false);
      }, 2000);

    } catch (err) {
      console.error('Upload error:', err);
      const errorMessage = err.response?.data?.message || err.message || 'Upload failed';
      setError(errorMessage);

      if (onError) {
        onError(err);
      }
    } finally {
      setUploading(false);
    }
  };

  // Clear selected file
  const handleClear = () => {
    setSelectedFile(null);
    setDescription('');
    setTags('');
    setError(null);
    setSuccess(false);
    setUploadProgress(0);
  };

  return (
    <div className="file-upload-container">
      <div className="upload-card">
        <h2>Upload File</h2>

        {/* Drag and Drop Area */}
        <div
          className={`drop-zone ${selectedFile ? 'has-file' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          {!selectedFile ? (
            <div className="drop-zone-content">
              <svg className="upload-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="17 8 12 3 7 8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <line x1="12" y1="3" x2="12" y2="15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <p className="drop-zone-text">Drag and drop a file here</p>
              <p className="drop-zone-subtext">or</p>
              <label htmlFor="file-input" className="file-input-label">
                Choose File
              </label>
              <input
                id="file-input"
                type="file"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
                accept={config.app.allowedFileTypes.join(',')}
              />
              <p className="drop-zone-hint">
                Max size: {config.app.maxFileSize / 1024 / 1024}MB
              </p>
            </div>
          ) : (
            <div className="selected-file">
              <svg className="file-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="13 2 13 9 20 9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <div className="file-details">
                <p className="file-name">{selectedFile.name}</p>
                <p className="file-size">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button
                type="button"
                onClick={handleClear}
                className="clear-button"
                disabled={uploading}
              >
                ×
              </button>
            </div>
          )}
        </div>

        {/* File Metadata */}
        {selectedFile && !success && (
          <div className="metadata-section">
            <div className="form-group">
              <label htmlFor="description">Description (optional)</label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add a description for this file..."
                maxLength={500}
                rows={3}
                disabled={uploading}
              />
              <span className="char-count">
                {description.length}/500
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="tags">Tags (optional)</label>
              <input
                id="tags"
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="lecture, week5, important (comma-separated)"
                disabled={uploading}
              />
            </div>
          </div>
        )}

        {/* Upload Progress */}
        {uploading && (
          <div className="progress-section">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="progress-text">{uploadProgress}%</p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="alert alert-error">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10" strokeWidth="2"/>
              <line x1="12" y1="8" x2="12" y2="12" strokeWidth="2" strokeLinecap="round"/>
              <line x1="12" y1="16" x2="12.01" y2="16" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="alert alert-success">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <polyline points="22 4 12 14.01 9 11.01" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>File uploaded successfully!</span>
          </div>
        )}

        {/* Upload Button */}
        {selectedFile && !success && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className={`upload-button ${uploading ? 'uploading' : ''}`}
          >
            {uploading ? (
              <>
                <span className="spinner"></span>
                Uploading...
              </>
            ) : (
              'Upload File'
            )}
          </button>
        )}
      </div>

      {/* Inline Styles - In production, use CSS file */}
      <style jsx>{`
        .file-upload-container {
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }

        .upload-card {
          background: white;
          border-radius: 12px;
          padding: 30px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .upload-card h2 {
          margin: 0 0 24px 0;
          font-size: 24px;
          font-weight: 600;
          color: #1a1a1a;
        }

        .drop-zone {
          border: 2px dashed #d1d5db;
          border-radius: 8px;
          padding: 40px;
          text-align: center;
          transition: all 0.3s ease;
          background: #f9fafb;
        }

        .drop-zone:hover {
          border-color: #3b82f6;
          background: #eff6ff;
        }

        .drop-zone.has-file {
          border-color: #10b981;
          background: #f0fdf4;
        }

        .drop-zone-content {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .upload-icon {
          color: #6b7280;
          margin-bottom: 16px;
        }

        .drop-zone-text {
          font-size: 16px;
          font-weight: 500;
          color: #374151;
          margin: 8px 0;
        }

        .drop-zone-subtext {
          font-size: 14px;
          color: #6b7280;
          margin: 8px 0;
        }

        .file-input-label {
          display: inline-block;
          padding: 10px 20px;
          background: #3b82f6;
          color: white;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: background 0.2s;
        }

        .file-input-label:hover {
          background: #2563eb;
        }

        .drop-zone-hint {
          font-size: 12px;
          color: #9ca3af;
          margin-top: 12px;
        }

        .selected-file {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .file-icon {
          color: #10b981;
          flex-shrink: 0;
        }

        .file-details {
          flex: 1;
          text-align: left;
        }

        .file-name {
          font-size: 16px;
          font-weight: 500;
          color: #1a1a1a;
          margin: 0 0 4px 0;
          word-break: break-word;
        }

        .file-size {
          font-size: 14px;
          color: #6b7280;
          margin: 0;
        }

        .clear-button {
          width: 32px;
          height: 32px;
          border: none;
          background: #ef4444;
          color: white;
          border-radius: 50%;
          font-size: 24px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s;
          flex-shrink: 0;
        }

        .clear-button:hover:not(:disabled) {
          background: #dc2626;
        }

        .clear-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .metadata-section {
          margin-top: 24px;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-group label {
          display: block;
          font-size: 14px;
          font-weight: 500;
          color: #374151;
          margin-bottom: 8px;
        }

        .form-group input,
        .form-group textarea {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
          font-family: inherit;
          transition: border-color 0.2s;
        }

        .form-group input:focus,
        .form-group textarea:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .form-group input:disabled,
        .form-group textarea:disabled {
          background: #f3f4f6;
          cursor: not-allowed;
        }

        .char-count {
          display: block;
          text-align: right;
          font-size: 12px;
          color: #9ca3af;
          margin-top: 4px;
        }

        .progress-section {
          margin-top: 24px;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background: #e5e7eb;
          border-radius: 4px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #2563eb);
          transition: width 0.3s ease;
        }

        .progress-text {
          text-align: center;
          font-size: 14px;
          font-weight: 500;
          color: #3b82f6;
          margin-top: 8px;
        }

        .alert {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          border-radius: 6px;
          margin-top: 20px;
          font-size: 14px;
        }

        .alert-error {
          background: #fee2e2;
          color: #991b1b;
          border: 1px solid #fecaca;
        }

        .alert-error svg {
          stroke: #991b1b;
          flex-shrink: 0;
        }

        .alert-success {
          background: #d1fae5;
          color: #065f46;
          border: 1px solid #a7f3d0;
        }

        .alert-success svg {
          stroke: #065f46;
          flex-shrink: 0;
        }

        .upload-button {
          width: 100%;
          padding: 14px;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s;
          margin-top: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }

        .upload-button:hover:not(:disabled) {
          background: #2563eb;
        }

        .upload-button:disabled {
          background: #9ca3af;
          cursor: not-allowed;
        }

        .upload-button.uploading {
          background: #6b7280;
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        @media (max-width: 640px) {
          .file-upload-container {
            padding: 12px;
          }

          .upload-card {
            padding: 20px;
          }

          .drop-zone {
            padding: 24px;
          }
        }
      `}</style>
    </div>
  );
};

export default FileUpload;
