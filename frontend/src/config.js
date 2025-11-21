// AWS Configuration for Campus Cloud Frontend
// Replace these values with your actual AWS resource IDs after deployment

export const config = {
  // AWS Region
  region: 'us-east-1', // Change to your deployed region

  // Cognito Configuration
  cognito: {
    userPoolId: 'us-east-1_XXXXXXXXX', // Replace with your User Pool ID from SAM outputs
    userPoolClientId: 'xxxxxxxxxxxxxxxxxxxxxxxxxx', // Replace with your User Pool Client ID
    identityPoolId: '', // Optional: for federated identities
  },

  // API Gateway Configuration
  api: {
    endpoint: 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev', // Replace with your API endpoint
    timeout: 30000, // 30 seconds
  },

  // S3 Configuration
  s3: {
    bucket: 'campus-cloud-dev-files-123456789012', // Replace with your S3 bucket name
    region: 'us-east-1',
  },

  // Application Settings
  app: {
    name: 'Campus Cloud',
    version: '1.0.0',
    maxFileSize: 104857600, // 100MB in bytes
    allowedFileTypes: [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'text/plain',
      'text/csv',
      'image/jpeg',
      'image/png',
      'image/gif',
      'application/zip',
      'application/x-zip-compressed',
      'video/mp4',
      'video/mpeg',
    ],
    defaultPageSize: 20,
    maxPageSize: 100,
  },

  // Feature Flags
  features: {
    enableSharing: true,
    enableAssignments: true,
    enableNotifications: false,
    enableVersioning: true,
    enableVirusScanning: false,
  },
};

// Helper function to validate configuration
export const validateConfig = () => {
  const errors = [];

  if (!config.cognito.userPoolId || config.cognito.userPoolId.includes('XXXXX')) {
    errors.push('Cognito User Pool ID is not configured');
  }

  if (!config.cognito.userPoolClientId || config.cognito.userPoolClientId.includes('xxxxx')) {
    errors.push('Cognito User Pool Client ID is not configured');
  }

  if (!config.api.endpoint || config.api.endpoint.includes('xxxxxx')) {
    errors.push('API Gateway endpoint is not configured');
  }

  if (errors.length > 0) {
    console.warn('⚠️ Configuration Warnings:', errors);
    return false;
  }

  console.log('✅ Configuration validated successfully');
  return true;
};

// Export for use in development vs production
export const isDevelopment = import.meta.env.MODE === 'development';
export const isProduction = import.meta.env.MODE === 'production';

export default config;
