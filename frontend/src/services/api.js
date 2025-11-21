// API Service for Campus Cloud Frontend
// Handles all API calls to the backend

import axios from 'axios';
import { config } from '../config';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: config.api.endpoint,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('idToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('idToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============================================
// FILE OPERATIONS
// ============================================

/**
 * Generate presigned URL for file upload
 */
export const generateUploadUrl = async (fileData) => {
  try {
    const response = await apiClient.post('/files/upload-url', {
      filename: fileData.filename,
      contentType: fileData.contentType,
      fileSize: fileData.fileSize,
      metadata: fileData.metadata || {},
    });
    return response.data;
  } catch (error) {
    console.error('Error generating upload URL:', error);
    throw error;
  }
};

/**
 * Upload file to S3 using presigned URL
 */
export const uploadFileToS3 = async (presignedData, file, onProgress) => {
  try {
    const formData = new FormData();

    // Add all presigned fields
    Object.keys(presignedData.uploadFields).forEach((key) => {
      formData.append(key, presignedData.uploadFields[key]);
    });

    // Add the file last
    formData.append('file', file);

    const response = await axios.post(presignedData.uploadUrl, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });

    return response;
  } catch (error) {
    console.error('Error uploading to S3:', error);
    throw error;
  }
};

/**
 * Complete file upload
 */
export const completeUpload = async (fileId, uploadData) => {
  try {
    const response = await apiClient.post(`/files/${fileId}/complete`, {
      uploadSuccess: uploadData.uploadSuccess,
      s3Key: uploadData.s3Key,
      checksum: uploadData.checksum,
    });
    return response.data;
  } catch (error) {
    console.error('Error completing upload:', error);
    throw error;
  }
};

/**
 * Complete file upload flow (convenience method)
 */
export const uploadFile = async (file, metadata, onProgress) => {
  try {
    // Step 1: Generate presigned URL
    const presignedData = await generateUploadUrl({
      filename: file.name,
      contentType: file.type,
      fileSize: file.size,
      metadata,
    });

    // Step 2: Upload to S3
    await uploadFileToS3(presignedData, file, onProgress);

    // Step 3: Complete upload
    const result = await completeUpload(presignedData.fileId, {
      uploadSuccess: true,
      s3Key: presignedData.uploadFields.key,
    });

    return result;
  } catch (error) {
    console.error('Error in upload flow:', error);
    throw error;
  }
};

/**
 * List user files
 */
export const listFiles = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();

    if (params.limit) queryParams.append('limit', params.limit);
    if (params.nextToken) queryParams.append('nextToken', params.nextToken);
    if (params.filter) queryParams.append('filter', params.filter);
    if (params.sortBy) queryParams.append('sortBy', params.sortBy);
    if (params.sortOrder) queryParams.append('sortOrder', params.sortOrder);

    const response = await apiClient.get(`/files?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error listing files:', error);
    throw error;
  }
};

/**
 * Get file details
 */
export const getFileDetails = async (fileId) => {
  try {
    const response = await apiClient.get(`/files/${fileId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting file details:', error);
    throw error;
  }
};

/**
 * Generate presigned download URL
 */
export const generateDownloadUrl = async (fileId, versionId = null) => {
  try {
    const params = versionId ? `?versionId=${versionId}` : '';
    const response = await apiClient.post(`/files/${fileId}/download-url${params}`);
    return response.data;
  } catch (error) {
    console.error('Error generating download URL:', error);
    throw error;
  }
};

/**
 * Download file (convenience method)
 */
export const downloadFile = async (fileId, filename) => {
  try {
    const { downloadUrl } = await generateDownloadUrl(fileId);

    // Trigger download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (error) {
    console.error('Error downloading file:', error);
    throw error;
  }
};

/**
 * Delete file
 */
