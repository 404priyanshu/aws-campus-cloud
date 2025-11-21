# Campus Cloud File Sharing & Submission System - Architecture

## System Overview

The Campus Cloud system is a fully serverless application built on AWS that enables students to upload, share, and submit files, while allowing instructors to manage assignments and submissions.

## Architecture Diagram Description

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USERS                                       │
│                    (Students & Instructors)                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTPS
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          CloudFront CDN                                  │
│                     (Global Content Delivery)                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    S3 Static Website Hosting                            │
│                      (React Frontend App)                               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
        ┌──────────────────────┐  ┌──────────────────────┐
        │  Amazon Cognito      │  │   API Gateway         │
        │  User Pools          │  │   (REST API)          │
        │  - Authentication    │  │   - Authorization     │
        │  - User Management   │  │   - Rate Limiting     │
        └──────────────────────┘  └──────────┬────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
        ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
        │  Lambda Function │   │  Lambda Function │   │  Lambda Function │
        │  - Presigned URL │   │  - List Files    │   │  - Share Files   │
        │  - Upload/Download│   │  - Complete Upload│   │  - Submissions  │
        └─────────┬────────┘   └────────┬─────────┘   └────────┬─────────┘
                  │                     │                       │
                  │                     ▼                       │
                  │          ┌──────────────────┐              │
                  │          │   DynamoDB       │              │
                  │          │   - Files Table  │◄─────────────┘
                  │          │   - Assignments  │
                  │          │   - Submissions  │
                  │          │   - Shares       │
                  │          └──────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │   Amazon S3      │
        │   File Storage   │
        │   - User Files   │
        │   - Assignments  │
        │   - Submissions  │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  S3 Event        │
        │  Notifications   │
        │  (Optional)      │
        └─────────┬────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  Lambda Function │
        │  - Virus Scan    │
        │  - Versioning    │
        │  - Notifications │
        └──────────────────┘
