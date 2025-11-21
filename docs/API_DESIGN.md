# Campus Cloud API Design

## Base URL
```
Production: https://api.campuscloud.edu/v1
Development: https://dev-api.campuscloud.edu/v1
```

## Authentication

All API endpoints (except public health checks) require authentication via AWS Cognito JWT tokens.

### Headers
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

### User Attributes in JWT
- `sub`: User ID (UUID)
- `email`: User email
- `cognito:groups`: User role (student, instructor, admin)
- `custom:university_id`: University student/staff ID

---

## API Endpoints

### 1. File Management

#### 1.1 Generate Presigned Upload URL

**Endpoint**: `POST /files/upload-url`

**Description**: Generates a presigned URL for uploading a file directly to S3.

**Request Body**:
```json
{
  "filename": "lecture-notes.pdf",
  "contentType": "application/pdf",
  "fileSize": 1048576,
  "metadata": {
    "description": "Week 5 Lecture Notes",
    "tags": ["lecture", "week5"]
  }
}
```

**Request Schema**:
```json
{
  "filename": "string (required, max 255 chars)",
  "contentType": "string (required, MIME type)",
  "fileSize": "integer (required, max 100MB = 104857600 bytes)",
  "metadata": {
    "description": "string (optional, max 500 chars)",
    "tags": "array of strings (optional, max 10 tags)"
  }
}
```

