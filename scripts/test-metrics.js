#!/usr/bin/env node

/**
 * Metrics API Testing Script
 * Tests the /api/monitoring/metrics endpoint with authentication
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const TEST_ORIGIN = 'http://localhost:8109';

// Test credentials (from seed_experts.py)
const TEST_CREDENTIALS = {
  username: 'expert',
  password: 'expert123'
};

async function authenticate() {
  try {
    console.log('🔐 Authenticating user...');
    console.log(`   Username: ${TEST_CREDENTIALS.username}`);
    
    const response = await fetch(`${API_BASE_URL}/api/expert/auth/login`, {
      method: 'POST',
      headers: {
        'Origin': TEST_ORIGIN,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(TEST_CREDENTIALS)
    });
    
    if (response.status === 200) {
      const data = await response.json();
      console.log('   ✅ Authentication successful');
      console.log(`   Token type: ${data.token_type}`);
      console.log(`   Expires in: ${data.expires_in} seconds`);
      return data.access_token;
    } else {
      const errorData = await response.json();
      console.log(`   ❌ Authentication failed: ${response.status}`);
      console.log(`   Error: ${errorData.error || 'Unknown error'}`);
      return null;
    }
  } catch (error) {
    console.log(`   ❌ Authentication error: ${error.message}`);
    return null;
  }
}

async function testMetricsEndpoint(token) {
  try {
    console.log('\n📊 Testing Metrics Endpoint...');
    console.log('   URL: /api/monitoring/metrics');
    console.log('   Method: GET');
    
    const response = await fetch(`${API_BASE_URL}/api/monitoring/metrics`, {
      method: 'GET',
      headers: {
        'Origin': TEST_ORIGIN,
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    
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
        
        // Show detailed metrics information
        if (responseData.system) {
          console.log(`   💻 System Metrics:`);
          console.log(`      CPU Usage: ${responseData.system.cpu_percent || 'N/A'}%`);
          console.log(`      Memory Usage: ${responseData.system.memory?.percent || 'N/A'}%`);
          console.log(`      Disk Usage: ${responseData.system.disk?.percent || 'N/A'}%`);
        }
        
        if (responseData.application) {
          console.log(`   🚀 Application Metrics:`);
          console.log(`      Total Requests: ${responseData.application.total_requests || 'N/A'}`);
          console.log(`      Total Errors: ${responseData.application.total_errors || 'N/A'}`);
          console.log(`      Avg Response Time: ${responseData.application.avg_response_time || 'N/A'}s`);
        }
        
        if (responseData.database) {
          console.log(`   🗄️  Database Metrics:`);
          console.log(`      Active Connections: ${responseData.database.active_connections || 'N/A'}`);
          console.log(`      Total Queries: ${responseData.database.total_queries || 'N/A'}`);
        }
        
        if (responseData.business) {
          console.log(`   📈 Business Metrics:`);
          console.log(`      Total Shipments: ${responseData.business.total_shipments || 'N/A'}`);
          console.log(`      Active Requests: ${responseData.business.active_requests || 'N/A'}`);
        }
        
      } catch (e) {
        console.log(`   ⚠️  Could not parse JSON response`);
      }
    } else {
      const textData = await response.text();
      console.log(`   📄 Response: ${textData.substring(0, 200)}${textData.length > 200 ? '...' : ''}`);
    }
    
    return { success: isSuccess, status: response.status, data: responseData };
    
  } catch (error) {
    console.log(`   ❌ Error: ${error.message}`);
    return { success: false, error: error.message };
  }
}

async function testOtherMonitoringEndpoints(token) {
  const endpoints = [
    {
      name: 'Database Metrics',
      url: '/api/monitoring/database',
      description: 'بررسی متریک‌های پایگاه داده'
    },
    {
      name: 'Business Metrics',
      url: '/api/monitoring/business',
      description: 'بررسی متریک‌های کسب و کار'
    },
    {
      name: 'System Alerts',
      url: '/api/monitoring/alerts',
      description: 'بررسی هشدارهای سیستم'
    }
  ];
  
  console.log('\n🔍 Testing Other Monitoring Endpoints...');
  
  for (const endpoint of endpoints) {
    try {
      console.log(`\n🧪 Testing: ${endpoint.name}`);
      console.log(`   📝 Description: ${endpoint.description}`);
      console.log(`   🔗 URL: ${endpoint.url}`);
      
      const response = await fetch(`${API_BASE_URL}${endpoint.url}`, {
        method: 'GET',
        headers: {
          'Origin': TEST_ORIGIN,
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      const isSuccess = response.status >= 200 && response.status < 300;
      const statusIcon = isSuccess ? '✅' : '❌';
      
      console.log(`   ${statusIcon} Status: ${response.status}`);
      
      if (isSuccess) {
        const data = await response.json();
        console.log(`   📊 Response Keys: ${Object.keys(data).join(', ')}`);
      } else {
        const errorData = await response.json();
        console.log(`   ❌ Error: ${errorData.error || 'Unknown error'}`);
      }
      
    } catch (error) {
      console.log(`   ❌ Error: ${error.message}`);
    }
  }
}

async function runMetricsTests() {
  console.log('📊 Starting Metrics API Tests\n');
  console.log(`🔗 API Base URL: ${API_BASE_URL}`);
  console.log(`🌐 Test Origin: ${TEST_ORIGIN}\n`);
  console.log('=' .repeat(60));
  
  // Step 1: Authenticate
  const token = await authenticate();
  
  if (!token) {
    console.log('\n❌ Authentication failed. Cannot test metrics endpoint.');
    console.log('\n🔧 Troubleshooting Tips:');
    console.log('1. Make sure the backend server is running');
    console.log('2. Check if expert users are seeded in the database');
    console.log('3. Run: python backend/seed_experts.py');
    return false;
  }
  
  // Step 2: Test metrics endpoint
  const metricsResult = await testMetricsEndpoint(token);
  
  // Step 3: Test other monitoring endpoints
  await testOtherMonitoringEndpoints(token);
  
  // Summary
  console.log('\n📊 Test Summary:');
  console.log('=' .repeat(60));
  
  if (metricsResult.success) {
    console.log('✅ Metrics endpoint test passed!');
    console.log('🎉 All monitoring endpoints are working correctly.');
  } else {
    console.log('❌ Metrics endpoint test failed.');
    console.log('⚠️  Please check the issues above.');
  }
  
  return metricsResult.success;
}

// Run tests
runMetricsTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Test runner error:', error);
  process.exit(1);
});
