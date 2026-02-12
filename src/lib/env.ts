/**
 * Environment variables validation and configuration
 * This ensures consistent environment variable handling across the application
 */

// Validate required environment variables
function validateEnv() {
  const requiredVars = ['VITE_API_URL'] as const;
  const missingVars: string[] = [];

  for (const varName of requiredVars) {
    if (!import.meta.env[varName]) {
      missingVars.push(varName);
    }
  }

  if (missingVars.length > 0) {
    console.error('❌ Missing required environment variables:', missingVars);
    console.error('Please check your .env file and ensure all required variables are set.');
    throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
  }
}

// API base URL: in browser use same host as page (port 5000) so app works from network/internet
const getApiUrl = (): string => {
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:5000`;
  }
  return import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';
};

// Validate and export environment configuration
export const env = {
  // API Configuration (use getApiUrl() for runtime; API_URL kept for backward compat, may be overridden by getApiUrl in call sites)
  get API_URL(): string {
    return getApiUrl();
  },
  
  // App Configuration
  APP_NAME: import.meta.env.VITE_APP_NAME || 'Forwarder App',
  APP_VERSION: import.meta.env.VITE_APP_VERSION || '1.0.0',
  
  // Development flags
  IS_DEVELOPMENT: import.meta.env.DEV,
  IS_PRODUCTION: import.meta.env.PROD,
} as const;

// Validate environment on module load
try {
  validateEnv();
  console.log('✅ Environment variables validated successfully');
  // Log API URL dynamically (will show correct URL in browser)
  if (typeof window !== 'undefined') {
    console.log('🔗 API URL (browser):', env.API_URL);
  } else {
    console.log('🔗 API URL (build-time):', import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000');
  }
} catch (error) {
  console.error('❌ Environment validation failed:', error);
  // Don't throw in development to allow debugging
  if (import.meta.env.PROD) {
    throw error;
  }
}

export default env;

