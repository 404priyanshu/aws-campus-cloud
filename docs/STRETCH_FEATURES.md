# Campus Cloud - Stretch Features

This document outlines optional advanced features that can be added to enhance the Campus Cloud File Sharing & Submission System.

---

## Table of Contents

1. [Virus Scanning with ClamAV](#1-virus-scanning-with-clamav)
2. [Real-time Notifications with WebSockets](#2-real-time-notifications-with-websockets)
3. [Advanced Search with OpenSearch](#3-advanced-search-with-opensearch)
4. [File Versioning and History](#4-file-versioning-and-history)
5. [Expiring Share Links](#5-expiring-share-links)
6. [Analytics Dashboard](#6-analytics-dashboard)
7. [Mobile Application](#7-mobile-application)
8. [Video Processing and Streaming](#8-video-processing-and-streaming)
9. [Collaborative Editing](#9-collaborative-editing)
10. [AI-Powered Features](#10-ai-powered-features)

---

## 1. Virus Scanning with ClamAV

### Overview
Automatically scan uploaded files for viruses and malware using ClamAV antivirus.

### Architecture
```
S3 Upload → S3 Event Notification → Lambda (ClamAV) → Quarantine/Approve → Update DynamoDB
```

### Implementation

#### Lambda Function with ClamAV Layer
```python
# lambda_function.py - virus_scanner
import json
import boto3
import os
import subprocess
from urllib.parse import unquote_plus

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')

QUARANTINE_BUCKET = os.environ['QUARANTINE_BUCKET']
FILES_TABLE = os.environ['FILES_TABLE']

def lambda_handler(event, context):
    """
    Triggered by S3 event when file is uploaded
    """
    # Get uploaded file info
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    print(f"Scanning file: {bucket}/{key}")
    
    # Download file
    download_path = f'/tmp/{os.path.basename(key)}'
    s3_client.download_file(bucket, key, download_path)
    
    # Update ClamAV database
    subprocess.run(['/opt/bin/freshclam', '--config-file=/opt/etc/freshclam.conf'], 
                   capture_output=True)
    
    # Scan file
    result = subprocess.run(
        ['/opt/bin/clamscan', '-v', download_path],
        capture_output=True,
        text=True
    )
    
    is_infected = result.returncode != 0
    
    # Parse file ID from key
    file_id = key.split('/')[-1]
    
    table = dynamodb.Table(FILES_TABLE)
    
    if is_infected:
        # Move to quarantine
        s3_client.copy_object(
            Bucket=QUARANTINE_BUCKET,
            Key=key,
            CopySource={'Bucket': bucket, 'Key': key}
        )
        s3_client.delete_object(Bucket=bucket, Key=key)
        
        # Update status
        table.update_item(
            Key={'userId': key.split('/')[1], 'fileId': file_id},
            UpdateExpression='SET virusScanStatus = :status, virusScanDate = :date',
            ExpressionAttributeValues={
                ':status': 'infected',
                ':date': datetime.utcnow().isoformat() + 'Z'
            }
        )
        
        # Notify user
        notify_user_virus_detected(key)
        
        print(f"INFECTED: {key} - Moved to quarantine")
    else:
        # Mark as clean
        table.update_item(
            Key={'userId': key.split('/')[1], 'fileId': file_id},
            UpdateExpression='SET virusScanStatus = :status, virusScanDate = :date',
            ExpressionAttributeValues={
                ':status': 'clean',
                ':date': datetime.utcnow().isoformat() + 'Z'
            }
        )
        
        print(f"CLEAN: {key}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'file': key,
            'status': 'infected' if is_infected else 'clean'
        })
    }

def notify_user_virus_detected(key):
    """Send notification when virus is detected"""
    # Implementation depends on notification system
    pass
```

#### SAM Template Addition
```yaml
VirusScannerFunction:
  Type: AWS::Serverless::Function
  Properties:
    FunctionName: !Sub '${AWS::StackName}-virus-scanner'
    CodeUri: ../backend/lambdas/
    Handler: virus_scanner.lambda_handler
    Runtime: python3.11
    Timeout: 300
    MemorySize: 3008
    Layers:
      - !Ref ClamAVLayer
    Environment:
      Variables:
        QUARANTINE_BUCKET: !Ref QuarantineBucket
        FILES_TABLE: !Ref FilesTable
    Events:
      S3Upload:
        Type: S3
        Properties:
          Bucket: !Ref FilesBucket
          Events: s3:ObjectCreated:*
    Policies:
      - S3CrudPolicy:
          BucketName: !Ref FilesBucket
      - S3CrudPolicy:
          BucketName: !Ref QuarantineBucket
      - DynamoDBCrudPolicy:
          TableName: !Ref FilesTable

ClamAVLayer:
  Type: AWS::Serverless::LayerVersion
  Properties:
    LayerName: clamav-layer
    Description: ClamAV binaries and definitions
    ContentUri: layers/clamav/
    CompatibleRuntimes:
      - python3.11
    RetentionPolicy: Delete

QuarantineBucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: !Sub '${AWS::StackName}-quarantine-${AWS::AccountId}'
    LifecycleConfiguration:
      Rules:
        - Id: DeleteOldQuarantinedFiles
          Status: Enabled
          ExpirationInDays: 90
```

#### Building ClamAV Layer
```bash
# Create layer directory
mkdir -p layers/clamav/bin layers/clamav/etc

# Download ClamAV (use pre-built binaries or compile)
# For Lambda, use: https://github.com/awslabs/clamav-aws-lambda

cd layers/clamav
curl -L https://github.com/awslabs/clamav-aws-lambda/releases/download/v1.0.0/clamav-layer.zip -o clamav.zip
unzip clamav.zip
cd ../..

# Package layer
cd layers/clamav
zip -r ../../clamav-layer.zip .
cd ../..
```

### Cost Estimate
- **Lambda execution**: ~$5-10/month (1000 scans)
- **S3 quarantine storage**: ~$1/month
- **Total**: ~$6-11/month

---

## 2. Real-time Notifications with WebSockets

### Overview
Push real-time notifications to users using API Gateway WebSocket API.

### Architecture
```
User Event → Lambda → API Gateway WebSocket → Connected Clients
```

### Implementation

#### WebSocket Lambda Functions

**Connection Handler:**
```python
# websocket_connect.py
import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
connections_table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    # Get user from JWT token
    user_id = event['requestContext']['authorizer']['userId']
    
    # Store connection
    connections_table.put_item(
        Item={
            'connectionId': connection_id,
            'userId': user_id,
            'connectedAt': datetime.utcnow().isoformat() + 'Z'
        }
    )
    
    return {'statusCode': 200, 'body': 'Connected'}
```

**Disconnect Handler:**
```python
# websocket_disconnect.py
def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    
    connections_table.delete_item(
        Key={'connectionId': connection_id}
    )
    
    return {'statusCode': 200, 'body': 'Disconnected'}
```

**Send Notification:**
```python
# send_notification.py
import boto3
import json
import os

apigateway = boto3.client('apigatewaymanagementapi',
    endpoint_url=os.environ['WEBSOCKET_ENDPOINT']
)
dynamodb = boto3.resource('dynamodb')

def notify_user(user_id, notification):
    """Send notification to all user's connections"""
    connections_table = dynamodb.Table(os.environ['CONNECTIONS_TABLE'])
    
    # Get user connections
    response = connections_table.query(
        IndexName='UserIdIndex',
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    
    for connection in response['Items']:
        try:
            apigateway.post_to_connection(
                ConnectionId=connection['connectionId'],
                Data=json.dumps(notification).encode('utf-8')
            )
        except apigateway.exceptions.GoneException:
            # Connection no longer exists
            connections_table.delete_item(
                Key={'connectionId': connection['connectionId']}
            )
```

#### Frontend Integration
```javascript
// websocket-client.js
import { config } from './config';

class WebSocketClient {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
  }
  
  connect(token) {
    const wsUrl = `${config.websocket.endpoint}?token=${token}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    this.ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      this.handleNotification(notification);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket closed');
      // Reconnect after 5 seconds
      setTimeout(() => this.connect(token), 5000);
    };
  }
  
  handleNotification(notification) {
    // Trigger event listeners
    const listeners = this.listeners.get(notification.type) || [];
    listeners.forEach(callback => callback(notification));
    
    // Show browser notification
    if (Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/logo192.png'
      });
    }
  }
  
  on(type, callback) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type).push(callback);
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

export default new WebSocketClient();
```

#### SAM Template Addition
```yaml
WebSocketApi:
  Type: AWS::ApiGatewayV2::Api
  Properties:
    Name: !Sub '${AWS::StackName}-websocket'
    ProtocolType: WEBSOCKET
    RouteSelectionExpression: "$request.body.action"

WebSocketStage:
  Type: AWS::ApiGatewayV2::Stage
  Properties:
    ApiId: !Ref WebSocketApi
    StageName: prod
    AutoDeploy: true

ConnectionsTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: !Sub '${AWS::StackName}-connections'
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: connectionId
        AttributeType: S
      - AttributeName: userId
        AttributeType: S
    KeySchema:
      - AttributeName: connectionId
        KeyType: HASH
    GlobalSecondaryIndexes:
      - IndexName: UserIdIndex
        KeySchema:
          - AttributeName: userId
            KeyType: HASH
        Projection:
          ProjectionType: ALL
    TimeToLiveSpecification:
      AttributeName: ttl
      Enabled: true
```

---

## 3. Advanced Search with OpenSearch

### Overview
Full-text search across files with faceted filtering.

### Architecture
```
DynamoDB Stream → Lambda → OpenSearch → Search API
```

### Implementation

#### Index Lambda Function
```python
# opensearch_indexer.py
import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, 
                   region, service, session_token=credentials.token)

opensearch_client = OpenSearch(
    hosts=[{'host': os.environ['OPENSEARCH_ENDPOINT'], 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

def lambda_handler(event, context):
    """Index DynamoDB changes to OpenSearch"""
    for record in event['Records']:
        if record['eventName'] == 'INSERT' or record['eventName'] == 'MODIFY':
            # Index new/updated item
            item = record['dynamodb']['NewImage']
            
            document = {
                'fileId': item['fileId']['S'],
                'filename': item['filename']['S'],
                'description': item.get('description', {}).get('S', ''),
                'tags': item.get('tags', {}).get('L', []),
                'contentType': item['contentType']['S'],
                'uploadedAt': item['uploadedAt']['S'],
                'userId': item['userId']['S']
            }
            
            opensearch_client.index(
                index='campus-cloud-files',
                id=item['fileId']['S'],
                body=document
            )
            
        elif record['eventName'] == 'REMOVE':
            # Delete from index
            file_id = record['dynamodb']['Keys']['fileId']['S']
            opensearch_client.delete(
                index='campus-cloud-files',
                id=file_id
            )
    
    return {'statusCode': 200}
```

#### Search Lambda Function
```python
# search_files.py
def lambda_handler(event, context):
    query_string = event['queryStringParameters'].get('q', '')
    filters = event['queryStringParameters'].get('filters', {})
    
    # Build OpenSearch query
    search_query = {
        'query': {
            'bool': {
                'must': [
                    {
                        'multi_match': {
                            'query': query_string,
                            'fields': ['filename^3', 'description^2', 'tags']
                        }
                    }
                ],
                'filter': []
            }
        },
        'highlight': {
            'fields': {
                'filename': {},
                'description': {}
            }
        },
        'aggs': {
            'file_types': {
                'terms': {'field': 'contentType'}
            },
            'upload_dates': {
                'date_histogram': {
                    'field': 'uploadedAt',
                    'calendar_interval': 'month'
                }
            }
        }
    }
    
    # Add filters
    if 'contentType' in filters:
        search_query['query']['bool']['filter'].append({
            'term': {'contentType': filters['contentType']}
        })
    
    # Execute search
    results = opensearch_client.search(
        index='campus-cloud-files',
        body=search_query
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'results': [hit['_source'] for hit in results['hits']['hits']],
            'total': results['hits']['total']['value'],
            'aggregations': results['aggregations']
        })
    }
```

### Cost Estimate
- **OpenSearch t3.small**: ~$30-50/month
- **Lambda indexing**: ~$2/month
- **Total**: ~$32-52/month

---

## 4. File Versioning and History

### Overview
Track and restore previous versions of files.

### Implementation

S3 versioning is already enabled in the template. Add UI and API:

```python
# get_file_versions.py
def lambda_handler(event, context):
    file_id = event['pathParameters']['fileId']
    
    # Get file metadata
    files_table = dynamodb.Table(os.environ['FILES_TABLE'])
    response = files_table.query(
        IndexName='FileIdIndex',
        KeyConditionExpression='fileId = :fid',
        ExpressionAttributeValues={':fid': file_id}
    )
    
    if not response['Items']:
        return {'statusCode': 404, 'body': 'File not found'}
    
    file_item = response['Items'][0]
    s3_key = file_item['s3Key']
    
    # Get all versions from S3
    s3_client = boto3.client('s3')
    versions = s3_client.list_object_versions(
        Bucket=os.environ['S3_BUCKET'],
        Prefix=s3_key
    )
    
    version_list = []
    for version in versions.get('Versions', []):
        version_list.append({
            'versionId': version['VersionId'],
            'lastModified': version['LastModified'].isoformat(),
            'size': version['Size'],
            'isLatest': version.get('IsLatest', False)
        })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'fileId': file_id,
            'filename': file_item['filename'],
            'versions': version_list
        })
    }
```

### Frontend Component
```jsx
// FileVersionHistory.jsx
import React, { useState, useEffect } from 'react';
import { getFileVersions, downloadFileVersion } from '../services/api';

const FileVersionHistory = ({ fileId }) => {
  const [versions, setVersions] = useState([]);
  
  useEffect(() => {
    loadVersions();
  }, [fileId]);
  
  const loadVersions = async () => {
    const data = await getFileVersions(fileId);
    setVersions(data.versions);
  };
  
  const handleRestore = async (versionId) => {
    await downloadFileVersion(fileId, versionId);
  };
  
  return (
    <div className="version-history">
      <h3>Version History</h3>
      <ul>
        {versions.map((version) => (
          <li key={version.versionId}>
            <span>{new Date(version.lastModified).toLocaleString()}</span>
            <span>{(version.size / 1024).toFixed(2)} KB</span>
            {version.isLatest && <span className="badge">Current</span>}
            <button onClick={() => handleRestore(version.versionId)}>
              Download
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FileVersionHistory;
```

---

## 5. Expiring Share Links

### Overview
Already implemented with DynamoDB TTL! Just need UI updates.

### Enhanced Implementation
```python
# generate_public_link.py
def lambda_handler(event, context):
    """Generate time-limited public share link"""
    file_id = event['pathParameters']['fileId']
    body = json.loads(event['body'])
    
    expiry_hours = body.get('expiryHours', 24)
    max_downloads = body.get('maxDownloads', 10)
    
    # Create share token
    share_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
    
    # Store in DynamoDB
    shares_table = dynamodb.Table(os.environ['PUBLIC_SHARES_TABLE'])
    shares_table.put_item(
        Item={
            'shareToken': share_token,
            'fileId': file_id,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
            'expiresAt': expires_at.isoformat() + 'Z',
            'maxDownloads': max_downloads,
            'downloadCount': 0,
            'ttl': int(expires_at.timestamp())
        }
    )
    
    # Generate public URL
    public_url = f"https://{os.environ['CLOUDFRONT_DOMAIN']}/share/{share_token}"
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'publicUrl': public_url,
            'expiresAt': expires_at.isoformat() + 'Z',
            'maxDownloads': max_downloads
        })
    }
```

---

## 6. Analytics Dashboard

### Overview
Track usage metrics and generate insights.

### Implementation

#### CloudWatch Custom Metrics
```python
# In each Lambda, add metrics
import boto3
cloudwatch = boto3.client('cloudwatch')

def publish_metric(metric_name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='CampusCloud',
        MetricData=[{
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow()
        }]
    )

# Example usage
publish_metric('FilesUploaded', 1)
publish_metric('StorageUsed', file_size, 'Bytes')
```

#### QuickSight Dashboard
```bash
# Create QuickSight analysis
aws quicksight create-analysis \
  --aws-account-id $ACCOUNT_ID \
  --analysis-id campus-cloud-analytics \
  --name "Campus Cloud Analytics" \
  --source-entity file://quicksight-template.json
```

#### Custom Analytics API
```python
# analytics.py
def lambda_handler(event, context):
    """Get analytics data"""
    time_range = event['queryStringParameters'].get('range', '7d')
    
    # Query DynamoDB for metrics
    files_table = dynamodb.Table(os.environ['FILES_TABLE'])
    
    # Get total files
    response = files_table.scan(Select='COUNT')
    total_files = response['Count']
    
    # Get storage usage
    response = files_table.scan(
        ProjectionExpression='fileSize'
    )
    total_storage = sum(item['fileSize'] for item in response['Items'])
    
    # Get active users (from CloudWatch Logs Insights)
    logs_client = boto3.client('logs')
    query = """
    fields @timestamp, userId
    | stats count() by userId
    | count()
    """
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'totalFiles': total_files,
            'totalStorage': total_storage,
            'activeUsers': active_users,
            'uploadsToday': uploads_today
        })
    }
```

---

## 7. Mobile Application

### Overview
React Native mobile app for iOS and Android.

### Key Features
- Biometric authentication
- Offline file access
- Camera integration
- Push notifications

### Implementation Outline
```javascript
// App.js
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import * as LocalAuthentication from 'expo-local-authentication';
import * as FileSystem from 'expo-file-system';
import * as Notifications from 'expo-notifications';

const Stack = createStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Files" component={FilesScreen} />
        <Stack.Screen name="Upload" component={UploadScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
```

---

## 8. Video Processing and Streaming

### Overview
Process uploaded videos and stream with adaptive bitrate.

### Architecture
```
S3 Upload → Lambda → MediaConvert → S3 (HLS) → CloudFront
```

### Implementation
```python
# video_processor.py
import boto3

mediaconvert = boto3.client('mediaconvert', endpoint_url=os.environ['MEDIACONVERT_ENDPOINT'])

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # Check if video file
    if not key.endswith(('.mp4', '.mov', '.avi')):
        return
    
    # Create MediaConvert job
    job = {
        'Role': os.environ['MEDIACONVERT_ROLE'],
        'Settings': {
            'Inputs': [{
                'FileInput': f's3://{bucket}/{key}',
                'AudioSelectors': {'Audio Selector 1': {'DefaultSelection': 'DEFAULT'}},
                'VideoSelector': {}
            }],
            'OutputGroups': [{
                'Name': 'HLS',
                'OutputGroupSettings': {
                    'Type': 'HLS_GROUP_SETTINGS',
                    'HlsGroupSettings': {
                        'Destination': f's3://{bucket}/processed/{key}/',
                        'SegmentLength': 10
                    }
                },
                'Outputs': [
                    {'VideoDescription': {'Width': 1920, 'Height': 1080}},
                    {'VideoDescription': {'Width': 1280, 'Height': 720}},
                    {'VideoDescription': {'Width': 854, 'Height': 480}}
                ]
            }]
        }
    }
    
    response = mediaconvert.create_job(**job)
    return response
```

---

## 9. Collaborative Editing

### Overview
Real-time collaborative document editing.

### Technologies
- Y.js for CRDT
- WebSocket for synchronization
- CodeMirror/Monaco for editing

### Architecture
```
Client ←→ WebSocket API ←→ Lambda ←→ DynamoDB (document state)
```

---

## 10. AI-Powered Features

### Overview
Leverage AWS AI services for intelligent features.

### Features

#### A. Automatic File Classification
```python
# classify_file.py
import boto3

comprehend = boto3.client('comprehend')
textract = boto3.client('textract')

def classify_document(s3_key):
    # Extract text
    response = textract.start_document_text_detection(
        DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': s3_key}}
    )
    
    # Get extracted text
    text = get_extracted_text(response['JobId'])
    
    # Classify with Comprehend
    classification = comprehend.classify_document(
        Text=text,
        EndpointArn=os.environ['CLASSIFIER_ENDPOINT']
    )
    
    return classification['Classes'][0]['Name']
```

#### B. Content Moderation
```python
# moderate_content.py
import boto3

rekognition = boto3.client('rekognition')

def moderate_image(s3_key):
    response = rekognition.detect_moderation_labels(
        Image={'S3Object': {'Bucket': bucket, 'Name': s3_key}},
        MinConfidence=90
    )
    
    inappropriate = any(
        label['Name'] in ['Explicit Nudity', 'Violence', 'Hate Symbols']
        for label in response['ModerationLabels']
    )
    
    return inappropriate
```

#### C. Smart Search Suggestions
```python
# search_suggestions.py
import boto3

comprehend = boto3.client('comprehend')

def get_suggestions(query):
    # Extract key phrases
    response = comprehend.detect_key_phrases(
        Text=query,
        LanguageCode='en'
    )
    
    suggestions = [phrase['Text'] for phrase in response['KeyPhrases']]
    return suggestions
```

---

## Implementation Priority

### Phase 1 (Quick Wins)
1. Expiring Share Links (already mostly implemented)
2. File Versioning UI (S3 already configured)
3. Basic Analytics Dashboard

### Phase 2 (Medium Effort)
1. Virus Scanning
2. Real-time Notifications
3. Enhanced Search

### Phase 3 (Advanced)
1. Video Processing
2. Mobile App
3. AI Features
4. Collaborative Editing

---

## Cost Estimates (All Features)

| Feature | Monthly Cost (100 users) |
|---------|-------------------------|
| Virus Scanning | $6-11 |
| WebSocket Notifications | $5-10 |
| OpenSearch | $32-52 |
| File Versioning | $2-5 (storage) |
| Expiring Links | $1-2 |
| Analytics | $5-10 |
| Video Processing | $20-50 (if used) |
| AI Services | $10-30 (if used) |
| **Total** | **$81-170/month** |

---

## Conclusion

These stretch features can significantly enhance the Campus Cloud system. Start with high-impact, low-effort features like expiring links and versioning, then gradually add more advanced capabilities based on user demand and budget.

For implementation help on any feature, refer to AWS documentation or contact the development team.