#!/usr/bin/env node

/**
 * Simple Location Management API Testing Script
 * Tests the three main location endpoints
 */

import fetch from 'node-fetch';

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const TEST_ORIGIN = 'http://localhost:8109';

async function testEndpoint(name, url, expectedStatus = 200) {
  try {
    console.log(`Testing: ${name}`);
    console.log(`URL: ${url}`);
    
    const response = await fetch(`${API_BASE_URL}${url}`, {
      headers: {
        'Origin': TEST_ORIGIN,
        'Content-Type': 'application/json'
      }
    });

    const isSuccess = response.status === expectedStatus;
    const statusIcon = isSuccess ? '✅' : '❌';
    
    console.log(`${statusIcon} Status: ${response.status} (expected: ${expectedStatus})`);
    
    if (response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.json();
      if (Array.isArray(data)) {
        console.log(`📊 Found ${data.length} items`);
        if (data.length > 0) {
          console.log(`🔍 Sample: ${JSON.stringify(data[0])}`);
        }
      } else {
        console.log(`📄 Response: ${JSON.stringify(data)}`);
      }
    }
    
    console.log('');
    return isSuccess;
    
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
    console.log('');
    return false;
  }
}

async function runTests() {
  console.log('🚀 Location Management API Tests');
  console.log('=================================\n');
  
  const results = [];
  
  // Test provinces
  results.push(await testEndpoint('Provinces List', '/api/provinces'));
  results.push(await testEndpoint('Provinces Direct Route', '/provinces'));
  
  // Test counties
  results.push(await testEndpoint('Counties by Province (Valid)', '/api/counties?province_id=64'));
  results.push(await testEndpoint('Counties by Province (Invalid)', '/api/counties?province_id=99999'));
  results.push(await testEndpoint('Counties Missing ID', '/api/counties', 400));
  
  // Test cities
  results.push(await testEndpoint('Cities by County (Valid)', '/api/cities?county_id=24'));
  results.push(await testEndpoint('Cities by County (Invalid)', '/api/cities?county_id=99999'));
  results.push(await testEndpoint('Cities Missing ID', '/api/cities', 400));
  
  // Summary
  const passed = results.filter(r => r).length;
  const total = results.length;
  
  console.log('📊 Test Summary:');
  console.log(`🎯 Results: ${passed}/${total} tests passed`);
  
  if (passed === total) {
    console.log('🎉 All location management tests passed!');
  } else {
    console.log('⚠️  Some tests failed.');
  }
  
  return passed === total;
}

// Run tests
runTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Test runner error:', error);
  process.exit(1);
});