**Response** (200 OK):
```json
{
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "uploadUrl": "https://campus-cloud-bucket.s3.amazonaws.com/...",
  "uploadFields": {
    "key": "users/u123/files/f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
    "AWSAccessKeyId": "AKIAIOSFODNN7EXAMPLE",
    "policy": "eyJleHBpcmF0aW9uIjogIjIwMjMt...",
    "signature": "abcdef1234567890"
  },
  "expiresIn": 300,
  "uploadMethod": "POST"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid file size or type
- `401 Unauthorized`: Missing or invalid JWT token
- `413 Payload Too Large`: File exceeds size limit

---

#### 1.2 Complete Upload

**Endpoint**: `POST /files/{fileId}/complete`

**Description**: Marks upload as complete and creates metadata record in DynamoDB.

**Path Parameters**:
- `fileId`: UUID of the file

**Request Body**:
```json
{
  "uploadSuccess": true,
  "s3Key": "users/u123/files/f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "checksum": "5d41402abc4b2a76b9719d911017c592"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "file": {
    "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
    "filename": "lecture-notes.pdf",
    "fileSize": 1048576,
    "contentType": "application/pdf",
    "uploadedAt": "2024-01-15T10:30:00Z",
    "status": "active",
    "s3Key": "users/u123/files/f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
    "owner": {
      "userId": "u123",
      "email": "student@university.edu"
    }
  }
}
```

**Error Responses**:
- `404 Not Found`: File ID not found
- `409 Conflict`: File already completed
- `500 Internal Server Error`: Database error

---

#### 1.3 List Files

**Endpoint**: `GET /files`

**Description**: Lists all files owned by or shared with the authenticated user.

**Query Parameters**:
- `limit`: Number of items (default: 20, max: 100)
- `nextToken`: Pagination token
- `filter`: Filter type (all, owned, shared)
- `sortBy`: Sort field (uploadedAt, filename, fileSize)
- `sortOrder`: Sort order (asc, desc)

**Example**: `GET /files?limit=50&filter=owned&sortBy=uploadedAt&sortOrder=desc`

**Response** (200 OK):
```json
{
  "files": [
    {
      "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
      "filename": "lecture-notes.pdf",
      "fileSize": 1048576,
      "contentType": "application/pdf",
      "uploadedAt": "2024-01-15T10:30:00Z",
      "status": "active",
      "owner": {
        "userId": "u123",
        "email": "student@university.edu"
      },
      "metadata": {
        "description": "Week 5 Lecture Notes",
        "tags": ["lecture", "week5"]
      },
      "isOwner": true,
      "sharedWith": 3
    }
  ],
  "total": 42,
  "nextToken": "eyJsYXN0RXZhbHVhdGVkS2V5Ijp7InVzZXJJ..."
}
```

---

#### 1.4 Get File Details

**Endpoint**: `GET /files/{fileId}`

**Description**: Retrieves detailed information about a specific file.

**Path Parameters**:
- `fileId`: UUID of the file

**Response** (200 OK):
```json
{
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "filename": "lecture-notes.pdf",
  "fileSize": 1048576,
  "contentType": "application/pdf",
  "uploadedAt": "2024-01-15T10:30:00Z",
  "lastModified": "2024-01-15T10:30:00Z",
  "status": "active",
  "owner": {
    "userId": "u123",
    "email": "student@university.edu",
    "name": "John Doe"
  },
  "metadata": {
    "description": "Week 5 Lecture Notes",
    "tags": ["lecture", "week5"]
  },
  "versions": [
    {
      "versionId": "v1",
      "uploadedAt": "2024-01-15T10:30:00Z",
      "fileSize": 1048576
    }
  ],
  "shares": [
    {
      "sharedWith": "u456",
      "email": "friend@university.edu",
      "sharedAt": "2024-01-15T11:00:00Z",
      "permissions": "read"
    }
  ],
  "downloadCount": 15
}
```

**Error Responses**:
- `403 Forbidden`: No access to this file
- `404 Not Found`: File doesn't exist

---

#### 1.5 Generate Presigned Download URL

**Endpoint**: `POST /files/{fileId}/download-url`

**Description**: Generates a presigned URL for downloading a file from S3.

**Path Parameters**:
- `fileId`: UUID of the file

**Query Parameters**:
- `versionId`: Specific version to download (optional)

**Response** (200 OK):
```json
{
  "downloadUrl": "https://campus-cloud-bucket.s3.amazonaws.com/...",
  "filename": "lecture-notes.pdf",
  "contentType": "application/pdf",
  "fileSize": 1048576,
  "expiresIn": 900
}
```

---

#### 1.6 Delete File

**Endpoint**: `DELETE /files/{fileId}`

**Description**: Soft deletes a file (marks as deleted, actual deletion after retention period).

**Path Parameters**:
- `fileId`: UUID of the file

**Response** (200 OK):
```json
{
  "success": true,
  "message": "File marked for deletion",
  "deletionDate": "2024-02-15T10:30:00Z"
}
```

**Error Responses**:
- `403 Forbidden`: Not the file owner
- `404 Not Found`: File doesn't exist

---

### 2. File Sharing

#### 2.1 Share File

**Endpoint**: `POST /files/{fileId}/share`

**Description**: Shares a file with other users by email.

**Path Parameters**:
- `fileId`: UUID of the file

**Request Body**:
```json
{
  "recipients": [
    {
      "email": "friend@university.edu",
      "permissions": "read"
    },
    {
      "email": "classmate@university.edu",
      "permissions": "read"
    }
  ],
  "message": "Here are the lecture notes you requested!",
  "expiresAt": "2024-02-15T23:59:59Z"
}
```

**Request Schema**:
```json
{
  "recipients": [
    {
      "email": "string (required, valid email)",
      "permissions": "enum: read (future: write)"
    }
  ],
  "message": "string (optional, max 500 chars)",
  "expiresAt": "ISO8601 datetime (optional)"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "shared": [
    {
      "shareId": "s1a2b3c4-5d6e-7f8g-9h0i-1j2k3l4m5n6o",
      "email": "friend@university.edu",
      "sharedAt": "2024-01-15T12:00:00Z",
      "expiresAt": "2024-02-15T23:59:59Z",
      "status": "active"
    }
  ],
  "failed": []
}
```

**Error Responses**:
- `403 Forbidden`: Not the file owner
- `404 Not Found`: File doesn't exist
- `400 Bad Request`: Invalid recipient email

---

#### 2.2 List File Shares

**Endpoint**: `GET /files/{fileId}/shares`

**Description**: Lists all active shares for a file.

**Path Parameters**:
- `fileId`: UUID of the file

**Response** (200 OK):
```json
{
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "filename": "lecture-notes.pdf",
  "shares": [
    {
      "shareId": "s1a2b3c4-5d6e-7f8g-9h0i-1j2k3l4m5n6o",
      "sharedWith": {
        "userId": "u456",
        "email": "friend@university.edu",
        "name": "Jane Smith"
      },
      "sharedAt": "2024-01-15T12:00:00Z",
      "expiresAt": "2024-02-15T23:59:59Z",
      "permissions": "read",
      "status": "active"
    }
  ],
  "total": 3
}
```

---

#### 2.3 Revoke Share

**Endpoint**: `DELETE /files/{fileId}/shares/{shareId}`

**Description**: Revokes access to a shared file.

**Path Parameters**:
- `fileId`: UUID of the file
- `shareId`: UUID of the share

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Share access revoked"
}
```

