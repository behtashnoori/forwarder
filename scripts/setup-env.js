#!/usr/bin/env node

/**
 * Environment Setup Script
 * This script helps set up the environment variables correctly
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const projectRoot = path.join(__dirname, '..');
const envPath = path.join(projectRoot, '.env');
const envExamplePath = path.join(projectRoot, '.env.example');

function createEnvFile() {
  const envContent = `# ===========================================
# FRONTEND ENVIRONMENT VARIABLES (Vite)
# ===========================================
VITE_API_URL=http://127.0.0.1:8000
VITE_APP_NAME=Forwarder App
VITE_APP_VERSION=1.0.0

# ===========================================
# BACKEND ENVIRONMENT VARIABLES (Flask)
# ===========================================

# Database Configuration
# Use PostgreSQL for production, SQLite for development
DATABASE_URL=postgresql+psycopg2://postgres:bagheri13@127.0.0.1:5432/forwarder_db

# CORS Configuration - Allow multiple origins for development
CORS_ORIGIN=http://localhost:8107,http://localhost:8080,http://localhost:3000,http://127.0.0.1:8107,http://127.0.0.1:8080
# Set to 1 to allow any origin (for network/internet access from e.g. http://SERVER_IP:8080)
CORS_ALLOW_ALL_ORIGINS=1

# SLA Configuration
SLA_HOURS=2

# Security Configuration
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Development Configuration
FLASK_ENV=development
FLASK_DEBUG=true

# Logging Configuration
LOG_LEVEL=INFO`;

  try {
    if (!fs.existsSync(envPath)) {
      fs.writeFileSync(envPath, envContent);
      console.log('✅ .env file created successfully');
    } else {
      console.log('ℹ️  .env file already exists');
    }
  } catch (error) {
    console.error('❌ Error creating .env file:', error.message);
  }
}

function validateEnvFile() {
  try {
    if (!fs.existsSync(envPath)) {
      console.log('❌ .env file not found');
      return false;
    }

    const envContent = fs.readFileSync(envPath, 'utf8');
    const requiredVars = ['VITE_API_URL'];
    
    for (const varName of requiredVars) {
      if (!envContent.includes(varName)) {
        console.log(`❌ Missing required variable: ${varName}`);
        return false;
      }
    }
    
    console.log('✅ .env file validation passed');
    return true;
  } catch (error) {
    console.error('❌ Error validating .env file:', error.message);
    return false;
  }
}

function main() {
  console.log('🚀 Setting up environment variables...\n');
  
  createEnvFile();
  const isValid = validateEnvFile();
  
  if (isValid) {
    console.log('\n✅ Environment setup completed successfully!');
    console.log('📝 You can now start your development servers:');
    console.log('   Frontend: npm run dev');
    console.log('   Backend: flask run');
  } else {
    console.log('\n❌ Environment setup failed. Please check the errors above.');
    process.exit(1);
  }
}

// Run if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { createEnvFile, validateEnvFile };