export const deleteFile = async (fileId) => {
  try {
    const response = await apiClient.delete(`/files/${fileId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting file:', error);
    throw error;
  }
};

// ============================================
// FILE SHARING
// ============================================

/**
 * Share file with users
 */
export const shareFile = async (fileId, shareData) => {
  try {
    const response = await apiClient.post(`/files/${fileId}/share`, {
      recipients: shareData.recipients,
      message: shareData.message,
      expiresAt: shareData.expiresAt,
    });
    return response.data;
  } catch (error) {
    console.error('Error sharing file:', error);
    throw error;
  }
};

/**
 * List file shares
 */
export const listFileShares = async (fileId) => {
  try {
    const response = await apiClient.get(`/files/${fileId}/shares`);
    return response.data;
  } catch (error) {
    console.error('Error listing shares:', error);
    throw error;
  }
};

/**
 * Revoke file share
 */
export const revokeShare = async (fileId, shareId) => {
  try {
    const response = await apiClient.delete(`/files/${fileId}/shares/${shareId}`);
    return response.data;
  } catch (error) {
    console.error('Error revoking share:', error);
    throw error;
  }
};

/**
 * List files shared with me
 */
export const listSharedWithMe = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.nextToken) queryParams.append('nextToken', params.nextToken);

    const response = await apiClient.get(`/shared-with-me?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error listing shared files:', error);
    throw error;
  }
};

// ============================================
// ASSIGNMENTS
// ============================================

/**
 * Create assignment (instructor only)
 */
export const createAssignment = async (assignmentData) => {
  try {
    const response = await apiClient.post('/assignments', assignmentData);
    return response.data;
  } catch (error) {
    console.error('Error creating assignment:', error);
    throw error;
  }
};

/**
 * List assignments
 */
export const listAssignments = async (params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.courseId) queryParams.append('courseId', params.courseId);
    if (params.status) queryParams.append('status', params.status);
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.nextToken) queryParams.append('nextToken', params.nextToken);

    const response = await apiClient.get(`/assignments?${queryParams.toString()}`);
    return response.data;
  } catch (error) {
    console.error('Error listing assignments:', error);
    throw error;
  }
};

/**
 * Get assignment details
 */
export const getAssignment = async (assignmentId) => {
  try {
    const response = await apiClient.get(`/assignments/${assignmentId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting assignment:', error);
    throw error;
  }
};

/**
 * Submit assignment
 */
export const submitAssignment = async (assignmentId, submissionData) => {
  try {
    const response = await apiClient.post(`/assignments/${assignmentId}/submit`, {
      fileId: submissionData.fileId,
      comments: submissionData.comments,
    });
    return response.data;
  } catch (error) {
    console.error('Error submitting assignment:', error);
    throw error;
  }
};

/**
 * List assignment submissions (instructor only)
 */
export const listSubmissions = async (assignmentId, params = {}) => {
  try {
    const queryParams = new URLSearchParams();
    if (params.status) queryParams.append('status', params.status);
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.nextToken) queryParams.append('nextToken', params.nextToken);

    const response = await apiClient.get(
      `/assignments/${assignmentId}/submissions?${queryParams.toString()}`
    );
    return response.data;
  } catch (error) {
    console.error('Error listing submissions:', error);
    throw error;
  }
};

/**
 * Get my submissions for an assignment
 */
export const getMySubmissions = async (assignmentId) => {
  try {
    const response = await apiClient.get(`/assignments/${assignmentId}/submissions/me`);
    return response.data;
  } catch (error) {
    console.error('Error getting my submissions:', error);
    throw error;
  }
};

/**
 * Grade submission (instructor only)
 */
export const gradeSubmission = async (assignmentId, submissionId, gradeData) => {
  try {
    const response = await apiClient.put(
      `/assignments/${assignmentId}/submissions/${submissionId}/grade`,
      {
        grade: gradeData.grade,
        maxGrade: gradeData.maxGrade,
        feedback: gradeData.feedback,
        feedbackFileId: gradeData.feedbackFileId,
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error grading submission:', error);
    throw error;
  }
};

// ============================================
// USER OPERATIONS
// ============================================

/**
 * Get user profile
 */
export const getUserProfile = async () => {
  try {
    const response = await apiClient.get('/users/me');
    return response.data;
  } catch (error) {
    console.error('Error getting user profile:', error);
    throw error;
  }
};

/**
 * Update user profile
 */
export const updateUserProfile = async (profileData) => {
  try {
    const response = await apiClient.put('/users/me', profileData);
    return response.data;
  } catch (error) {
    console.error('Error updating user profile:', error);
    throw error;
  }
};

/**
 * Search users
 */
export const searchUsers = async (query, limit = 10) => {
  try {
    const response = await apiClient.get(`/users/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    return response.data;
  } catch (error) {
    console.error('Error searching users:', error);
    throw error;
  }
};

// ============================================
// SYSTEM
// ============================================

/**
 * Health check
 */
export const healthCheck = async () => {
  try {
    const response = await axios.get(`${config.api.endpoint}/health`);
    return response.data;
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
};

// Export all functions as default
export default {
  // Files
  generateUploadUrl,
  uploadFileToS3,
  completeUpload,
  uploadFile,
  listFiles,
  getFileDetails,
  generateDownloadUrl,
  downloadFile,
  deleteFile,

  // Sharing
  shareFile,
  listFileShares,
  revokeShare,
  listSharedWithMe,

  // Assignments
  createAssignment,
  listAssignments,
  getAssignment,
  submitAssignment,
  listSubmissions,
  getMySubmissions,
  gradeSubmission,

  // Users
  getUserProfile,
  updateUserProfile,
  searchUsers,

  // System
  healthCheck,
};