---

#### 2.4 List Shared With Me

**Endpoint**: `GET /shared-with-me`

**Description**: Lists all files shared with the authenticated user.

**Query Parameters**:
- `limit`: Number of items (default: 20, max: 100)
- `nextToken`: Pagination token

**Response** (200 OK):
```json
{
  "files": [
    {
      "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
      "filename": "shared-document.pdf",
      "fileSize": 2097152,
      "contentType": "application/pdf",
      "sharedBy": {
        "userId": "u789",
        "email": "professor@university.edu",
        "name": "Dr. Smith"
      },
      "sharedAt": "2024-01-14T09:00:00Z",
      "expiresAt": "2024-02-14T09:00:00Z",
      "permissions": "read"
    }
  ],
  "total": 8,
  "nextToken": null
}
```

---

### 3. Assignments

#### 3.1 Create Assignment (Instructor Only)

**Endpoint**: `POST /assignments`

**Description**: Creates a new assignment for students to submit files.

**Request Body**:
```json
{
  "title": "Programming Assignment 1",
  "description": "Implement a binary search tree in Python",
  "courseId": "CS101",
  "dueDate": "2024-02-01T23:59:59Z",
  "maxFileSize": 10485760,
  "allowedFileTypes": ["application/pdf", "text/plain", "application/zip"],
  "maxSubmissions": 3,
  "instructions": "Submit a single PDF with your code and documentation"
}
```

**Response** (201 Created):
```json
{
  "assignmentId": "a1b2c3d4-e5f6-7g8h-9i0j-1k2l3m4n5o6p",
  "title": "Programming Assignment 1",
  "description": "Implement a binary search tree in Python",
  "courseId": "CS101",
  "instructor": {
    "userId": "u999",
    "email": "professor@university.edu",
    "name": "Dr. Smith"
  },
  "createdAt": "2024-01-15T14:00:00Z",
  "dueDate": "2024-02-01T23:59:59Z",
  "status": "active",
  "submissionCount": 0
}
```

**Error Responses**:
- `403 Forbidden`: Not an instructor

---

#### 3.2 List Assignments

**Endpoint**: `GET /assignments`

**Description**: Lists all assignments (students see assigned, instructors see created).

**Query Parameters**:
- `courseId`: Filter by course (optional)
- `status`: Filter by status (active, closed, draft)
- `limit`: Number of items (default: 20, max: 100)
- `nextToken`: Pagination token

**Response** (200 OK):
```json
{
  "assignments": [
    {
      "assignmentId": "a1b2c3d4-e5f6-7g8h-9i0j-1k2l3m4n5o6p",
      "title": "Programming Assignment 1",
      "courseId": "CS101",
      "courseName": "Introduction to Computer Science",
      "instructor": {
        "name": "Dr. Smith",
        "email": "professor@university.edu"
      },
      "createdAt": "2024-01-15T14:00:00Z",
      "dueDate": "2024-02-01T23:59:59Z",
      "status": "active",
      "submissionCount": 45,
      "mySubmissions": 1,
      "hasSubmitted": true
    }
  ],
  "total": 12,
  "nextToken": null
}
```

---

#### 3.3 Get Assignment Details

**Endpoint**: `GET /assignments/{assignmentId}`

**Description**: Retrieves detailed information about an assignment.

**Path Parameters**:
- `assignmentId`: UUID of the assignment

**Response** (200 OK):
```json
{
  "assignmentId": "a1b2c3d4-e5f6-7g8h-9i0j-1k2l3m4n5o6p",
  "title": "Programming Assignment 1",
  "description": "Implement a binary search tree in Python",
  "instructions": "Submit a single PDF with your code and documentation",
  "courseId": "CS101",
  "courseName": "Introduction to Computer Science",
  "instructor": {
    "userId": "u999",
    "email": "professor@university.edu",
    "name": "Dr. Smith"
  },
  "createdAt": "2024-01-15T14:00:00Z",
  "dueDate": "2024-02-01T23:59:59Z",
  "status": "active",
  "maxFileSize": 10485760,
  "allowedFileTypes": ["application/pdf", "text/plain", "application/zip"],
  "maxSubmissions": 3,
  "submissionCount": 45,
  "mySubmissions": [
    {
      "submissionId": "sub1",
      "submittedAt": "2024-01-20T15:30:00Z",
      "fileId": "f123",
      "filename": "assignment1.pdf",
      "status": "submitted"
    }
  ]
}
```

