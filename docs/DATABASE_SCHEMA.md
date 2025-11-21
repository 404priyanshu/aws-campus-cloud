# Campus Cloud - DynamoDB Table Schema

## Overview

This document describes the DynamoDB table design for the Campus Cloud File Sharing System. The design follows single-table design principles where appropriate and uses multiple tables for clear separation of concerns.

---

## Table 1: Files

**Table Name**: `campus-cloud-files`

**Purpose**: Stores metadata for all uploaded files

### Primary Key Structure

- **Partition Key (PK)**: `userId` (String) - Owner's user ID
- **Sort Key (SK)**: `fileId` (String) - Unique file identifier (UUID)

### Attributes

| Attribute | Type | Description | Required |
|-----------|------|-------------|----------|
| userId | String | File owner's user ID | Yes |
| fileId | String | Unique file identifier (UUID) | Yes |
| filename | String | Original filename | Yes |
| fileSize | Number | File size in bytes | Yes |
| contentType | String | MIME type | Yes |
| s3Key | String | S3 object key | Yes |
| s3Bucket | String | S3 bucket name | Yes |
| status | String | File status (active, deleted, quarantined) | Yes |
| uploadedAt | String | ISO8601 timestamp | Yes |
| lastModified | String | ISO8601 timestamp | Yes |
| checksum | String | MD5 or SHA256 checksum | No |
| versionId | String | S3 version ID (if versioning enabled) | No |
| description | String | User-provided description | No |
| tags | List | Array of tag strings | No |
| metadata | Map | Additional custom metadata | No |
| downloadCount | Number | Number of times downloaded | Yes (default: 0) |
| isPublic | Boolean | Public access flag | Yes (default: false) |
| deletedAt | String | ISO8601 timestamp (soft delete) | No |
| virusScanStatus | String | Scan status (pending, clean, infected) | No |
| virusScanDate | String | ISO8601 timestamp of last scan | No |

### Global Secondary Indexes (GSI)

#### GSI-1: FileIdIndex
**Purpose**: Look up file by fileId across all users

- **Partition Key**: `fileId` (String)
- **Projection**: ALL
- **Use Case**: Direct file access, sharing validation

#### GSI-2: StatusIndex
**Purpose**: Query files by status and date

- **Partition Key**: `status` (String)
- **Sort Key**: `uploadedAt` (String)
- **Projection**: ALL
- **Use Case**: Admin operations, cleanup jobs

### Access Patterns

1. **Get user's files**: Query by PK (userId)
2. **Get specific file**: Query by PK (userId) + SK (fileId)
3. **Get file by ID only**: Query GSI-1 by fileId
4. **List active files**: Query GSI-2 where status = "active"
5. **List deleted files for cleanup**: Query GSI-2 where status = "deleted"

### Example Items

```json
{
  "userId": "u123-456-789",
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "filename": "lecture-notes-week5.pdf",
  "fileSize": 1048576,
  "contentType": "application/pdf",
  "s3Key": "users/u123-456-789/files/f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "s3Bucket": "campus-cloud-files-prod",
  "status": "active",
  "uploadedAt": "2024-01-15T10:30:00.000Z",
  "lastModified": "2024-01-15T10:30:00.000Z",
  "checksum": "5d41402abc4b2a76b9719d911017c592",
  "versionId": "v1.0",
  "description": "Computer Science 101 - Week 5 Lecture Notes",
  "tags": ["cs101", "lecture", "week5"],
  "metadata": {
    "semester": "Spring 2024",
    "course": "CS101"
  },
  "downloadCount": 15,
  "isPublic": false,
  "virusScanStatus": "clean",
  "virusScanDate": "2024-01-15T10:31:00.000Z"
}
```

---

## Table 2: Shares

**Table Name**: `campus-cloud-shares`

**Purpose**: Manages file sharing permissions between users

### Primary Key Structure

- **Partition Key (PK)**: `fileId` (String) - Shared file ID
- **Sort Key (SK)**: `sharedWithUserId` (String) - Recipient user ID

### Attributes

