# Campus Cloud - Complete Deployment Guide

This guide provides step-by-step instructions for deploying the Campus Cloud File Sharing & Submission System from scratch to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Account Setup](#aws-account-setup)
3. [Local Development Environment](#local-development-environment)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Testing & Verification](#testing--verification)
8. [Production Deployment](#production-deployment)
9. [Troubleshooting](#troubleshooting)
10. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

- **AWS Account** with administrator access
- **AWS CLI** v2.x or higher
- **AWS SAM CLI** v1.100 or higher
- **Python** 3.11 or higher
- **Node.js** 18.x or higher
- **npm** 9.x or higher
- **Git** 2.x or higher

### Required Knowledge

- Basic understanding of AWS services (Lambda, API Gateway, S3, DynamoDB)
- Command line proficiency
- Basic React/JavaScript knowledge (for frontend customization)

### Estimated Time

- **Development Environment**: 30 minutes
- **Backend Deployment**: 15-20 minutes
- **Frontend Deployment**: 10-15 minutes
- **Testing**: 15 minutes
- **Total**: ~1-1.5 hours

---

## AWS Account Setup

### Step 1: Create AWS Account

If you don't have an AWS account:

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow the registration process
4. Complete identity verification
5. Set up billing information

### Step 2: Create IAM User for Deployment

**Important:** Don't use root account credentials for deployment.

```bash
# Login to AWS Console as root
# Navigate to IAM → Users → Add User

# User Details:
# - Username: campus-cloud-deployer
# - Access type: Programmatic access
# - Permissions: AdministratorAccess (for initial setup)
```

**Alternative via CLI (if you have root credentials configured):**

```bash
# Create IAM user
aws iam create-user --user-name campus-cloud-deployer

# Attach AdministratorAccess policy
aws iam attach-user-policy \
  --user-name campus-cloud-deployer \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Create access key
aws iam create-access-key --user-name campus-cloud-deployer
```

Save the Access Key ID and Secret Access Key.

### Step 3: Configure AWS CLI

```bash
# Configure default profile
aws configure

# Enter:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: us-east-1 (or your preferred region)
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/campus-cloud-deployer"
}
```

### Step 4: Set Up Budget Alerts

Protect yourself from unexpected costs:

```bash
# Create budget.json
cat > budget.json << 'EOF'
{
  "BudgetLimit": {
    "Amount": "50.0",
    "Unit": "USD"
  },
  "BudgetName": "Campus-Cloud-Monthly-Budget",
  "BudgetType": "COST",
  "CostFilters": {},
  "CostTypes": {
    "IncludeTax": true,
    "IncludeSubscription": true,
    "UseBlended": false
  },
  "TimeUnit": "MONTHLY"
}
EOF

# Create budget
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json
```

---

## Local Development Environment

### Step 1: Install Required Tools

#### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install AWS CLI
brew install awscli

# Install SAM CLI
brew tap aws/tap
brew install aws-sam-cli

# Install Python 3.11
brew install python@3.11

# Install Node.js
brew install node@18

# Verify installations
aws --version
sam --version
python3 --version
node --version
npm --version
```

#### Windows

```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install tools
choco install awscli -y
choco install awssamcli -y
choco install python311 -y
choco install nodejs-lts -y

# Verify installations
aws --version
sam --version
python --version
node --version
npm --version
```

#### Linux (Ubuntu/Debian)

```bash
# Update package manager
sudo apt update

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Verify installations
aws --version
sam --version
python3.11 --version
node --version
npm --version
```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/campus-cloud-system.git
cd campus-cloud-system

# Verify structure
ls -la
# Should show: backend/, frontend/, infrastructure/, docs/, README.md
```

### Step 3: Set Up Python Virtual Environment

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list

cd ..
```

---

## Backend Deployment

### Step 1: Review SAM Template

```bash
cd infrastructure

# Review the template
cat template.yaml

# Key resources to note:
# - UserPool (Cognito)
# - FilesBucket (S3)
# - DynamoDB Tables
# - Lambda Functions
# - API Gateway
```

### Step 2: Build SAM Application

```bash
# Build the application
sam build

# Output should show:
# Building codeuri: ../backend/lambdas/
# Running PythonPipBuilder:ResolveDependencies
# Build Succeeded
```

If build fails:
```bash
# Check Python version
python3 --version

# Check if requirements.txt exists
cat ../backend/requirements.txt

# Rebuild with verbose output
sam build --debug
```

### Step 3: Deploy Backend (First Time)

```bash
# Deploy with guided prompts
sam deploy --guided

# Answer the prompts:
```

**Prompt Responses:**

```
Stack Name [sam-app]: campus-cloud-dev
AWS Region [us-east-1]: us-east-1
Parameter Environment [dev]: dev
Parameter DomainName [campuscloud.edu]: your-domain.com
Parameter AdminEmail []: your-email@example.com

Confirm changes before deploy [Y/n]: Y
Allow SAM CLI IAM role creation [Y/n]: Y
Disable rollback [y/N]: N
GeneratePresignedUrlFunction may not have authorization defined [Y/n]: Y
CompleteUploadFunction may not have authorization defined [Y/n]: Y
ListFilesFunction may not have authorization defined [Y/n]: Y
ShareFileFunction may not have authorization defined [Y/n]: Y
SubmitAssignmentFunction may not have authorization defined [Y/n]: Y
Save arguments to configuration file [Y/n]: Y
SAM configuration file [samconfig.toml]: samconfig.toml
SAM configuration environment [default]: default
```

**Deployment Progress:**

```
Deploying with following values
===============================
Stack name                   : campus-cloud-dev
Region                       : us-east-1
Confirm changeset           : True
Disable rollback            : False
Deployment s3 bucket        : aws-sam-cli-managed-default-samclisourcebucket-xxxxx
Capabilities                : ["CAPABILITY_IAM"]
Parameter overrides         : {"Environment": "dev", ...}
Signing Profiles            : {}

Initiating deployment
=====================

Waiting for changeset to be created...

CloudFormation stack changeset
-------------------------------------------------------------------------------------------------
Operation                        LogicalResourceId                ResourceType                  
-------------------------------------------------------------------------------------------------
+ Add                            ApiLogGroup                      AWS::Logs::LogGroup           
+ Add                            AssignmentsTable                 AWS::DynamoDB::Table          
+ Add                            CampusCloudApi                   AWS::Serverless::Api          
+ Add                            CloudFrontDistribution           AWS::CloudFront::Distribution 
...
+ Add                            UserPool                         AWS::Cognito::UserPool        
-------------------------------------------------------------------------------------------------

Changeset created successfully. Run the following command to review changes:
sam deploy --guided

Deploy this changeset? [y/N]: y

2024-01-15 10:00:00 - Waiting for stack create/update to complete

Stack campus-cloud-dev CREATE_COMPLETE
```

**Estimated Time:** 8-12 minutes

### Step 4: Save Deployment Outputs

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs' \
  --output table

# Save to file
aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs' \
  --output json > deployment-outputs.json

# Display important values
cat deployment-outputs.json | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"'
```

Expected outputs:
```
UserPoolId: us-east-1_AbCdEfGhI
UserPoolClientId: 1a2b3c4d5e6f7g8h9i0j1k2l3m
ApiEndpoint: https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev
FilesBucketName: campus-cloud-dev-files-123456789012
FrontendBucketName: campus-cloud-dev-frontend-123456789012
CloudFrontURL: d1234567890abc.cloudfront.net
```

**IMPORTANT: Save these values! You'll need them for frontend configuration.**

### Step 5: Subsequent Deployments

After the first deployment, you can use:

```bash
# Quick deploy (uses saved config)
sam build && sam deploy

# Or deploy specific function
sam build && sam deploy --parameter-overrides Environment=dev
```

---

## Frontend Deployment

### Step 1: Install Dependencies

```bash
cd ../frontend

# Install npm packages
npm install

# Verify installation
npm list --depth=0
```

### Step 2: Configure Frontend

Create configuration file with your deployed backend values:

```bash
# Create config file
cat > src/config.js << EOF
export const config = {
  region: 'us-east-1',
  cognito: {
    userPoolId: 'us-east-1_REPLACE_ME',
    userPoolClientId: 'REPLACE_ME_WITH_CLIENT_ID',
  },
  api: {
    endpoint: 'https://REPLACE_ME.execute-api.us-east-1.amazonaws.com/dev',
    timeout: 30000,
  },
  s3: {
    bucket: 'campus-cloud-dev-files-REPLACE_ME',
    region: 'us-east-1',
  },
  app: {
    name: 'Campus Cloud',
    version: '1.0.0',
    maxFileSize: 104857600,
    allowedFileTypes: [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'image/jpeg',
      'image/png'
    ],
    defaultPageSize: 20,
    maxPageSize: 100,
  },
  features: {
    enableSharing: true,
    enableAssignments: true,
    enableNotifications: false,
    enableVersioning: true,
  },
};

export default config;
EOF
```

**Now replace the values:**

```bash
# Get values from backend deployment
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

USER_POOL_CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text)

API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

BUCKET=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`FilesBucketName`].OutputValue' \
  --output text)

# Update config.js automatically (macOS/Linux)
sed -i.bak "s|userPoolId: '.*'|userPoolId: '$USER_POOL_ID'|g" src/config.js
sed -i.bak "s|userPoolClientId: '.*'|userPoolClientId: '$USER_POOL_CLIENT_ID'|g" src/config.js
sed -i.bak "s|endpoint: '.*'|endpoint: '$API_ENDPOINT'|g" src/config.js
sed -i.bak "s|bucket: '.*'|bucket: '$BUCKET'|g" src/config.js

# Verify changes
grep -A 5 "cognito:" src/config.js
grep -A 3 "api:" src/config.js
```

### Step 3: Build Frontend

```bash
# Build production bundle
npm run build

# Output should be in build/ directory
ls -la build/

# Should see:
# - index.html
# - static/
# - favicon.ico
# - etc.
```

### Step 4: Deploy to S3

```bash
# Get frontend bucket name
FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

echo "Deploying to bucket: $FRONTEND_BUCKET"

# Upload files to S3
aws s3 sync build/ s3://$FRONTEND_BUCKET/ \
  --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html" \
  --exclude "service-worker.js"

# Upload index.html with no-cache
aws s3 cp build/index.html s3://$FRONTEND_BUCKET/index.html \
  --cache-control "no-cache, no-store, must-revalidate"

# Verify upload
aws s3 ls s3://$FRONTEND_BUCKET/
```

### Step 5: Invalidate CloudFront Cache

```bash
# Get CloudFront distribution ID
CLOUDFRONT_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='$FRONTEND_BUCKET.s3.amazonaws.com']].Id" \
  --output text)

echo "CloudFront Distribution ID: $CLOUDFRONT_ID"

# Create invalidation
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"

# Get CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
  --output text)

echo "Application URL: https://$CLOUDFRONT_URL"
```

---

## Post-Deployment Configuration

### Step 1: Create Test Users

```bash
# Set variables
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

# Create student user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username student@test.com \
  --user-attributes \
    Name=email,Value=student@test.com \
    Name=name,Value="Test Student" \
    Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

# Add to student group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username student@test.com \
  --group-name student

# Create instructor user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username instructor@test.com \
  --user-attributes \
    Name=email,Value=instructor@test.com \
    Name=name,Value="Test Instructor" \
    Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

# Add to instructor group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username instructor@test.com \
  --group-name instructor

echo "Test users created successfully!"
echo "Student: student@test.com / TempPass123!"
echo "Instructor: instructor@test.com / TempPass123!"
```

### Step 2: Verify Lambda Permissions

```bash
# Check Lambda execution roles
aws iam list-roles --query 'Roles[?contains(RoleName, `campus-cloud`)].RoleName'

# Check Lambda function policies
aws lambda get-policy --function-name campus-cloud-dev-generate-presigned-url
```

### Step 3: Enable CloudWatch Logs Retention

```bash
# Set log retention to 30 days for all Lambda functions
for func in $(aws lambda list-functions --query 'Functions[?contains(FunctionName, `campus-cloud-dev`)].FunctionName' --output text); do
  LOG_GROUP="/aws/lambda/$func"
  aws logs put-retention-policy --log-group-name $LOG_GROUP --retention-in-days 30
  echo "Set retention for $LOG_GROUP"
done
```

### Step 4: Configure CORS (if needed)

The SAM template already configures CORS, but verify:

```bash
# Check API Gateway CORS
API_ID=$(aws cloudformation describe-stack-resource \
  --stack-name campus-cloud-dev \
  --logical-resource-id CampusCloudApi \
  --query 'StackResourceDetail.PhysicalResourceId' \
  --output text)

aws apigateway get-rest-api --rest-api-id $API_ID
```

---

## Testing & Verification

### Step 1: Health Check

```bash
# Test API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

curl $API_ENDPOINT/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

### Step 2: Test Authentication

```bash
# Get user pool client ID
CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text)

# Authenticate
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=student@test.com,PASSWORD=YourNewPassword123! \
  | jq -r '.AuthenticationResult.IdToken' > token.txt

# Use token
TOKEN=$(cat token.txt)
curl -H "Authorization: Bearer $TOKEN" $API_ENDPOINT/files
```

### Step 3: Test File Upload Flow

```bash
# 1. Generate upload URL
curl -X POST "$API_ENDPOINT/files/upload-url" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.txt",
    "contentType": "text/plain",
    "fileSize": 100
  }' | jq '.'

# 2. Upload file using presigned URL (get URL from previous response)
# 3. Complete upload (get fileId from step 1)
# 4. List files
curl -H "Authorization: Bearer $TOKEN" $API_ENDPOINT/files | jq '.'
```

### Step 4: Test Frontend

```bash
# Get CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
  --output text)

# Open in browser
echo "Open: https://$CLOUDFRONT_URL"

# Or test with curl
curl -I https://$CLOUDFRONT_URL
```

**Manual Testing Checklist:**

- [ ] Can access login page
- [ ] Can login with test student account
- [ ] Can upload a file
- [ ] Can view uploaded files list
- [ ] Can download a file
- [ ] Can share a file
- [ ] Can view shared files
- [ ] Login as instructor
- [ ] Can create assignment
- [ ] Login as student
- [ ] Can submit assignment
- [ ] Login as instructor
- [ ] Can view submissions
- [ ] Can grade submission

---

## Production Deployment

### Differences from Development

For production deployment:

1. **Use separate AWS account** (recommended)
2. **Enable additional security features**
3. **Set up custom domain**
4. **Configure monitoring and alerts**
5. **Enable WAF for API Gateway**
6. **Use RDS for user data** (optional)

### Step 1: Create Production Stack

```bash
# Build
sam build

# Deploy to production
sam deploy \
  --stack-name campus-cloud-prod \
  --parameter-overrides \
    Environment=prod \
    DomainName=campuscloud.edu \
    AdminEmail=admin@campuscloud.edu \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Step 2: Configure Custom Domain

```bash
# Request SSL certificate
aws acm request-certificate \
  --domain-name campuscloud.edu \
  --subject-alternative-names "*.campuscloud.edu" \
  --validation-method DNS \
  --region us-east-1

# Add custom domain to API Gateway
# (Follow AWS Console instructions)

# Configure Route 53
# (Create A record pointing to CloudFront)
```

### Step 3: Enable WAF

```bash
# Create WAF Web ACL
aws wafv2 create-web-acl \
  --name campus-cloud-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --region us-east-1 \
  --rules file://waf-rules.json

# Associate with API Gateway
aws wafv2 associate-web-acl \
  --web-acl-arn <WAF_ARN> \
  --resource-arn <API_GATEWAY_ARN>
```

### Step 4: Enable Enhanced Monitoring

```bash
# Enable X-Ray tracing (already in template)
# Enable detailed CloudWatch metrics
# Set up custom dashboards
# Configure SNS alerts
```

---

## Troubleshooting

### Common Issues

#### Issue 1: SAM Build Fails

```
Error: PythonPipBuilder:ResolveDependencies - requirements.txt not found
```

**Solution:**
```bash
cd backend
ls requirements.txt  # Verify file exists
pip install -r requirements.txt  # Test locally
cd ../infrastructure
sam build --debug
```

#### Issue 2: Deployment Fails - S3 Bucket Already Exists

```
Error: campus-cloud-dev-files-123456789012 already exists
```

**Solution:**
```bash
# Delete existing bucket
aws s3 rb s3://campus-cloud-dev-files-123456789012 --force

# Or use different stack name
sam deploy --stack-name campus-cloud-dev-v2
```

#### Issue 3: Lambda Timeout

```
Task timed out after 30.00 seconds
```

**Solution:**
```yaml
# In template.yaml, increase timeout
Globals:
  Function:
    Timeout: 60  # Increase from 30
```

#### Issue 4: CORS Errors in Frontend

```
Access to fetch at 'https://...' has been blocked by CORS policy
```

**Solution:**
```bash
# Check API Gateway CORS settings
# Verify Lambda response headers include CORS headers
# Check browser console for specific CORS error
```

#### Issue 5: 401 Unauthorized

```
{"error": "Unauthorized"}
```

**Solution:**
```bash
# Check token expiration
# Verify Cognito User Pool ID in frontend config
# Test authentication flow
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH ...
```

### Debug Commands

```bash
# View Lambda logs
sam logs -n GeneratePresignedUrlFunction --stack-name campus-cloud-dev --tail

# Check DynamoDB tables
aws dynamodb list-tables
aws dynamodb scan --table-name campus-cloud-dev-files --max-items 10

# Check S3 bucket
aws s3 ls s3://campus-cloud-dev-files-123456789012/

# Check API Gateway
aws apigateway get-rest-apis
aws apigateway get-stages --rest-api-id <API_ID>

# Validate CloudFormation template
aws cloudformation validate-template --template-body file://template.yaml
```

---

## Rollback Procedures

### Rollback Backend

```bash
# List stack events to find issue
aws cloudformation describe-stack-events --stack-name campus-cloud-dev

# Rollback to previous version
aws cloudformation cancel-update-stack --stack-name campus-cloud-dev

# Or delete and redeploy
aws cloudformation delete-stack --stack-name campus-cloud-dev
# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name campus-cloud-dev
# Redeploy
sam deploy --guided
```

### Rollback Frontend

```bash
# List S3 versions
aws s3api list-object-versions --bucket $FRONTEND_BUCKET

# Restore previous version
aws s3api copy-object \
  --bucket $FRONTEND_BUCKET \
  --copy-source $FRONTEND_BUCKET/index.html?versionId=<VERSION_ID> \
  --key index.html

# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"
```

### Emergency Shutdown

```bash
# Disable API Gateway
aws apigateway update-stage \
  --rest-api-id <API_ID> \
  --stage-name dev \
  --patch-operations op=replace,path=/description,value="MAINTENANCE MODE"

# Or delete entire stack
aws cloudformation delete-stack --stack-name campus-cloud-dev
```

---

## Post-Deployment Checklist

- [ ] Backend deployed successfully
- [ ] Frontend deployed successfully
- [ ] Test users created
- [ ] Authentication working
- [ ] File upload working
- [ ] File download working
- [ ] File sharing working
- [ ] Assignment submission working
- [ ] CloudWatch logs enabled
- [ ] Alarms configured
- [ ] Budget alerts set
- [ ] Documentation updated
- [ ] Team notified
- [ ] Backup procedures documented

---

## Next Steps

1. **Customize Frontend** - Update branding, colors, logo
2. **Add More Features** - Implement stretch features (virus scanning, notifications)
3. **Set Up CI/CD** - Automate deployments with GitHub Actions or AWS CodePipeline
4. **Performance Optimization** - Monitor and optimize Lambda functions
5. **Cost Optimization** - Review and optimize resource usage
6. **Security Hardening** - Implement additional security measures
7. **User Training** - Create user documentation and training materials

---

## Support

For issues or questions:
- Check CloudWatch logs
- Review API Gateway execution logs
- Search GitHub issues
- Contact AWS support

---

**Deployment completed! Your Campus Cloud application is now live! 🎉**