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

// Validate and export environment configuration
export const env = {
  // API Configuration
  API_URL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000',
  
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
  console.log('🔗 API URL:', env.API_URL);
} catch (error) {
  console.error('❌ Environment validation failed:', error);
  // Don't throw in development to allow debugging
  if (import.meta.env.PROD) {
    throw error;
  }
}

export default env;