| Attribute | Type | Description | Required |
|-----------|------|-------------|----------|
| shareId | String | Unique share identifier (UUID) | Yes |
| fileId | String | File being shared | Yes |
| ownerId | String | File owner's user ID | Yes |
| sharedWithUserId | String | Recipient's user ID | Yes |
| sharedWithEmail | String | Recipient's email | Yes |
| permissions | String | Access level (read, write) | Yes |
| sharedAt | String | ISO8601 timestamp | Yes |
| expiresAt | String | ISO8601 timestamp | No |
| status | String | Share status (active, revoked, expired) | Yes |
| message | String | Optional message from sharer | No |
| accessCount | Number | Times accessed by recipient | Yes (default: 0) |
| lastAccessedAt | String | ISO8601 timestamp | No |

### Global Secondary Indexes (GSI)

#### GSI-1: SharedWithUserIndex
**Purpose**: Find all files shared with a specific user

- **Partition Key**: `sharedWithUserId` (String)
- **Sort Key**: `sharedAt` (String)
- **Projection**: ALL
- **Use Case**: "Shared with me" view

#### GSI-2: ShareIdIndex
**Purpose**: Look up share by shareId

- **Partition Key**: `shareId` (String)
- **Projection**: ALL
- **Use Case**: Revoke share by ID

### Local Secondary Index (LSI)

#### LSI-1: FileExpirationIndex
**Purpose**: Query shares by expiration date

- **Partition Key**: `fileId` (String)
- **Sort Key**: `expiresAt` (String)
- **Projection**: ALL
- **Use Case**: Expired share cleanup

### Time-to-Live (TTL)

- **TTL Attribute**: `ttl` (Number) - Unix timestamp
- **Behavior**: Automatically delete expired shares

### Access Patterns

1. **Get file's shares**: Query by PK (fileId)
2. **Get shares for user**: Query GSI-1 by sharedWithUserId
3. **Check specific share**: Get by PK (fileId) + SK (sharedWithUserId)
4. **Revoke share**: Query GSI-2 by shareId, then delete
5. **Find expired shares**: Query LSI-1 where expiresAt < now

### Example Items

```json
{
  "shareId": "s1a2b3c4-5d6e-7f8g-9h0i-1j2k3l4m5n6o",
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "ownerId": "u123-456-789",
  "sharedWithUserId": "u987-654-321",
  "sharedWithEmail": "friend@university.edu",
  "permissions": "read",
  "sharedAt": "2024-01-15T12:00:00.000Z",
  "expiresAt": "2024-02-15T23:59:59.000Z",
  "status": "active",
  "message": "Here are the lecture notes you requested!",
  "accessCount": 3,
  "lastAccessedAt": "2024-01-16T09:30:00.000Z",
  "ttl": 1708041599
}
```

---

## Table 3: Assignments

**Table Name**: `campus-cloud-assignments`

**Purpose**: Stores assignment information created by instructors

### Primary Key Structure

- **Partition Key (PK)**: `courseId` (String) - Course identifier
- **Sort Key (SK)**: `assignmentId` (String) - Unique assignment ID (UUID)

### Attributes

| Attribute | Type | Description | Required |
|-----------|------|-------------|----------|
| assignmentId | String | Unique assignment identifier (UUID) | Yes |
| courseId | String | Course identifier | Yes |
| courseName | String | Course name | Yes |
| title | String | Assignment title | Yes |
| description | String | Assignment description | Yes |
| instructions | String | Detailed instructions | No |
| instructorId | String | Instructor's user ID | Yes |
| instructorEmail | String | Instructor's email | Yes |
| instructorName | String | Instructor's name | Yes |
| createdAt | String | ISO8601 timestamp | Yes |
| updatedAt | String | ISO8601 timestamp | Yes |
| dueDate | String | ISO8601 timestamp | Yes |
| status | String | Assignment status (draft, active, closed) | Yes |
| maxFileSize | Number | Max file size in bytes | Yes |
| allowedFileTypes | List | Array of allowed MIME types | Yes |
| maxSubmissions | Number | Max submissions per student | Yes (default: 1) |
| submissionCount | Number | Total submissions received | Yes (default: 0) |
| points | Number | Assignment point value | No |
| rubricUrl | String | Link to grading rubric | No |
| attachments | List | Reference files from instructor | No |

### Global Secondary Indexes (GSI)

#### GSI-1: InstructorIndex
**Purpose**: Query assignments by instructor

- **Partition Key**: `instructorId` (String)
- **Sort Key**: `createdAt` (String)
- **Projection**: ALL
- **Use Case**: Instructor dashboard

#### GSI-2: StatusDueDateIndex
**Purpose**: Query assignments by status and due date

