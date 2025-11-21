# Campus Cloud - File Sharing & Submission System

A fully serverless, production-ready file sharing and assignment submission system built for universities using AWS services.

[![AWS](https://img.shields.io/badge/AWS-Cloud-orange)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)

## 🎯 Features

### For Students
- ✅ **Secure Authentication** - Sign up and log in using AWS Cognito
- ✅ **File Upload** - Upload files up to 100MB using S3 presigned URLs
- ✅ **File Management** - List, download, and delete your files
- ✅ **File Sharing** - Share files with classmates and instructors
- ✅ **Assignment Submission** - Submit files for assignments with deadlines
- ✅ **Grade Viewing** - View grades and feedback from instructors

### For Instructors
- ✅ **Assignment Creation** - Create assignments with file requirements
- ✅ **Submission Management** - View and manage student submissions
- ✅ **Grading** - Grade submissions with feedback
- ✅ **File Validation** - Automatic file type and size validation

### Technical Features
- 🚀 **Fully Serverless** - No servers to manage
- 🔒 **Secure** - Encryption at rest and in transit
- 📊 **Scalable** - Auto-scales to handle any load
- 💰 **Cost-Effective** - Pay only for what you use (~$15-40/month for 100 users)
- 📈 **Monitored** - CloudWatch alarms and dashboards
- 🔄 **Versioned** - S3 versioning for file history

---

## 🏗️ Architecture

```
┌─────────────┐
│   Users     │
│  (Browser)  │
└──────┬──────┘
       │
       ├──────────────────────────────┐
       │                              │
       ▼                              ▼
┌──────────────┐           ┌──────────────────┐
│  CloudFront  │           │     Cognito      │
│     (CDN)    │           │   (Auth/Users)   │
└──────┬───────┘           └──────────────────┘
       │
       ▼
┌──────────────┐
│   S3 Static  │
│   (Frontend) │
└──────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│         API Gateway (REST)           │
│  - /files/*                          │
│  - /assignments/*                    │
│  - /shared-with-me                   │
└──────┬───────────────────────────────┘
       │
       ├────────┬────────┬────────┐
       ▼        ▼        ▼        ▼
┌───────────┐ ┌────────┐ ┌──────┐ ┌──────┐
│  Lambda   │ │ Lambda │ │ ...  │ │ ...  │
│  Presign  │ │  List  │ │      │ │      │
└─────┬─────┘ └───┬────┘ └──┬───┘ └──┬───┘
      │           │          │        │
      └───────────┴──────────┴────────┘
                  │
      ┌───────────┴───────────┐
      ▼                       ▼
┌──────────┐           ┌──────────────┐
│    S3    │           │  DynamoDB    │
│  Files   │           │   Tables     │
└──────────┘           └──────────────┘
```

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **AWS Account** with administrator access
- **AWS CLI** installed and configured ([Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- **AWS SAM CLI** installed ([Install Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html))
- **Python 3.11+** installed
- **Node.js 18+** and npm (for frontend)
- **Git** installed

### Install AWS CLI
```bash
# macOS
brew install awscli

# Windows
# Download from: https://aws.amazon.com/cli/

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Install AWS SAM CLI
```bash
# macOS
brew tap aws/tap
brew install aws-sam-cli

# Windows
# Download from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install-windows.html

# Linux
pip install aws-sam-cli
```

### Configure AWS Credentials
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region, and output format
```

---

## 🚀 Quick Start Deployment (15 minutes)

### Step 1: Clone the Repository
```bash
git clone <your-repo-url>
cd campus-cloud-system
```

### Step 2: Deploy Backend Infrastructure
```bash
cd infrastructure

# Build the SAM application
sam build

# Deploy (first time - guided)
sam deploy --guided

# You'll be prompted for:
# - Stack Name: campus-cloud-dev
# - AWS Region: us-east-1 (or your preferred region)
# - Parameter Environment: dev
# - Parameter AdminEmail: your-email@example.com
# - Confirm changes before deploy: Y
# - Allow SAM CLI IAM role creation: Y
# - Save arguments to configuration file: Y

# For subsequent deployments, just run:
sam deploy
```

**Deployment time:** ~5-8 minutes

### Step 3: Note the Outputs
After deployment completes, SAM will output important values:
```
CloudFormation outputs from deployed stack
---------------------------------------------------
Outputs
---------------------------------------------------
Key                 UserPoolId
Description         Cognito User Pool ID
Value               us-east-1_XXXXXXXXX

Key                 UserPoolClientId
Description         Cognito User Pool Client ID
Value               abcdef123456789

Key                 ApiEndpoint
Description         API Gateway endpoint URL
Value               https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev

Key                 CloudFrontURL
Description         CloudFront distribution URL
Value               d1234567890abc.cloudfront.net
---------------------------------------------------
```

**Save these values!** You'll need them for the frontend configuration.

### Step 4: Create a Test User
```bash
# Replace with your values
USER_POOL_ID="us-east-1_XXXXXXXXX"
EMAIL="student@test.com"

# Create student user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $EMAIL \
  --user-attributes Name=email,Value=$EMAIL Name=name,Value="Test Student" Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

# Add user to student group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username $EMAIL \
  --group-name student

# Create instructor user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username instructor@test.com \
  --user-attributes Name=email,Value=instructor@test.com Name=name,Value="Test Instructor" Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username instructor@test.com \
  --group-name instructor
```

### Step 5: Build and Deploy Frontend
```bash
cd ../frontend

# Install dependencies
npm install

# Create environment configuration
cat > src/config.js << EOF
export const config = {
  region: 'us-east-1',
  userPoolId: 'YOUR_USER_POOL_ID',
  userPoolClientId: 'YOUR_USER_POOL_CLIENT_ID',
  apiEndpoint: 'YOUR_API_ENDPOINT'
};
EOF

# Build the React app
npm run build

# Deploy to S3
FRONTEND_BUCKET="campus-cloud-dev-frontend-YOUR_ACCOUNT_ID"
aws s3 sync build/ s3://$FRONTEND_BUCKET/ --delete

# Invalidate CloudFront cache
CLOUDFRONT_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?Origins.Items[?DomainName=='$FRONTEND_BUCKET.s3.amazonaws.com']].Id" --output text)
aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_ID --paths "/*"
```

### Step 6: Access the Application
Open your browser and navigate to the CloudFront URL from Step 3:
```
https://d1234567890abc.cloudfront.net
```

**Login with:**
- Email: `student@test.com`
- Password: `TempPass123!` (you'll be prompted to change it)

---

## 📁 Project Structure

```
campus-cloud-system/
├── README.md                           # This file
├── backend/
│   ├── lambdas/
│   │   ├── generate_presigned_url.py   # Upload/download URL generation
│   │   ├── complete_upload.py          # Complete upload verification
│   │   ├── list_files.py               # List user files
│   │   ├── share_file.py               # File sharing logic
│   │   └── submit_assignment.py        # Assignment submissions
│   └── requirements.txt                # Python dependencies
├── infrastructure/
│   ├── template.yaml                   # AWS SAM template (IaC)
│   └── samconfig.toml                  # SAM configuration
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/                 # React components
│   │   ├── services/                   # API services
│   │   ├── App.js                      # Main app
│   │   └── config.js                   # Configuration
│   ├── package.json
│   └── README.md
└── docs/
    ├── ARCHITECTURE.md                 # Architecture documentation
    ├── API_DESIGN.md                   # API specification
    ├── DATABASE_SCHEMA.md              # DynamoDB schemas
    └── DEPLOYMENT.md                   # Detailed deployment guide
```

---

## 🔧 Configuration

### Environment Variables

Backend Lambda functions use these environment variables (auto-configured by SAM):

| Variable | Description | Default |
|----------|-------------|---------|
| `FILES_TABLE` | DynamoDB files table name | Set by SAM |
| `SHARES_TABLE` | DynamoDB shares table name | Set by SAM |
| `ASSIGNMENTS_TABLE` | DynamoDB assignments table | Set by SAM |
| `SUBMISSIONS_TABLE` | DynamoDB submissions table | Set by SAM |
| `S3_BUCKET` | S3 bucket for file storage | Set by SAM |
| `UPLOAD_URL_EXPIRATION` | Presigned URL expiration (seconds) | 300 |
| `DOWNLOAD_URL_EXPIRATION` | Download URL expiration (seconds) | 900 |
| `MAX_FILE_SIZE` | Maximum file size in bytes | 104857600 (100MB) |
| `ENABLE_NOTIFICATIONS` | Enable SNS notifications | false |

### Frontend Configuration

Edit `frontend/src/config.js`:

```javascript
export const config = {
  region: 'us-east-1',              // AWS region
  userPoolId: 'us-east-1_XXXXXXX',  // Cognito User Pool ID
  userPoolClientId: 'xxxxxxxxxxxxx', // Cognito App Client ID
  apiEndpoint: 'https://xxxxxx.execute-api.us-east-1.amazonaws.com/dev'
};
```

---

## 🧪 Testing

### Manual Testing with curl

#### 1. Login and Get Token
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id YOUR_CLIENT_ID \
  --auth-parameters USERNAME=student@test.com,PASSWORD=YourPassword123! \
  | jq -r '.AuthenticationResult.IdToken'
```

#### 2. Test Upload URL Generation
```bash
TOKEN="your-jwt-token"
API_ENDPOINT="your-api-endpoint"

curl -X POST "$API_ENDPOINT/files/upload-url" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.pdf",
    "contentType": "application/pdf",
    "fileSize": 1024,
    "metadata": {
      "description": "Test file"
    }
  }'
```

#### 3. Test List Files
```bash
curl -X GET "$API_ENDPOINT/files" \
  -H "Authorization: Bearer $TOKEN"
```

### Automated Testing

```bash
# Install test dependencies
pip install pytest boto3 moto

# Run unit tests
cd backend
pytest tests/

# Run integration tests
pytest tests/integration/
```

---

## 📊 Monitoring and Logs

### CloudWatch Logs

View Lambda function logs:
```bash
# List log groups
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/campus-cloud"

# View recent logs
aws logs tail /aws/lambda/campus-cloud-dev-generate-presigned-url --follow
```

### CloudWatch Alarms

The deployment creates these alarms:
- **API Error Alarm** - Triggers on high 5XX error rate
- **Lambda Error Alarm** - Triggers on Lambda failures
- **DynamoDB Throttle Alarm** - Triggers on throttled requests

View alarms:
```bash
aws cloudwatch describe-alarms --alarm-name-prefix campus-cloud
```

### Metrics Dashboard

View metrics in AWS Console:
1. Navigate to CloudWatch → Dashboards
2. Search for "campus-cloud"
3. View API Gateway, Lambda, DynamoDB, and S3 metrics

---

## 💰 Cost Estimation

### Monthly Costs (100 Active Users)

| Service | Usage | Cost |
|---------|-------|------|
| **Lambda** | 1M requests, 512MB, 30s avg | $10 |
| **API Gateway** | 1M requests | $3.50 |
| **DynamoDB** | 25M requests, on-demand | $12 |
| **S3 Storage** | 100GB | $2.30 |
| **S3 Requests** | 500K GET, 100K PUT | $2 |
| **CloudFront** | 100GB transfer | $8.50 |
| **Cognito** | 100 users | Free |
| **CloudWatch** | Logs and metrics | $5 |
| **Total** | | **~$43/month** |

### Cost Optimization Tips

1. **Enable S3 Lifecycle Policies** - Move old files to cheaper storage
2. **Use DynamoDB Reserved Capacity** - Save up to 75% if traffic is predictable
3. **Enable CloudFront Compression** - Reduce data transfer costs
4. **Set up Budget Alerts** - Get notified if costs exceed thresholds
5. **Delete Unused Versions** - Clean up old S3 object versions

```bash
# Set up budget alert
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json
```

---

## 🔒 Security Best Practices

### Implemented Security Features

✅ **Encryption at Rest** - All data encrypted (S3, DynamoDB)
✅ **Encryption in Transit** - HTTPS/TLS 1.3 only
✅ **Authentication** - AWS Cognito with secure password policies
✅ **Authorization** - JWT token validation on all API calls
✅ **Presigned URLs** - Time-limited (5-15 minutes)
✅ **S3 Block Public Access** - Enabled on files bucket
✅ **IAM Least Privilege** - Minimal permissions for Lambda
✅ **CloudTrail Logging** - Audit trail for all API calls
✅ **DynamoDB Point-in-Time Recovery** - 35-day recovery window

### Additional Security Recommendations

1. **Enable MFA** for Cognito users (optional):
```bash
aws cognito-idp set-user-pool-mfa-config \
  --user-pool-id YOUR_POOL_ID \
  --mfa-configuration OPTIONAL \
  --software-token-mfa-configuration Enabled=true
```

2. **Set up WAF** for API Gateway (production):
```bash
aws wafv2 create-web-acl \
  --name campus-cloud-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json
```

3. **Enable CloudTrail** for governance:
```bash
aws cloudtrail create-trail \
  --name campus-cloud-trail \
  --s3-bucket-name your-cloudtrail-bucket
```

4. **Implement Virus Scanning** (see stretch features below)

---

## 🎓 User Guides

### For Students

#### Uploading a File
1. Log in to the application
2. Click "Upload File" button
3. Select file (max 100MB)
4. Add description and tags (optional)
5. Click "Upload"
6. Wait for confirmation

#### Sharing a File
1. Navigate to "My Files"
2. Click on file to share
3. Click "Share" button
4. Enter recipient email addresses
5. Add optional message
6. Set expiration date (optional)
7. Click "Share"

#### Submitting an Assignment
1. Navigate to "Assignments"
2. Click on assignment
3. Click "Submit"
4. Select file from "My Files" or upload new
5. Add comments (optional)
6. Click "Submit Assignment"

### For Instructors

#### Creating an Assignment
1. Log in as instructor
2. Navigate to "Assignments"
3. Click "Create Assignment"
4. Fill in:
   - Title and description
   - Course ID
   - Due date
   - Max file size
   - Allowed file types
   - Max submissions per student
5. Click "Create"

#### Grading Submissions
1. Navigate to "Assignments"
2. Click on assignment
3. Click "View Submissions"
4. Click on student submission
5. Download and review file
6. Enter grade and feedback
7. Upload feedback file (optional)
8. Click "Submit Grade"

---

## 🚀 Stretch Features (Optional)

### 1. Virus Scanning with ClamAV

Add Lambda function triggered by S3 events:

```python
# lambda_function.py
import boto3
import clamd

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Download file
    s3_client.download_file(bucket, key, '/tmp/file')
    
    # Scan with ClamAV
    cd = clamd.ClamdUnixSocket()
    scan_result = cd.scan('/tmp/file')
    
    if 'FOUND' in scan_result:
        # Move to quarantine
        s3_client.copy_object(...)
        s3_client.delete_object(...)
        # Notify user
```

### 2. Real-time Notifications with WebSockets

Add API Gateway WebSocket API:

```yaml
# Add to template.yaml
WebSocketApi:
  Type: AWS::ApiGatewayV2::Api
  Properties:
    Name: campus-cloud-websocket
    ProtocolType: WEBSOCKET
    RouteSelectionExpression: "$request.body.action"
```

### 3. Advanced Search with Elasticsearch

Deploy OpenSearch cluster and index file metadata:

```bash
# Create OpenSearch domain
aws opensearch create-domain \
  --domain-name campus-cloud-search \
  --engine-version OpenSearch_2.11 \
  --cluster-config InstanceType=t3.small.search,InstanceCount=1
```

### 4. File Expiration Links

Add DynamoDB TTL-based automatic share expiration (already implemented in shares table).

### 5. Analytics Dashboard

Add QuickSight dashboard:

```bash
aws quicksight create-dashboard \
  --aws-account-id YOUR_ACCOUNT_ID \
  --dashboard-id campus-cloud-analytics \
  --name "Campus Cloud Analytics"
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "AccessDenied" when uploading to S3
**Solution:** Check CORS configuration on S3 bucket and presigned URL expiration.

```bash
aws s3api get-bucket-cors --bucket YOUR_BUCKET_NAME
```

#### 2. "User is not authenticated" error
**Solution:** Token expired. Log in again to get new JWT token.

#### 3. Lambda timeout errors
**Solution:** Increase timeout in `template.yaml`:

```yaml
Timeout: 60  # Increase from 30 to 60 seconds
```

#### 4. DynamoDB throttling
**Solution:** Switch to on-demand mode or increase provisioned capacity:

```bash
aws dynamodb update-table \
  --table-name YOUR_TABLE \
  --billing-mode PAY_PER_REQUEST
```

#### 5. CloudFront serves old content
**Solution:** Invalidate cache:

```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

### Debug Mode

Enable detailed logging:

```bash
# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name campus-cloud-dev-list-files \
  --environment Variables={LOG_LEVEL=DEBUG}
```

### Get Help

- Check CloudWatch Logs
- Review API Gateway execution logs
- Test with AWS Console first before using frontend
- Join our Slack/Discord community

---

## 🔄 Updating and Maintenance

### Update Lambda Code

```bash
cd infrastructure
sam build
sam deploy
```

### Update Frontend

```bash
cd frontend
npm run build
aws s3 sync build/ s3://YOUR_FRONTEND_BUCKET/ --delete
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

### Database Migrations

For schema changes, use DynamoDB's schemaless nature:

```python
# Add new attribute to existing items
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('campus-cloud-files')

# Scan and update
response = table.scan()
for item in response['Items']:
    table.update_item(
        Key={'userId': item['userId'], 'fileId': item['fileId']},
        UpdateExpression='SET newAttribute = :val',
        ExpressionAttributeValues={':val': 'default_value'}
    )
```

### Backup and Restore

```bash
# Enable point-in-time recovery (already enabled in template)
aws dynamodb update-continuous-backups \
  --table-name campus-cloud-dev-files \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# Create on-demand backup
aws dynamodb create-backup \
  --table-name campus-cloud-dev-files \
  --backup-name files-backup-$(date +%Y%m%d)

# Restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name campus-cloud-dev-files-restored \
  --backup-arn arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE/backup/BACKUP
```

---

## 🧹 Cleanup and Deletion

### Delete Everything (Careful!)

```bash
# 1. Empty S3 buckets first
aws s3 rm s3://YOUR_FILES_BUCKET --recursive
aws s3 rm s3://YOUR_FRONTEND_BUCKET --recursive

# 2. Delete CloudFormation stack
aws cloudformation delete-stack --stack-name campus-cloud-dev

# 3. Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name campus-cloud-dev

# 4. Verify deletion
aws cloudformation describe-stacks --stack-name campus-cloud-dev
```

### Delete Specific Resources

```bash
# Delete only Lambda functions
sam delete --stack-name campus-cloud-dev --no-prompts

# Delete only DynamoDB tables
aws dynamodb delete-table --table-name campus-cloud-dev-files
```

---

## 📚 Additional Resources

### Documentation
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/)
- [DynamoDB Developer Guide](https://docs.aws.amazon.com/dynamodb/)
- [Cognito Developer Guide](https://docs.aws.amazon.com/cognito/)

### Tutorials
- [Building Serverless Applications](https://aws.amazon.com/serverless/)
- [DynamoDB Single Table Design](https://www.alexdebrie.com/posts/dynamodb-single-table/)
- [S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)

### Community
- AWS re:Post
- Stack Overflow (`aws-lambda`, `aws-sam`, `amazon-dynamodb` tags)
- AWS Slack Community

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Coding Standards
- Follow PEP 8 for Python code
- Use ESLint for JavaScript code
- Write unit tests for new features
- Update documentation

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **AWS Cloud Club** - Initial work

## 🙏 Acknowledgments

- AWS for providing excellent serverless services
- The open-source community for tools and libraries
- University students and instructors for feedback

---

## 📞 Support

For issues, questions, or suggestions:

- **Email:** support@campuscloud.edu
- **GitHub Issues:** [github.com/your-org/campus-cloud/issues](https://github.com)
- **Documentation:** [docs.campuscloud.edu](https://docs.campuscloud.edu)

---

**Happy Cloud Computing! ☁️🎓**