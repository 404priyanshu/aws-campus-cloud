# Campus Cloud - IAM Policies and Security

This document contains all IAM policies required for the Campus Cloud File Sharing & Submission System.

---

## Table of Contents

1. [Lambda Execution Role Policies](#lambda-execution-role-policies)
2. [API Gateway Policies](#api-gateway-policies)
3. [Developer/Deployer Policies](#developerdeployer-policies)
4. [Service-Specific Policies](#service-specific-policies)
5. [Least Privilege Examples](#least-privilege-examples)
6. [Security Best Practices](#security-best-practices)

---

## Lambda Execution Role Policies

### 1. Generate Presigned URL Lambda Policy

This Lambda needs access to S3 and DynamoDB.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/campus-cloud-*"
    },
    {
      "Sid": "S3PresignedURLAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::campus-cloud-files-*/*"
    },
    {
      "Sid": "DynamoDBFilesAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files/index/*"
      ]
    },
    {
      "Sid": "DynamoDBSharesReadAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-shares",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-shares/index/*"
      ]
    },
    {
      "Sid": "XRayTracingAccess",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Complete Upload Lambda Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/campus-cloud-*"
    },
    {
      "Sid": "S3VerifyUploadAccess",
      "Effect": "Allow",
      "Action": [
        "s3:HeadObject",
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::campus-cloud-files-*/*"
    },
    {
      "Sid": "DynamoDBUpdateAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/campus-cloud-*-files"
    },
    {
      "Sid": "XRayTracingAccess",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. List Files Lambda Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/campus-cloud-*"
    },
    {
      "Sid": "DynamoDBReadAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files/index/*",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-shares",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-shares/index/*"
      ]
    },
    {
      "Sid": "XRayTracingAccess",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

### 4. Share File Lambda Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/campus-cloud-*"
    },
    {
      "Sid": "DynamoDBFilesAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files/index/*"
      ]
    },
    {
      "Sid": "DynamoDBSharesAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-shares",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-shares/index/*"
      ]
    },
    {
      "Sid": "DynamoDBUsersReadAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-users",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-users/index/*"
      ]
    },
    {
      "Sid": "SNSPublishAccess",
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:campus-cloud-*"
    },
    {
      "Sid": "XRayTracingAccess",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5. Submit Assignment Lambda Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/campus-cloud-*"
    },
    {
      "Sid": "DynamoDBFilesReadAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-files/index/*"
      ]
    },
    {
      "Sid": "DynamoDBAssignmentsAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-assignments",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-assignments/index/*"
      ]
    },
    {
      "Sid": "DynamoDBSubmissionsAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-submissions",
        "arn:aws:dynamodb:*:*:table/campus-cloud-*-submissions/index/*"
      ]
    },
    {
      "Sid": "SNSPublishAccess",
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:campus-cloud-*"
    },
    {
      "Sid": "XRayTracingAccess",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## API Gateway Policies

### API Gateway Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/apigateway/*"
    },
    {
      "Sid": "LambdaInvokeAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:campus-cloud-*"
    }
  ]
}
```

### API Gateway Resource Policy (Optional - for IP whitelisting)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:*:*:*/*/GET/*"
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:*:*:*/*/*",
      "Condition": {
        "NotIpAddress": {
          "aws:SourceIp": [
            "YOUR_UNIVERSITY_IP_RANGE/24",
            "YOUR_VPN_IP/32"
          ]
        }
      }
    }
  ]
}
```

---

## Developer/Deployer Policies

### SAM Deployment Policy

This policy allows a developer to deploy using AWS SAM.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudFormationAccess",
      "Effect": "Allow",
      "Action": [
        "cloudformation:CreateStack",
        "cloudformation:UpdateStack",
        "cloudformation:DeleteStack",
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResource",
        "cloudformation:DescribeStackResources",
        "cloudformation:GetTemplate",
        "cloudformation:ValidateTemplate",
        "cloudformation:CreateChangeSet",
        "cloudformation:DescribeChangeSet",
        "cloudformation:ExecuteChangeSet",
        "cloudformation:DeleteChangeSet"
      ],
      "Resource": "arn:aws:cloudformation:*:*:stack/campus-cloud-*/*"
    },
    {
      "Sid": "S3DeploymentBucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::aws-sam-cli-managed-*",
        "arn:aws:s3:::aws-sam-cli-managed-*/*",
        "arn:aws:s3:::campus-cloud-*",
        "arn:aws:s3:::campus-cloud-*/*"
      ]
    },
    {
      "Sid": "LambdaDeploymentAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:DeleteFunction",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:ListVersionsByFunction",
        "lambda:PublishVersion",
        "lambda:CreateAlias",
        "lambda:UpdateAlias",
        "lambda:GetAlias",
        "lambda:ListTags",
        "lambda:TagResource",
        "lambda:UntagResource",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:GetPolicy"
      ],
      "Resource": "arn:aws:lambda:*:*:function:campus-cloud-*"
    },
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:DeleteRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/campus-cloud-*"
    },
    {
      "Sid": "APIGatewayManagement",
      "Effect": "Allow",
      "Action": [
        "apigateway:*"
      ],
      "Resource": "arn:aws:apigateway:*::/*"
    },
    {
      "Sid": "DynamoDBManagement",
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DeleteTable",
        "dynamodb:DescribeTable",
        "dynamodb:DescribeContinuousBackups",
        "dynamodb:DescribeTimeToLive",
        "dynamodb:UpdateTable",
        "dynamodb:UpdateTimeToLive",
        "dynamodb:UpdateContinuousBackups",
        "dynamodb:TagResource",
        "dynamodb:UntagResource",
        "dynamodb:ListTagsOfResource"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/campus-cloud-*"
    },
    {
      "Sid": "CognitoManagement",
      "Effect": "Allow",
      "Action": [
        "cognito-idp:CreateUserPool",
        "cognito-idp:DeleteUserPool",
        "cognito-idp:DescribeUserPool",
        "cognito-idp:UpdateUserPool",
        "cognito-idp:CreateUserPoolClient",
        "cognito-idp:DeleteUserPoolClient",
        "cognito-idp:DescribeUserPoolClient",
        "cognito-idp:UpdateUserPoolClient",
        "cognito-idp:CreateGroup",
        "cognito-idp:DeleteGroup",
        "cognito-idp:GetGroup"
      ],
      "Resource": "arn:aws:cognito-idp:*:*:userpool/*"
    },
    {
      "Sid": "CloudFrontManagement",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateDistribution",
        "cloudfront:GetDistribution",
        "cloudfront:GetDistributionConfig",
        "cloudfront:UpdateDistribution",
        "cloudfront:DeleteDistribution",
        "cloudfront:TagResource",
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation",
        "cloudfront:ListInvalidations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy",
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarms"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Service-Specific Policies

### S3 Bucket Policy (Files Bucket)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::campus-cloud-files-*/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    },
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::campus-cloud-files-*",
        "arn:aws:s3:::campus-cloud-files-*/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "AllowLambdaAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::campus-cloud-files-*/*",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "${AWS::AccountId}"
        }
      }
    }
  ]
}
```

### S3 Bucket Policy (Frontend Bucket)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::campus-cloud-frontend-*/*"
    },
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::campus-cloud-frontend-*",
        "arn:aws:s3:::campus-cloud-frontend-*/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