```

## Core Components

### 1. Frontend Layer
- **CloudFront**: CDN for global content delivery with HTTPS
- **S3 Static Hosting**: Hosts the React application
- **React App**: Single-page application for user interface

### 2. Authentication & Authorization
- **Amazon Cognito User Pools**: 
  - User registration and login
  - JWT token generation
  - User attribute management (role: student/instructor)
  - Password policies and MFA support

### 3. API Layer
- **API Gateway REST API**:
  - Cognito Authorizer for JWT validation
  - CORS configuration
  - Request/response validation
  - Throttling and rate limiting
  - API key management (optional)

### 4. Business Logic Layer
- **AWS Lambda Functions** (Python 3.11):
  - `generate-presigned-url`: Creates S3 presigned URLs for upload/download
  - `list-files`: Retrieves user's files from DynamoDB
  - `complete-upload`: Updates DynamoDB after successful upload
  - `share-file`: Creates share records with access control
  - `submit-assignment`: Handles assignment submissions
  - `list-assignments`: Returns available assignments
  - `view-submissions`: Instructor view of student submissions

### 5. Storage Layer
- **Amazon S3**:
  - Bucket structure: `{bucket}/users/{userId}/files/{fileId}`
  - Bucket structure: `{bucket}/assignments/{assignmentId}/submissions/{submissionId}`
  - Versioning enabled for file history
  - Lifecycle policies for cost optimization
  - Encryption at rest (SSE-S3 or SSE-KMS)

### 6. Database Layer
- **Amazon DynamoDB**:
  - Files table: Metadata for all uploaded files
  - Assignments table: Assignment details and deadlines
  - Submissions table: Student submission records
  - Shares table: File sharing permissions

## Data Flow

### Upload Flow
1. User authenticates with Cognito, receives JWT
2. Frontend requests presigned URL from API Gateway
3. Lambda validates user and generates S3 presigned POST URL
4. Frontend uploads directly to S3 using presigned URL
5. After upload, frontend calls "complete upload" endpoint
6. Lambda creates record in DynamoDB Files table
7. (Optional) S3 event triggers virus scanning Lambda

### Download Flow
1. User requests file download through frontend
2. Frontend calls API Gateway with file ID
3. Lambda validates ownership/share permissions
4. Lambda generates S3 presigned GET URL (15-minute expiry)
5. Frontend redirects user to presigned URL
6. User downloads directly from S3

### Share Flow
1. User selects file and enters recipient email
2. Frontend calls share API endpoint
3. Lambda validates file ownership
4. Lambda creates share record in DynamoDB
5. (Optional) SNS sends email notification to recipient

### Submit Assignment Flow
1. Student uploads file (normal upload flow)
2. Student calls submit endpoint with file ID and assignment ID
3. Lambda validates assignment deadline and file ownership
4. Lambda creates submission record in DynamoDB
5. Lambda updates assignment submission count
6. (Optional) SNS notifies instructor

## Security Architecture

### Authentication & Authorization
- **Cognito JWT tokens** for API authentication
- **IAM roles** with least privilege principle
- **Resource-based policies** on S3 buckets
- **API Gateway authorizers** validate tokens

### Data Security
- **Encryption in transit**: HTTPS/TLS 1.3
- **Encryption at rest**: S3 SSE-S3 or SSE-KMS
- **DynamoDB encryption**: Default encryption enabled
- **Presigned URLs**: Time-limited (5-15 minutes)
- **CORS policies**: Restrict origins

### Access Control
- **User isolation**: S3 prefix-based separation
- **Share validation**: DynamoDB-backed permissions
- **Role-based access**: Student vs Instructor permissions
- **API throttling**: Prevent abuse

## Scalability

### Auto-Scaling Components
- **Lambda**: Automatic concurrent execution scaling
- **DynamoDB**: On-demand capacity mode
- **S3**: Unlimited storage capacity
- **CloudFront**: Global edge locations

### Performance Optimizations
- **CloudFront caching**: Static asset caching
- **DynamoDB indexes**: GSI for efficient queries
- **S3 Transfer Acceleration**: Faster uploads (optional)
- **Lambda memory optimization**: Right-sized functions

## Cost Optimization

### Strategies
- **S3 Lifecycle policies**: Archive old files to Glacier
- **DynamoDB on-demand**: Pay per request
- **Lambda provisioned concurrency**: Only if needed
- **CloudFront compression**: Reduce data transfer
- **S3 Intelligent-Tiering**: Automatic cost optimization

### Estimated Monthly Cost (100 active users)
- **Lambda**: $5-10
- **API Gateway**: $3-5
- **DynamoDB**: $5-15
- **S3 Storage (100GB)**: $2-3
- **CloudFront**: $1-5
- **Cognito**: Free tier
- **Total**: ~$15-40/month

## High Availability & Disaster Recovery

### Built-in Resilience
- **Multi-AZ**: All services run across multiple AZs
- **S3 11 9's durability**: 99.999999999%
- **DynamoDB automatic backups**: Point-in-time recovery
- **Lambda automatic failover**: Regional redundancy

### Backup Strategy
- **S3 versioning**: Enabled on buckets
- **DynamoDB PITR**: 35-day recovery window
- **Cross-region replication**: Optional for critical data
- **CloudFormation templates**: Infrastructure as code

## Monitoring & Logging

### CloudWatch Integration
- **Lambda logs**: Execution logs and errors
- **API Gateway logs**: Access logs and execution logs
- **S3 access logs**: Bucket-level logging
- **DynamoDB metrics**: Read/write capacity utilization
- **Custom metrics**: Upload success rate, latency

### Alarms & Notifications
- **Lambda errors**: Alert on function failures
- **API Gateway 5xx**: Alert on server errors
- **DynamoDB throttling**: Alert on capacity issues
- **Cost alerts**: Budget threshold notifications

## Development & Deployment

### Environments
- **Development**: Isolated stack for testing
- **Staging**: Pre-production validation
- **Production**: Live user environment

### CI/CD Pipeline
- **Source control**: GitHub/GitLab
- **Build**: AWS CodeBuild or GitHub Actions
- **Test**: Unit and integration tests
- **Deploy**: AWS SAM or CDK
- **Rollback**: CloudFormation stack rollback

## Stretch Features

### 1. Virus Scanning
- **S3 event → Lambda**: Trigger on object creation
- **ClamAV integration**: Scan uploaded files
- **Quarantine bucket**: Move infected files
- **User notification**: Email alert on detection

### 2. File Versioning
- **S3 versioning**: Automatic version tracking
- **DynamoDB version history**: Metadata for each version
- **UI version selector**: Download previous versions

### 3. Expiring Links
- **DynamoDB TTL**: Auto-delete share records
- **Short-lived presigned URLs**: 5-minute expiry
- **Custom expiry**: User-defined link expiration

### 4. Real-time Notifications
- **WebSocket API**: API Gateway WebSocket
- **Connection management**: Lambda + DynamoDB
- **Push notifications**: Browser notifications API

### 5. Advanced Search
- **DynamoDB GSI**: Search by filename, date, type
- **Elasticsearch**: Full-text search (advanced)
- **Tagging system**: User-defined file tags

### 6. Analytics Dashboard
- **CloudWatch dashboards**: Usage metrics
- **QuickSight**: Advanced analytics and reports
- **User activity tracking**: Upload/download statistics

## Compliance & Governance

### Data Privacy
- **FERPA compliance**: Student data protection
- **Data retention policies**: Configurable retention periods
- **User data deletion**: Complete data removal on request
- **Audit trails**: CloudTrail logging

### Access Auditing
- **CloudTrail**: API call logging
- **S3 access logs**: Object-level operations
- **DynamoDB streams**: Change data capture
- **Compliance reports**: Automated generation

## Next Steps

1. Review architecture and gather requirements
2. Set up AWS account and configure billing alerts
3. Deploy infrastructure using provided SAM template
4. Configure Cognito user pool and test authentication
5. Deploy Lambda functions and test API endpoints
6. Build and deploy React frontend
7. Perform end-to-end testing
8. Configure monitoring and alarms
9. Launch to pilot users
10. Iterate based on feedback