- **Partition Key**: `status` (String)
- **Sort Key**: `dueDate` (String)
- **Projection**: ALL
- **Use Case**: Upcoming assignments, overdue assignments

#### GSI-3: AssignmentIdIndex
**Purpose**: Direct assignment lookup

- **Partition Key**: `assignmentId` (String)
- **Projection**: ALL
- **Use Case**: Assignment details without courseId

### Access Patterns

1. **Get course assignments**: Query by PK (courseId)
2. **Get specific assignment**: Query by PK (courseId) + SK (assignmentId)
3. **Get instructor's assignments**: Query GSI-1 by instructorId
4. **Get active assignments**: Query GSI-2 where status = "active"
5. **Get assignment by ID**: Query GSI-3 by assignmentId

### Example Items

```json
{
  "assignmentId": "a1b2c3d4-e5f6-7g8h-9i0j-1k2l3m4n5o6p",
  "courseId": "CS101-2024-SPRING",
  "courseName": "Introduction to Computer Science",
  "title": "Programming Assignment 1: Binary Search Tree",
  "description": "Implement a binary search tree with insert, delete, and search operations",
  "instructions": "Submit a single PDF containing your code, test cases, and a brief explanation of your approach.",
  "instructorId": "u999-888-777",
  "instructorEmail": "professor@university.edu",
  "instructorName": "Dr. Jane Smith",
  "createdAt": "2024-01-15T14:00:00.000Z",
  "updatedAt": "2024-01-15T14:00:00.000Z",
  "dueDate": "2024-02-01T23:59:59.000Z",
  "status": "active",
  "maxFileSize": 10485760,
  "allowedFileTypes": ["application/pdf", "text/plain", "application/zip"],
  "maxSubmissions": 3,
  "submissionCount": 45,
  "points": 100,
  "rubricUrl": "https://example.com/rubric.pdf"
}
```

---

## Table 4: Submissions

**Table Name**: `campus-cloud-submissions`

**Purpose**: Tracks student submissions for assignments

### Primary Key Structure

- **Partition Key (PK)**: `assignmentId` (String) - Assignment identifier
- **Sort Key (SK)**: `studentId#submissionNumber` (String) - Composite key

### Attributes

| Attribute | Type | Description | Required |
|-----------|------|-------------|----------|
| submissionId | String | Unique submission identifier (UUID) | Yes |
| assignmentId | String | Assignment identifier | Yes |
| studentId | String | Student's user ID | Yes |
| studentEmail | String | Student's email | Yes |
| studentName | String | Student's name | Yes |
| universityId | String | Student's university ID | No |
| fileId | String | Submitted file ID | Yes |
| filename | String | Submitted filename | Yes |
| fileSize | Number | File size in bytes | Yes |
| submittedAt | String | ISO8601 timestamp | Yes |
| submissionNumber | Number | Submission attempt number (1, 2, 3) | Yes |
| status | String | Submission status (submitted, graded, returned) | Yes |
| isLate | Boolean | Whether submission is late | Yes |
| dueDate | String | Assignment due date (denormalized) | Yes |
| comments | String | Student comments | No |
| grade | Number | Numeric grade | No |
| maxGrade | Number | Maximum possible grade | No |
| feedback | String | Instructor feedback | No |
| feedbackFileId | String | Feedback file reference | No |
| gradedAt | String | ISO8601 timestamp | No |
| gradedBy | String | Grader's user ID | No |
| gradedByName | String | Grader's name | No |

### Global Secondary Indexes (GSI)

#### GSI-1: StudentIndex
**Purpose**: Query submissions by student

- **Partition Key**: `studentId` (String)
- **Sort Key**: `submittedAt` (String)
- **Projection**: ALL
- **Use Case**: Student submission history

#### GSI-2: SubmissionIdIndex
**Purpose**: Direct submission lookup

- **Partition Key**: `submissionId` (String)
- **Projection**: ALL
- **Use Case**: Submission details without assignmentId

#### GSI-3: StatusIndex
**Purpose**: Query submissions by status

- **Partition Key**: `status` (String)
- **Sort Key**: `submittedAt` (String)
- **Projection**: ALL
- **Use Case**: Ungraded submissions, grading queue

### Access Patterns