### DynamoDB Table Policy (Optional - for fine-grained access control)

DynamoDB doesn't support resource policies, but you can use IAM conditions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowUserToAccessOwnData",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/campus-cloud-*-files",
      "Condition": {
        "ForAllValues:StringEquals": {
          "dynamodb:LeadingKeys": [
            "${cognito-identity.amazonaws.com:sub}"
          ]
        }
      }
    }
  ]
}
```

---

## Least Privilege Examples

### Read-Only Access Policy

For monitoring or auditing users:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadOnlyAccess",
      "Effect": "Allow",
      "Action": [
        "cloudformation:Describe*",
        "cloudformation:Get*",
        "cloudformation:List*",
        "lambda:Get*",
        "lambda:List*",
        "dynamodb:Describe*",
        "dynamodb:List*",
        "dynamodb:Scan",
        "dynamodb:Query",
        "s3:Get*",
        "s3:List*",
        "apigateway:GET",
        "cognito-idp:Describe*",
        "cognito-idp:List*",
        "logs:Describe*",
        "logs:Get*",
        "logs:FilterLogEvents",
        "cloudwatch:Describe*",
        "cloudwatch:Get*",
        "cloudwatch:List*"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:ResourceTag/Project": "campus-cloud"
        }
      }
    }
  ]
}
```

### Student User Policy (Application Level)

This would be enforced by Lambda functions, not IAM:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "StudentFileOperations",
      "Effect": "Allow",
      "Action": [
        "campus-cloud:UploadFile",
        "campus-cloud:DownloadFile",
        "campus-cloud:ListOwnFiles",
        "campus-cloud:DeleteOwnFile",
        "campus-cloud:ShareFile",
        "campus-cloud:SubmitAssignment",
        "campus-cloud:ViewOwnSubmissions"
      ],
      "Resource": "*"
    }
  ]
}
```

### Instructor User Policy (Application Level)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InstructorOperations",
      "Effect": "Allow",
      "Action": [
        "campus-cloud:*File*",
        "campus-cloud:CreateAssignment",
        "campus-cloud:UpdateAssignment",
        "campus-cloud:DeleteAssignment",
        "campus-cloud:ListAssignments",
        "campus-cloud:ViewSubmissions",
        "campus-cloud:GradeSubmission"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Security Best Practices

### 1. Use Service Control Policies (SCPs)

If using AWS Organizations:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyRootAccountUsage",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:root"
        }
      }
    },
    {
      "Sid": "RequireMFAForProduction",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        },
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
```

