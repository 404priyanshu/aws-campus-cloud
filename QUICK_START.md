# Campus Cloud - Quick Start Guide

Get your Campus Cloud File Sharing & Submission System running in 30 minutes!

---

## 🚀 TL;DR - Deploy Now

```bash
# 1. Clone and navigate
git clone <repo-url>
cd campus-cloud-system

# 2. Deploy backend
cd infrastructure
sam build && sam deploy --guided

# 3. Create test user
USER_POOL_ID="<from-output>"
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username student@test.com \
  --user-attributes Name=email,Value=student@test.com Name=email_verified,Value=true \
  --temporary-password "TempPass123!"

# 4. Deploy frontend
cd ../frontend
npm install
# Update src/config.js with outputs
npm run build
aws s3 sync build/ s3://<frontend-bucket>/

# 5. Open CloudFront URL
echo "Done! Open: https://<cloudfront-url>"
```

---

## 📋 Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI installed (`aws --version`)
- [ ] AWS SAM CLI installed (`sam --version`)
- [ ] Python 3.11+ (`python3 --version`)
- [ ] Node.js 18+ (`node --version`)
- [ ] AWS credentials configured (`aws sts get-caller-identity`)

### Install Missing Tools

**macOS:**
```bash
brew install awscli aws-sam-cli python@3.11 node@18
```

**Windows (Chocolatey):**
```powershell
choco install awscli awssamcli python311 nodejs-lts
```

**Linux (Ubuntu):**
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install

# Python & Node
sudo apt install python3.11 python3.11-venv nodejs npm
```

---

## 🏗️ Backend Deployment (10 minutes)

### Step 1: Build
```bash
cd infrastructure
sam build
```

**Expected output:**
```
Building codeuri: ../backend/lambdas/
Running PythonPipBuilder:ResolveDependencies
Build Succeeded
```

### Step 2: Deploy
```bash
sam deploy --guided
```

**When prompted, enter:**
- Stack Name: `campus-cloud-dev`
- AWS Region: `us-east-1` (or your region)
- Environment: `dev`
- AdminEmail: `your-email@example.com`
- Confirm changes: `Y`
- Allow IAM role creation: `Y`
- Save config: `Y`

**Deployment time:** 8-12 minutes ☕

### Step 3: Save Outputs
```bash
# View outputs
aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs'

# Save to file
aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs' \
  --output json > outputs.json
```

**Important values:**
- `UserPoolId`: us-east-1_XXXXXXXXX
- `UserPoolClientId`: xxxxxxxxxxxxxxxxxx
- `ApiEndpoint`: https://xxxxx.execute-api.us-east-1.amazonaws.com/dev
- `CloudFrontURL`: d1234567890abc.cloudfront.net

---

## 👤 Create Test Users (2 minutes)

### Student User
```bash
USER_POOL_ID="<your-user-pool-id>"

aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username student@test.com \
  --user-attributes \
    Name=email,Value=student@test.com \
    Name=name,Value="Test Student" \
    Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username student@test.com \
  --group-name student
```

### Instructor User
```bash
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username instructor@test.com \
  --user-attributes \
    Name=email,Value=instructor@test.com \
    Name=name,Value="Test Instructor" \
    Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username instructor@test.com \
  --group-name instructor
```

**Test credentials:**
- Student: `student@test.com` / `TempPass123!`
- Instructor: `instructor@test.com` / `TempPass123!`

---

## 💻 Frontend Deployment (8 minutes)

### Step 1: Install Dependencies
```bash
cd ../frontend
npm install
```

### Step 2: Configure
```bash
# Auto-configure (Linux/macOS)
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text)

API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