---

#### 3.4 Submit Assignment

**Endpoint**: `POST /assignments/{assignmentId}/submit`

**Description**: Submits a file for an assignment.

**Path Parameters**:
- `assignmentId`: UUID of the assignment

**Request Body**:
```json
{
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "comments": "This is my final submission"
}
```

**Response** (201 Created):
```json
{
  "submissionId": "sub1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
  "assignmentId": "a1b2c3d4-e5f6-7g8h-9i0j-1k2l3m4n5o6p",
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "filename": "assignment1.pdf",
  "student": {
    "userId": "u123",
    "email": "student@university.edu",
    "name": "John Doe"
  },
  "submittedAt": "2024-01-20T15:30:00Z",
  "status": "submitted",
  "isLate": false,
  "comments": "This is my final submission"
}
```

**Error Responses**:
- `400 Bad Request`: File doesn't meet requirements
- `403 Forbidden`: Deadline passed or max submissions reached
- `404 Not Found`: Assignment or file not found

---

#### 3.5 List Submissions (Instructor Only)

**Endpoint**: `GET /assignments/{assignmentId}/submissions`

**Description**: Lists all submissions for an assignment.

**Path Parameters**:
- `assignmentId`: UUID of the assignment

**Query Parameters**:
- `status`: Filter by status (submitted, graded)
- `limit`: Number of items (default: 50, max: 100)
- `nextToken`: Pagination token

**Response** (200 OK):
```json
{
  "assignmentId": "a1b2c3d4-e5f6-7g8h-9i0j-1k2l3m4n5o6p",
  "assignmentTitle": "Programming Assignment 1",
  "submissions": [
    {
      "submissionId": "sub1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
      "student": {
        "userId": "u123",
        "email": "student@university.edu",
        "name": "John Doe",
        "studentId": "S12345"
      },
      "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
      "filename": "assignment1.pdf",
      "fileSize": 1048576,
      "submittedAt": "2024-01-20T15:30:00Z",
      "status": "submitted",
      "isLate": false,
      "grade": null,
      "feedback": null
    }
  ],
  "total": 45,
  "statistics": {
    "totalSubmissions": 45,
    "onTime": 42,
    "late": 3,
    "pending": 5
  },
  "nextToken": null
}
```

---

#### 3.6 Grade Submission (Instructor Only)

**Endpoint**: `PUT /assignments/{assignmentId}/submissions/{submissionId}/grade`

**Description**: Adds a grade and feedback to a submission.

**Path Parameters**:
- `assignmentId`: UUID of the assignment
- `submissionId`: UUID of the submission

**Request Body**:
```json
{
  "grade": 95,
  "maxGrade": 100,
  "feedback": "Excellent work! Well-structured code and clear documentation.",
  "feedbackFileId": "f-feedback-123"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "submission": {
    "submissionId": "sub1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
    "grade": 95,
    "maxGrade": 100,
    "feedback": "Excellent work! Well-structured code and clear documentation.",
    "gradedAt": "2024-01-21T10:00:00Z",
    "gradedBy": {
      "userId": "u999",
      "email": "professor@university.edu",
      "name": "Dr. Smith"
    },
    "status": "graded"
  }
}
```

---

### 4. User Management

#### 4.1 Get User Profile

**Endpoint**: `GET /users/me`

**Description**: Retrieves the authenticated user's profile.

**Response** (200 OK):
```json
{
  "userId": "u123",
  "email": "student@university.edu",
  "name": "John Doe",
  "role": "student",
  "studentId": "S12345",
  "createdAt": "2024-01-01T00:00:00Z",
  "statistics": {
    "totalFiles": 25,
    "totalStorage": 52428800,
    "filesShared": 8,
    "filesReceived": 12,
    "assignmentsSubmitted": 15
  }
}
```

---

#### 4.2 Update User Profile

**Endpoint**: `PUT /users/me`

**Description**: Updates the authenticated user's profile.

**Request Body**:
```json
{
  "name": "John Michael Doe",
  "notificationPreferences": {
    "emailNotifications": true,
    "shareNotifications": true,
    "assignmentReminders": true
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "user": {
    "userId": "u123",
    "email": "student@university.edu",
    "name": "John Michael Doe",
    "updatedAt": "2024-01-15T16:00:00Z"
  }
}
```

---

#### 4.3 Search Users

