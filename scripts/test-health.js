#!/usr/bin/env node

/**
 * Health Check API Testing Script
 * Tests all health-related endpoints
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const TEST_ORIGIN = 'http://localhost:8109';

// Health check tests
const healthTests = [
  {
    name: 'Basic Health Check',
    url: '/api/health',
    method: 'GET',
    description: 'بررسی سلامت API'
  },
  {
    name: 'System Health Status',
    url: '/api/monitoring/health',
    method: 'GET',
    description: 'بررسی سلامت سیستم'
  },
  {
    name: 'System Metrics',
    url: '/api/monitoring/metrics',
    method: 'GET',
    description: 'بررسی متریک‌ها',
    requiresAuth: true
  }
];

async function testHealthEndpoint(test) {
  try {
    console.log(`🧪 Testing: ${test.name}`);
    console.log(`   📝 Description: ${test.description}`);
    console.log(`   🔗 URL: ${test.url}`);
    console.log(`   📡 Method: ${test.method}`);
    
    if (test.requiresAuth) {
      console.log(`   🔐 Note: This endpoint requires authentication`);
    }
    
    const requestOptions = {
      method: test.method,
      headers: {
        'Origin': TEST_ORIGIN,
        'Content-Type': 'application/json'
      }
    };
    
    const response = await fetch(`${API_BASE_URL}${test.url}`, requestOptions);
    
    const isSuccess = response.status >= 200 && response.status < 300;
    const statusIcon = isSuccess ? '✅' : '❌';
    
    console.log(`   ${statusIcon} Status: ${response.status}`);
    
    // Check CORS headers
    const corsOrigin = response.headers.get('Access-Control-Allow-Origin');
    const corsMethods = response.headers.get('Access-Control-Allow-Methods');
    const corsHeaders = response.headers.get('Access-Control-Allow-Headers');
    
    console.log(`   🌐 CORS Headers:`);
    console.log(`      ${corsOrigin ? '✅' : '❌'} Allow-Origin: ${corsOrigin || 'Not set'}`);
    console.log(`      ${corsMethods ? '✅' : '❌'} Allow-Methods: ${corsMethods || 'Not set'}`);
    console.log(`      ${corsHeaders ? '✅' : '❌'} Allow-Headers: ${corsHeaders || 'Not set'}`);
    
    // Get response content
    const contentType = response.headers.get('Content-Type');
    let responseData = null;
    
    if (contentType && contentType.includes('application/json')) {
      try {
        responseData = await response.json();
        console.log(`   📊 Response Data:`);
        console.log(`      Type: JSON`);
        console.log(`      Keys: ${Object.keys(responseData).join(', ')}`);
        
        // Show specific data for health endpoints
        if (test.url === '/api/health') {
          console.log(`      Message: ${responseData}`);
        } else if (test.url === '/api/monitoring/health') {
          console.log(`      Status: ${responseData.status || 'N/A'}`);
          console.log(`      Timestamp: ${responseData.timestamp || 'N/A'}`);
        } else if (test.url === '/api/monitoring/metrics') {
          console.log(`      System Info: ${responseData.system ? 'Available' : 'N/A'}`);
          console.log(`      Application Info: ${responseData.application ? 'Available' : 'N/A'}`);
        }
      } catch (e) {
        console.log(`   ⚠️  Could not parse JSON response`);
      }
    } else {
      const textData = await response.text();
      console.log(`   📄 Response: ${textData.substring(0, 100)}${textData.length > 100 ? '...' : ''}`);
    }
    
    console.log('');
    return { success: isSuccess, status: response.status, data: responseData };
    
  } catch (error) {
    console.log(`   ❌ Error: ${error.message}`);
    console.log('');
    return { success: false, error: error.message };
  }
}

async function runHealthTests() {
  console.log('🏥 Starting Health Check API Tests\n');
  console.log(`🔗 API Base URL: ${API_BASE_URL}`);
  console.log(`🌐 Test Origin: ${TEST_ORIGIN}\n`);
  console.log('=' .repeat(60));
  
  const results = [];
  
  for (const test of healthTests) {
    const result = await testHealthEndpoint(test);
    results.push({ ...test, ...result });
    
    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  
  // Summary
  console.log('📊 Test Summary:');
  console.log('=' .repeat(60));
  
  const passed = results.filter(r => r.success).length;
  const total = results.length;
  
  results.forEach(result => {
    const icon = result.success ? '✅' : '❌';
    const statusText = result.success ? `Status: ${result.status}` : `Error: ${result.error || 'Failed'}`;
    console.log(`${icon} ${result.name} - ${statusText}`);
  });
  
  console.log(`\n🎯 Results: ${passed}/${total} tests passed`);
  
  if (passed === total) {
    console.log('🎉 All health check tests passed! API is healthy.');
  } else {
    console.log('⚠️  Some health check tests failed. Please check the issues above.');
    
    // Provide troubleshooting tips
    console.log('\n🔧 Troubleshooting Tips:');
    console.log('1. Make sure the backend server is running (default port 8000)');
    console.log('2. Check if the server is accessible at', API_BASE_URL);
    console.log('3. Verify that all required dependencies are installed');
    console.log('4. Check server logs for any error messages');
  }
  
  return passed === total;
}

// Run tests
runHealthTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Test runner error:', error);
  process.exit(1);
});