# Create config
cat > src/config.js << EOF
export const config = {
  region: 'us-east-1',
  cognito: {
    userPoolId: '$USER_POOL_ID',
    userPoolClientId: '$CLIENT_ID',
  },
  api: {
    endpoint: '$API_ENDPOINT',
    timeout: 30000,
  },
  s3: {
    bucket: 'campus-cloud-dev-files-${AWS::AccountId}',
    region: 'us-east-1',
  },
  app: {
    name: 'Campus Cloud',
    version: '1.0.0',
    maxFileSize: 104857600,
    allowedFileTypes: [
      'application/pdf',
      'application/msword',
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

**Windows/Manual:** Edit `src/config.js` and replace values from outputs.json

### Step 3: Build
```bash
npm run build
```

**Expected output:**
```
Creating an optimized production build...
Compiled successfully.

File sizes after gzip:
  50.5 kB  build/static/js/main.abc123.js
  1.2 kB   build/static/css/main.xyz789.css

The build folder is ready to be deployed.
```

### Step 4: Deploy to S3
```bash
FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

aws s3 sync build/ s3://$FRONTEND_BUCKET/ --delete
```

### Step 5: Invalidate CloudFront
```bash
CLOUDFRONT_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName=='$FRONTEND_BUCKET.s3.amazonaws.com']].Id" \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_ID \
  --paths "/*"
```

---

## ✅ Verify Deployment (5 minutes)

### 1. Test API
```bash
curl $API_ENDPOINT/health
```

**Expected:** `{"status":"healthy","timestamp":"..."}`

### 2. Test Authentication
```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=student@test.com,PASSWORD=YourNewPassword123! \
  | jq -r '.AuthenticationResult.IdToken')

curl -H "Authorization: Bearer $TOKEN" $API_ENDPOINT/files
```

**Expected:** `{"files":[],"total":0}`

### 3. Test Frontend
```bash
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
  --output text)

echo "Open: https://$CLOUDFRONT_URL"
```

**Browser test checklist:**
- [ ] Login page loads
- [ ] Can login with student@test.com
- [ ] Dashboard displays
- [ ] Can upload a file
- [ ] Can view uploaded file
- [ ] Can download file

---

## 🎉 You're Live!

Your Campus Cloud system is now running!

**Access URLs:**
- Frontend: `https://<cloudfront-url>`
- API: `https://<api-id>.execute-api.us-east-1.amazonaws.com/dev`

**Test Accounts:**
- Student: `student@test.com` / `TempPass123!`
- Instructor: `instructor@test.com` / `TempPass123!`

---

## 🔧 Common Issues

### Issue: SAM build fails
```bash
# Check Python version
python3 --version  # Must be 3.11+

# Check requirements.txt exists
cat backend/requirements.txt

# Try with debug
sam build --debug
```

### Issue: Deployment timeout
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name campus-cloud-dev

# View events
aws cloudformation describe-stack-events --stack-name campus-cloud-dev
```

### Issue: CORS errors
```bash
# Verify API Gateway CORS settings
aws apigateway get-rest-api --rest-api-id <api-id>

# Check Lambda response headers (must include Access-Control-Allow-Origin)
```

### Issue: 401 Unauthorized
```bash
# Verify token
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=student@test.com,PASSWORD=YourPassword123!

# Check Cognito User Pool ID in config.js matches
```

---

## 🧹 Cleanup (Delete Everything)

```bash
# Empty S3 buckets first
FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

FILES_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name campus-cloud-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`FilesBucketName`].OutputValue' \
  --output text)

aws s3 rm s3://$FRONTEND_BUCKET --recursive
aws s3 rm s3://$FILES_BUCKET --recursive

# Delete stack
aws cloudformation delete-stack --stack-name campus-cloud-dev

# Wait for completion
aws cloudformation wait stack-delete-complete --stack-name campus-cloud-dev

echo "Cleanup complete!"
```

---

## 📚 Next Steps

1. **Customize Frontend**
   - Update branding in `frontend/src/`
   - Modify colors and styles
   - Add university logo

2. **Add Real Users**
   - Import users from CSV
   - Set up SSO with university identity provider
   - Configure email verification

3. **Enable Features**
   - Set up virus scanning (see STRETCH_FEATURES.md)
   - Add real-time notifications
   - Configure custom domain

4. **Production Deployment**
   - Deploy to separate AWS account
   - Enable WAF and Shield
   - Set up monitoring and alerts
   - Configure backup procedures

5. **Documentation**
   - Create user guides
   - Record training videos
   - Set up support channels

---

## 📖 Documentation

- **Full README**: [README.md](README.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **API Design**: [docs/API_DESIGN.md](docs/API_DESIGN.md)
- **Database Schema**: [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)
- **Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **IAM Policies**: [docs/IAM_POLICIES.md](docs/IAM_POLICIES.md)
- **Stretch Features**: [docs/STRETCH_FEATURES.md](docs/STRETCH_FEATURES.md)

---

## 🆘 Support

**Having issues?**
1. Check CloudWatch logs: `sam logs -n <function-name> --tail`
2. Review [DEPLOYMENT.md](docs/DEPLOYMENT.md) troubleshooting section
3. Search GitHub issues
4. Contact: support@campuscloud.edu

---

## 💰 Cost Estimate

**Monthly cost for 100 active users:**
- Lambda: $10
- API Gateway: $3.50
- DynamoDB: $12
- S3: $2.30
- CloudFront: $8.50
- Cognito: Free
- **Total: ~$36/month**

Set up budget alerts to monitor costs!

---

**🎓 Happy Cloud Computing!**