**Endpoint**: `GET /users/search`

**Description**: Searches for users by email or name (for sharing files).

**Query Parameters**:
- `q`: Search query (email or name)
- `limit`: Number of results (default: 10, max: 50)

**Example**: `GET /users/search?q=john&limit=10`

**Response** (200 OK):
```json
{
  "users": [
    {
      "userId": "u123",
      "email": "john.doe@university.edu",
      "name": "John Doe",
      "role": "student"
    },
    {
      "userId": "u456",
      "email": "john.smith@university.edu",
      "name": "John Smith",
      "role": "student"
    }
  ],
  "total": 2
}
```

---

### 5. System Endpoints

#### 5.1 Health Check

**Endpoint**: `GET /health`

**Description**: Checks API health status (no authentication required).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T16:30:00Z",
  "version": "1.0.0",
  "services": {
    "dynamodb": "healthy",
    "s3": "healthy",
    "cognito": "healthy"
  }
}
```

---

## Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "fieldName",
      "reason": "Specific reason for the error"
    },
    "requestId": "req-123abc456def",
    "timestamp": "2024-01-15T16:30:00Z"
  }
}
```

### Common Error Codes

- `UNAUTHORIZED`: Missing or invalid authentication token
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `BAD_REQUEST`: Invalid request parameters
- `CONFLICT`: Resource conflict (e.g., duplicate)
- `PAYLOAD_TOO_LARGE`: Request body or file too large
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_SERVER_ERROR`: Server error

---

## Rate Limiting

- **Authenticated requests**: 1000 requests per hour per user
- **File uploads**: 50 uploads per hour per user
- **Downloads**: 200 downloads per hour per user

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1642257600
```

---

## Pagination

All list endpoints support pagination with:
- `limit`: Number of items per page
- `nextToken`: Opaque token for next page

Response includes:
```json
{
  "items": [...],
  "nextToken": "eyJsYXN0RXZhbHVhdGVkS2V5Ijp7...",
  "total": 150
}
```

---

## Filtering and Sorting

Supported query parameters:
- `filter`: Field-based filtering
- `sortBy`: Sort field name
- `sortOrder`: `asc` or `desc`

Example:
```
GET /files?filter=contentType:application/pdf&sortBy=uploadedAt&sortOrder=desc
```

---

## Versioning

API version is included in the URL path: `/v1/`

Breaking changes will result in a new version: `/v2/`

Non-breaking changes (additions) are made to existing versions.

---

## CORS Configuration

Allowed origins:
- `https://campuscloud.edu`
- `https://dev.campuscloud.edu`
- `http://localhost:3000` (development only)

Allowed methods: `GET, POST, PUT, DELETE, OPTIONS`

Allowed headers: `Authorization, Content-Type, X-Requested-With`

---

## WebSocket API (Optional - Real-time Notifications)

**Connection URL**: `wss://ws.campuscloud.edu`

**Authentication**: JWT token in query string `?token=<JWT>`

**Message Format**:
```json
{
  "action": "subscribe",
  "topic": "files.shared"
}
```

**Notification Types**:
- `file.shared`: File shared with you
- `file.submitted`: Student submits assignment
- `submission.graded`: Submission graded by instructor
- `assignment.created`: New assignment posted

---

## SDK Examples

### JavaScript/TypeScript
```javascript
import { CampusCloudClient } from '@campuscloud/sdk';

const client = new CampusCloudClient({
  apiUrl: 'https://api.campuscloud.edu/v1',
  auth: {
    token: 'jwt-token'
  }
});

// Upload file
const { uploadUrl, fileId } = await client.files.getUploadUrl({
  filename: 'document.pdf',
  contentType: 'application/pdf',
  fileSize: 1048576
});

// Complete upload
await client.files.completeUpload(fileId, { uploadSuccess: true });
```

### Python
```python
from campuscloud import CampusCloudClient

client = CampusCloudClient(
    api_url='https://api.campuscloud.edu/v1',
    token='jwt-token'
)

# List files
files = client.files.list(limit=50, filter='owned')
```

---

## Testing

### Postman Collection
Import the provided Postman collection: `campus-cloud-api.postman_collection.json`

### Test Accounts
- Student: `student@test.university.edu` / `TestPass123!`
- Instructor: `instructor@test.university.edu` / `TestPass123!`

### Sandbox Environment
- API: `https://sandbox-api.campuscloud.edu/v1`
- No rate limiting
- Data reset daily