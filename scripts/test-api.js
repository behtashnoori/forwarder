#!/usr/bin/env node

/**
 * Comprehensive API Testing Script
 * Tests all API endpoints to ensure they work correctly
 */

import fetch from 'node-fetch';

const API_BASE_URL = 'http://127.0.0.1:5000';
const TEST_ORIGIN = 'http://localhost:8109';

// Test configuration
const tests = [
  {
    name: 'Health Check',
    url: '/api/health',
    method: 'GET',
    expectedStatus: 200
  },
  {
    name: 'Provinces List',
    url: '/api/provinces',
    method: 'GET',
    expectedStatus: 200
  },
  {
    name: 'Counties by Province',
    url: '/api/counties?province_id=64',
    method: 'GET',
    expectedStatus: 200
  },
  {
    name: 'Cities by County',
    url: '/api/cities?county_id=24',
    method: 'GET',
    expectedStatus: 200
  },
  {
    name: 'Expert Console Ping',
    url: '/api/expert/ping',
    method: 'GET',
    expectedStatus: 200
  },
  {
    name: 'Shipment Request Ping',
    url: '/api/shipment-request/ping',
    method: 'GET',
    expectedStatus: 200
  },
  {
    name: 'CRM Ping',
    url: '/api/crm/ping',
    method: 'GET',
    expectedStatus: 200
  },
  {
    name: 'Monitoring Health',
    url: '/api/monitoring/health',
    method: 'GET',
    expectedStatus: 200
  }
];

async function testEndpoint(test) {
  try {
    console.log(`🧪 Testing: ${test.name}`);
    console.log(`   URL: ${test.url}`);
    
    const response = await fetch(`${API_BASE_URL}${test.url}`, {
      method: test.method,
      headers: {
        'Origin': TEST_ORIGIN,
        'Content-Type': 'application/json'
      }
    });

    const isSuccess = response.status === test.expectedStatus;
    const statusIcon = isSuccess ? '✅' : '❌';
    
    console.log(`   ${statusIcon} Status: ${response.status} (expected: ${test.expectedStatus})`);
    
    // Check CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
      'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
      'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
    };
    
    console.log(`   🌐 CORS Headers:`);
    Object.entries(corsHeaders).forEach(([key, value]) => {
      const corsIcon = value ? '✅' : '❌';
      console.log(`      ${corsIcon} ${key}: ${value || 'Not set'}`);
    });
    
    if (!isSuccess) {
      const text = await response.text();
      console.log(`   📄 Response: ${text.substring(0, 200)}...`);
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
  console.log('🚀 Starting Comprehensive API Tests\n');
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
  } else {
    console.log('⚠️  Some tests failed. Please check the issues above.');
  }
  
  return passed === total;
}

// Run tests if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllTests().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('❌ Test runner error:', error);
    process.exit(1);
  });
}

export { runAllTests, testEndpoint };










