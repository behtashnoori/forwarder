#!/usr/bin/env node

/**
 * Simple API Testing Script (No external dependencies)
 * Tests basic API endpoints using built-in fetch
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const TEST_ORIGIN = 'http://localhost:8109';

// Test configuration
const tests = [
  {
    name: 'Health Check',
    url: '/api/health',
    method: 'GET'
  },
  {
    name: 'Provinces List',
    url: '/api/provinces',
    method: 'GET'
  },
  {
    name: 'Counties by Province',
    url: '/api/counties?province_id=64',
    method: 'GET'
  },
  {
    name: 'Expert Console Ping',
    url: '/api/expert/ping',
    method: 'GET'
  },
  {
    name: 'Shipment Request Ping',
    url: '/api/shipment-request/ping',
    method: 'GET'
  },
  {
    name: 'Shipment Request OPTIONS',
    url: '/api/shipment-request',
    method: 'OPTIONS'
  },
  {
    name: 'Shipment Request POST',
    url: '/api/shipment-request',
    method: 'POST',
    body: JSON.stringify({
      contact_phone: '09123456789',
      origin_province_id: 64,
      origin_county_id: 24,
      origin_city_id: 449,
      dest_province_id: 64,
      dest_county_id: 24,
      dest_city_id: 449,
      transport_method: 'road',
      customer_first_name: 'تست',
      customer_last_name: 'کاربر'
    })
  }
];

async function testEndpoint(test) {
  try {
    console.log(`🧪 Testing: ${test.name}`);
    console.log(`   URL: ${test.url}`);
    
    const requestOptions = {
      method: test.method,
      headers: {
        'Origin': TEST_ORIGIN,
        'Content-Type': 'application/json'
      }
    };
    
    if (test.body) {
      requestOptions.body = test.body;
    }
    
    const response = await fetch(`${API_BASE_URL}${test.url}`, requestOptions);

    const isSuccess = response.status >= 200 && response.status < 300;
    const statusIcon = isSuccess ? '✅' : '❌';
    
    console.log(`   ${statusIcon} Status: ${response.status}`);
    
    // Check CORS headers
    const corsOrigin = response.headers.get('Access-Control-Allow-Origin');
    const corsCredentials = response.headers.get('Access-Control-Allow-Credentials');
    
    console.log(`   🌐 CORS:`);
    console.log(`      ${corsOrigin ? '✅' : '❌'} Allow-Origin: ${corsOrigin || 'Not set'}`);
    console.log(`      ${corsCredentials ? '✅' : '❌'} Allow-Credentials: ${corsCredentials || 'Not set'}`);
    
    if (isSuccess && test.url.includes('/provinces')) {
      const data = await response.json();
      console.log(`   📊 Data: ${data.length} provinces loaded`);
    } else if (isSuccess && test.method === 'POST' && test.url.includes('/shipment-request')) {
      const data = await response.json();
      console.log(`   📊 Response: ${data.message} (ID: ${data.id})`);
    }
    
    console.log('');
    return isSuccess;
    
  } catch (error) {
    console.log(`   ❌ Error: ${error.message}`);
    console.log('');
    return false;
  }
}

async function runAllTests() {
  console.log('🚀 Starting API Tests\n');
  console.log(`🔗 API Base URL: ${API_BASE_URL}`);
  console.log(`🌐 Test Origin: ${TEST_ORIGIN}\n`);
  
  const results = [];
  
  for (const test of tests) {
    const success = await testEndpoint(test);
    results.push({ ...test, success });
    
    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  // Summary
  console.log('📊 Test Summary:');
  console.log('================');
  
  const passed = results.filter(r => r.success).length;
  const total = results.length;
  
  results.forEach(result => {
    const icon = result.success ? '✅' : '❌';
    console.log(`${icon} ${result.name}`);
  });
  
  console.log(`\n🎯 Results: ${passed}/${total} tests passed`);
  
  if (passed === total) {
    console.log('🎉 All tests passed! API is working correctly.');
    console.log('🌐 CORS is properly configured for development.');
  } else {
    console.log('⚠️  Some tests failed. Please check the issues above.');
  }
  
  return passed === total;
}

// Run tests
runAllTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Test runner error:', error);
  process.exit(1);
});