1. **Get assignment submissions**: Query by PK (assignmentId)
2. **Get student's submission**: Query by PK + SK (assignmentId#studentId)
3. **Get student's all submissions**: Query GSI-1 by studentId
4. **Get submission by ID**: Query GSI-2 by submissionId
5. **Get ungraded submissions**: Query GSI-3 where status = "submitted"

### Example Items

```json
{
  "submissionId": "sub1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
  "assignmentId": "a1b2c3d4-e5f6-7g8h-9i0j-1k2l3m4n5o6p",
  "studentId": "u123-456-789",
  "studentEmail": "student@university.edu",
  "studentName": "John Doe",
  "universityId": "S12345678",
  "fileId": "f7c8d9e1-2b3a-4c5d-6e7f-8a9b0c1d2e3f",
  "filename": "assignment1_johndoe.pdf",
  "fileSize": 2097152,
  "submittedAt": "2024-01-20T15:30:00.000Z",
  "submissionNumber": 1,
  "status": "graded",
  "isLate": false,
  "dueDate": "2024-02-01T23:59:59.000Z",
  "comments": "This is my final submission",
  "grade": 95,
  "maxGrade": 100,
  "feedback": "Excellent work! Well-structured code and comprehensive test cases.",
  "gradedAt": "2024-01-21T10:00:00.000Z",
  "gradedBy": "u999-888-777",
  "gradedByName": "Dr. Jane Smith"
}
```

---

## Table 5: Users (Optional - Cognito handles most user data)

**Table Name**: `campus-cloud-users`

**Purpose**: Extended user profile and preferences (Cognito stores core auth data)

### Primary Key Structure

- **Partition Key (PK)**: `userId` (String) - User identifier (matches Cognito sub)

### Attributes

| Attribute | Type | Description | Required |
|-----------|------|-------------|----------|
| userId | String | User identifier (Cognito sub) | Yes |
| email | String | User email | Yes |
| name | String | Full name | Yes |
| role | String | User role (student, instructor, admin) | Yes |
| universityId | String | University ID | No |
| department | String | Department/Major | No |
| createdAt | String | ISO8601 timestamp | Yes |
| lastLoginAt | String | ISO8601 timestamp | No |
| storageUsed | Number | Total storage in bytes | Yes (default: 0) |
| storageQuota | Number | Storage limit in bytes | Yes |
| notificationPreferences | Map | Notification settings | Yes |
| statistics | Map | User statistics | Yes |
| status | String | Account status (active, suspended) | Yes |

### Global Secondary Indexes (GSI)

#### GSI-1: EmailIndex
**Purpose**: Look up user by email

- **Partition Key**: `email` (String)
- **Projection**: ALL
- **Use Case**: User search, sharing

### Example Items

```json
{
  "userId": "u123-456-789",
  "email": "student@university.edu",
  "name": "John Doe",
  "role": "student",
  "universityId": "S12345678",
  "department": "Computer Science",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastLoginAt": "2024-01-15T09:00:00.000Z",
  "storageUsed": 52428800,
  "storageQuota": 5368709120,
  "notificationPreferences": {
    "emailNotifications": true,
    "shareNotifications": true,
    "assignmentReminders": true,
    "gradeNotifications": true
  },
  "statistics": {
    "totalFiles": 25,
    "filesShared": 8,
    "filesReceived": 12,
    "assignmentsSubmitted": 15,
    "totalDownloads": 45
  },
  "status": "active"
}
```

---

## DynamoDB Configuration

### Capacity Mode

**Recommendation**: On-Demand for development, Provisioned for production (with auto-scaling)

**On-Demand**:
- Good for unpredictable workloads
- Pay per request
- No capacity planning needed

**Provisioned**:
- Cost-effective for predictable workloads
- Requires capacity planning
- Enable auto-scaling (target utilization: 70%)

### Initial Provisioned Capacity (if using provisioned mode)

| Table | RCU | WCU | GSI RCU | GSI WCU |
|-------|-----|-----|---------|---------|
| Files | 25 | 10 | 10 | 5 |
| Shares | 10 | 5 | 5 | 5 |
| Assignments | 10 | 5 | 5 | 5 |
| Submissions | 20 | 10 | 10 | 5 |
| Users | 5 | 2 | 5 | 2 |

### Backup Configuration

- **Point-in-time Recovery (PITR)**: Enabled (35-day window)
- **On-Demand Backups**: Weekly
- **Backup Retention**: 30 days minimum

