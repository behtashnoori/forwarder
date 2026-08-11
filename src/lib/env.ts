/**
 * Environment variables validation and configuration
 * This ensures consistent environment variable handling across the application
 */

// An empty VITE_API_URL intentionally selects the packaged same-origin gateway.
function validateEnv() {
  if (
    import.meta.env.DEV ||
    !import.meta.env.VITE_API_URL ||
    import.meta.env.VITE_API_URL === '__FORWARDER_SAME_ORIGIN__'
  ) return;
  const requiredVars = ['VITE_API_URL'] as const;
  const missingVars: string[] = [];
  for (const varName of requiredVars) {
    if (!import.meta.env[varName]) missingVars.push(varName);
  }
  if (missingVars.length > 0) {
    console.error('❌ Missing required environment variables:', missingVars);
    throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
  }
}

// API base URL: in dev use empty string so all requests go to same origin and Vite proxies /api to backend
const getApiUrl = (): string => {
  if (import.meta.env.DEV) return '';
  if (import.meta.env.VITE_API_URL === '__FORWARDER_SAME_ORIGIN__') return '';
  return import.meta.env.VITE_API_URL || '';
};

// Validate and export environment configuration
export const env = {
  // API Configuration (use getApiUrl() for runtime; API_URL kept for backward compat, may be overridden by getApiUrl in call sites)
  get API_URL(): string {
    return getApiUrl();
  },
  
  // App Configuration
  APP_NAME: import.meta.env.VITE_APP_NAME || 'Forwarder App',
  APP_VERSION: import.meta.env.VITE_APP_VERSION,
  
  // Development flags
  IS_DEVELOPMENT: import.meta.env.DEV,
  IS_PRODUCTION: import.meta.env.PROD,
} as const;

// Validate environment on module load
try {
  validateEnv();
  console.log('✅ Environment variables validated successfully');
  if (import.meta.env.DEV) {
    console.log('🔗 API (dev): relative /api via Vite proxy');
  } else {
    console.log('🔗 API URL:', env.API_URL || import.meta.env.VITE_API_URL);
  }
} catch (error) {
  console.error('❌ Environment validation failed:', error);
  // Don't throw in development to allow debugging
  if (import.meta.env.PROD) {
    throw error;
  }
}

export default env;

