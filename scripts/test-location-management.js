#!/usr/bin/env node

/**
 * Location Management API Testing Script
 * Tests all location management endpoints:
 * - GET /api/provinces
 * - GET /api/counties?province_id={id}
 * - GET /api/cities?county_id={id}
 */

import fetch from 'node-fetch';

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const TEST_ORIGIN = 'http://localhost:8109';

// Test configuration for location management
const locationTests = [
  {
    name: 'Provinces List - API Route',
    url: '/api/provinces',
    method: 'GET',
    expectedStatus: 200,
    description: 'Test the main API route for provinces'
  },
  {
    name: 'Provinces List - Direct Route',
    url: '/provinces',
    method: 'GET',
    expectedStatus: 200,
    description: 'Test the direct route for provinces (frontend compatibility)'
  },
  {
    name: 'Counties by Province - Valid ID',
    url: '/api/counties?province_id=1',
    method: 'GET',
    expectedStatus: 200,
    description: 'Test counties endpoint with valid province ID'
  },
  {
    name: 'Counties by Province - Invalid ID',
    url: '/api/counties?province_id=99999',
    method: 'GET',
    expectedStatus: 200,
    description: 'Test counties endpoint with non-existent province ID (should return empty array)'
  },
  {
    name: 'Counties by Province - Missing ID',
    url: '/api/counties',
    method: 'GET',
    expectedStatus: 400,
    description: 'Test counties endpoint without province_id parameter'
  },
  {
    name: 'Cities by County - Valid ID',
    url: '/api/cities?county_id=1',
    method: 'GET',
    expectedStatus: 200,
    description: 'Test cities endpoint with valid county ID'
  },
  {
    name: 'Cities by County - Invalid ID',
    url: '/api/cities?county_id=99999',
    method: 'GET',
    expectedStatus: 200,
    description: 'Test cities endpoint with non-existent county ID (should return empty array)'
  },
  {
    name: 'Cities by County - Missing ID',
    url: '/api/cities',
    method: 'GET',
    expectedStatus: 400,
    description: 'Test cities endpoint without county_id parameter'
  }
];

async function testLocationEndpoint(test) {
  try {
    console.log(`🧪 Testing: ${test.name}`);
    console.log(`   📝 Description: ${test.description}`);
    console.log(`   🔗 URL: ${test.url}`);
    
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
    
    // Parse and display response data
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      console.log(`   📊 Response Data:`);
      
      if (Array.isArray(data)) {
        console.log(`      📋 Array with ${data.length} items`);
        if (data.length > 0) {
          console.log(`      🔍 First item:`, JSON.stringify(data[0], null, 2));
          if (data.length > 1) {
            console.log(`      🔍 Last item:`, JSON.stringify(data[data.length - 1], null, 2));
          }
        }
      } else {
        console.log(`      📄 Object:`, JSON.stringify(data, null, 2));
      }
    } else {
      const text = await response.text();
      console.log(`   📄 Response: ${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
    }
    
    console.log('');
    return isSuccess;
    
  } catch (error) {
    console.log(`   ❌ Error: ${error.message}`);
    console.log('');
    return false;
  }
}

async function testLocationHierarchy() {
  console.log('🔗 Testing Location Hierarchy Flow\n');
  
  try {
    // Step 1: Get provinces
    console.log('📍 Step 1: Getting provinces...');
    const provincesResponse = await fetch(`${API_BASE_URL}/api/provinces`, {
      headers: { 'Origin': TEST_ORIGIN }
    });
    
    if (provincesResponse.status !== 200) {
      console.log('❌ Failed to get provinces');
      return false;
    }
    
    const provinces = await provincesResponse.json();
    console.log(`✅ Found ${provinces.length} provinces`);
    
    if (provinces.length === 0) {
      console.log('⚠️  No provinces found, cannot test hierarchy');
      return false;
    }
    
    // Step 2: Get counties for first province
    const firstProvince = provinces[0];
    console.log(`\n📍 Step 2: Getting counties for province "${firstProvince.name}" (ID: ${firstProvince.id})...`);
    
    const countiesResponse = await fetch(`${API_BASE_URL}/api/counties?province_id=${firstProvince.id}`, {
      headers: { 'Origin': TEST_ORIGIN }
    });
    
    if (countiesResponse.status !== 200) {
      console.log('❌ Failed to get counties');
      return false;
    }
    
    const counties = await countiesResponse.json();
    console.log(`✅ Found ${counties.length} counties`);
    
    if (counties.length === 0) {
      console.log('⚠️  No counties found for this province, cannot test cities');
      return true; // This is still a valid result
    }
    
    // Step 3: Get cities for first county
    const firstCounty = counties[0];
    console.log(`\n📍 Step 3: Getting cities for county "${firstCounty.name}" (ID: ${firstCounty.id})...`);
    
    const citiesResponse = await fetch(`${API_BASE_URL}/api/cities?county_id=${firstCounty.id}`, {
      headers: { 'Origin': TEST_ORIGIN }
    });
    
    if (citiesResponse.status !== 200) {
      console.log('❌ Failed to get cities');
      return false;
    }
    
    const cities = await citiesResponse.json();
    console.log(`✅ Found ${cities.length} cities`);
    
    console.log('\n🎯 Hierarchy Test Summary:');
    console.log(`   Province: ${firstProvince.name} (${provinces.length} total provinces)`);
    console.log(`   County: ${firstCounty.name} (${counties.length} counties in province)`);
    console.log(`   Cities: ${cities.length} cities in county`);
    
    if (cities.length > 0) {
      console.log(`   Sample cities: ${cities.slice(0, 3).map(c => c.name).join(', ')}`);
    }
    
    console.log('\n✅ Location hierarchy test completed successfully!');
    return true;
    
  } catch (error) {
    console.log(`❌ Hierarchy test error: ${error.message}`);
    return false;
  }
}

async function runLocationTests() {
  console.log('🚀 Starting Location Management API Tests\n');
  console.log(`🔗 API Base URL: ${API_BASE_URL}`);
  console.log(`🌐 Test Origin: ${TEST_ORIGIN}\n`);
  
  const results = [];
  
  // Run individual endpoint tests
  for (const test of locationTests) {
    const success = await testLocationEndpoint(test);
    results.push({ ...test, success });
    
    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  
  // Run hierarchy flow test
  console.log('='.repeat(60));
  const hierarchySuccess = await testLocationHierarchy();
  results.push({ 
    name: 'Location Hierarchy Flow', 
    success: hierarchySuccess,
    description: 'Test the complete flow from provinces to counties to cities'
  });
  
  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 Location Management Test Summary:');
  console.log('=====================================');
  
  const passed = results.filter(r => r.success).length;
  const total = results.length;
  
  results.forEach(result => {
    const icon = result.success ? '✅' : '❌';
    console.log(`${icon} ${result.name}`);
  });
  
  console.log(`\n🎯 Results: ${passed}/${total} tests passed`);
  
  if (passed === total) {
    console.log('🎉 All location management tests passed!');
  } else {
    console.log('⚠️  Some location management tests failed. Please check the issues above.');
  }
  
  return passed === total;
}

// Run tests if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runLocationTests().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('❌ Location test runner error:', error);
    process.exit(1);
  });
}

export { runLocationTests, testLocationEndpoint, testLocationHierarchy };