### Encryption

- **Encryption at Rest**: Enabled (AWS owned CMK or Customer managed CMK)
- **Encryption in Transit**: Enabled by default (TLS 1.2+)

---

## Data Retention and Cleanup

### Files Table
- Soft delete: Mark status as "deleted", keep for 30 days
- Hard delete: Lambda scheduled job removes items older than 30 days

### Shares Table
- TTL enabled: Auto-delete expired shares
- Manual cleanup: Lambda job for stale shares (90+ days)

### Submissions Table
- Retention: Keep for current semester + 2 years
- Archive: Export to S3 Glacier after 2 years

---

## Cost Estimation

### Monthly Cost (100 active users, On-Demand mode)

| Component | Estimated Cost |
|-----------|----------------|
| Files Table (10M requests) | $2.50 |
| Shares Table (5M requests) | $1.25 |
| Assignments Table (2M requests) | $0.50 |
| Submissions Table (8M requests) | $2.00 |
| Users Table (1M requests) | $0.25 |
| Storage (5GB) | $1.25 |
| Backups (10GB) | $2.00 |
| **Total** | **~$9.75/month** |

---

## Monitoring and Alarms

### CloudWatch Metrics to Monitor

1. **ConsumedReadCapacityUnits**: Read usage
2. **ConsumedWriteCapacityUnits**: Write usage
3. **UserErrors**: Application errors (4xx)
4. **SystemErrors**: DynamoDB errors (5xx)
5. **ThrottledRequests**: Capacity exceeded
6. **ConditionalCheckFailedRequests**: Optimistic locking failures

### Recommended Alarms

- **High Throttling**: > 10 throttled requests in 5 minutes
- **High Error Rate**: > 5% error rate for 5 minutes
- **Low Storage**: > 80% storage quota used
- **Backup Failures**: Any failed backup

---

## Security Best Practices

1. **IAM Policies**: Use least privilege principle
2. **VPC Endpoints**: Access DynamoDB via VPC endpoint (no internet)
3. **Audit Logging**: Enable CloudTrail for all table operations
4. **Encryption**: Use Customer Managed CMK for sensitive data
5. **Access Control**: Use IAM roles, not access keys
6. **Data Classification**: Tag tables based on data sensitivity

---

## Migration Strategy

### From Development to Production

1. Export table schema (CloudFormation/CDK/Terraform)
2. Create production tables with same schema
3. Enable PITR before migration
4. Use AWS DMS or custom Lambda for data migration
5. Validate data integrity (row counts, checksums)
6. Update application configuration
7. Monitor performance after cutover

### Schema Changes

1. **Adding attributes**: No downtime (DynamoDB is schemaless)
2. **Adding GSI**: May take hours for large tables (online operation)
3. **Removing GSI**: No downtime
4. **Changing keys**: Requires new table + data migration

---

## Testing Recommendations

### Load Testing

- Use artillery, JMeter, or Locust
- Test read/write patterns separately
- Test GSI query performance
- Test pagination with large datasets
- Test concurrent writes (optimistic locking)

### Test Data

- Generate realistic test data (faker.js)
- Test with 10x expected production load
- Test edge cases (empty strings, large items, etc.)

---

## Appendix: Query Examples

### Get User's Files (Most Recent First)
```python
response = dynamodb.query(
    TableName='campus-cloud-files',
    KeyConditionExpression='userId = :uid',
    ExpressionAttributeValues={':uid': 'u123-456-789'},
    ScanIndexForward=False,
    Limit=20
)
```

### Get Files Shared With User
```python
response = dynamodb.query(
    TableName='campus-cloud-shares',
    IndexName='SharedWithUserIndex',
    KeyConditionExpression='sharedWithUserId = :uid',
    ExpressionAttributeValues={':uid': 'u987-654-321'}
)
```

### Get Ungraded Submissions
```python
response = dynamodb.query(
    TableName='campus-cloud-submissions',
    IndexName='StatusIndex',
    KeyConditionExpression='#status = :status',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={':status': 'submitted'}
)
```

### Update File Download Count
```python
response = dynamodb.update_item(
    TableName='campus-cloud-files',
    Key={'userId': 'u123', 'fileId': 'f456'},
    UpdateExpression='SET downloadCount = downloadCount + :inc',
    ExpressionAttributeValues={':inc': 1}
)
```