### 2. Enable CloudTrail for Auditing

Ensure CloudTrail is logging all API calls:

```bash
aws cloudtrail create-trail \
  --name campus-cloud-audit-trail \
  --s3-bucket-name campus-cloud-audit-logs \
  --is-multi-region-trail \
  --enable-log-file-validation

aws cloudtrail start-logging --name campus-cloud-audit-trail
```

### 3. Use VPC Endpoints

For enhanced security, use VPC endpoints for AWS services:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyAccessFromOutsideVPC",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "*",
      "Resource": "arn:aws:dynamodb:*:*:table/campus-cloud-*",
      "Condition": {
        "StringNotEquals": {
          "aws:SourceVpce": "vpce-1234567890abcdef"
        }
      }
    }
  ]
}
```

### 4. Enable MFA Delete on S3

```bash
aws s3api put-bucket-versioning \
  --bucket campus-cloud-files-prod \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::123456789012:mfa/root-account-mfa-device 123456"
```

### 5. Use AWS Secrets Manager for Sensitive Data

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowLambdaToReadSecrets",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:campus-cloud/*"
    }
  ]
}
```

### 6. Implement IAM Permission Boundaries

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ServiceBoundary",
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "dynamodb:*",
        "lambda:*",
        "logs:*",
        "xray:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2"
          ]
        }
      }
    },
    {
      "Sid": "DenyDangerousActions",
      "Effect": "Deny",
      "Action": [
        "iam:CreateUser",
        "iam:DeleteUser",
        "iam:CreateAccessKey",
        "iam:DeleteAccessKey",
        "s3:DeleteBucket",
        "dynamodb:DeleteTable"
      ],
      "Resource": "*"
    }
  ]
}
```

### 7. Tag-Based Access Control

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowActionsOnTaggedResources",
      "Effect": "Allow",
      "Action": [
        "lambda:*",
        "dynamodb:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Environment": "${aws:PrincipalTag/Environment}"
        }
      }
    }
  ]
}
```

---

## Emergency Access Policy

For emergency situations:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EmergencyBreakGlassAccess",
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "YOUR_ADMIN_IP/32"
        },
        "DateGreaterThan": {
          "aws:CurrentTime": "2024-01-15T00:00:00Z"
        },
        "DateLessThan": {
          "aws:CurrentTime": "2024-01-15T23:59:59Z"
        }
      }
    }
  ]
}
```

**Note:** This policy should only be attached temporarily during emergencies.

---

## Policy Testing

### Test Lambda Execution Role

```bash
# Test as Lambda role
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/campus-cloud-dev-GeneratePresignedUrlRole \
  --role-session-name test-session

# Export credentials
export AWS_ACCESS_KEY_ID=<AccessKeyId>
export AWS_SECRET_ACCESS_KEY=<SecretAccessKey>
export AWS_SESSION_TOKEN=<SessionToken>

# Test S3 access
aws s3 ls s3://campus-cloud-files-dev/

# Test DynamoDB access
aws dynamodb scan --table-name campus-cloud-dev-files --max-items 5
```

### Policy Simulator

Use IAM Policy Simulator to test policies:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/campus-cloud-dev-LambdaRole \
  --action-names s3:GetObject dynamodb:PutItem \
  --resource-arns arn:aws:s3:::campus-cloud-files-dev/* arn:aws:dynamodb:us-east-1:123456789012:table/campus-cloud-dev-files
```

---

## Compliance and Auditing

### Generate IAM Credential Report

```bash
aws iam generate-credential-report
aws iam get-credential-report --output text --query Content | base64 --decode > credential-report.csv
```

### List All Policies Attached to Role

```bash
aws iam list-attached-role-policies --role-name campus-cloud-dev-GeneratePresignedUrlRole
aws iam list-role-policies --role-name campus-cloud-dev-GeneratePresignedUrlRole
```

### Access Analyzer

Enable IAM Access Analyzer:

```bash
aws accessanalyzer create-analyzer \
  --analyzer-name campus-cloud-analyzer \
  --type ACCOUNT
```

---

## Summary

This document provides comprehensive IAM policies for the Campus Cloud system. Key principles:

1. **Least Privilege** - Grant only necessary permissions
2. **Separation of Duties** - Different roles for different functions
3. **Defense in Depth** - Multiple layers of security
4. **Audit Everything** - Enable CloudTrail and logging
5. **Regular Reviews** - Periodically review and update policies
6. **Use MFA** - Require MFA for sensitive operations
7. **Encrypt Everything** - Use encryption at rest and in transit

For questions or security concerns, contact your security team or AWS support.