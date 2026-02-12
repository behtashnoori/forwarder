#!/usr/bin/env node

/**
 * Comprehensive Shipment Request Testing Script
 * Tests domestic and international shipment request processes
 * Includes gamification and public tracking tests
 */

import fetch from 'node-fetch';

const API_BASE_URL = 'http://127.0.0.1:5000';
const TEST_ORIGIN = 'http://localhost:8109';

// Test data
const testData = {
  domestic: {
    shipping_type: "domestic",
    origin_province_id: 63, // Valid province
    origin_county_id: 2,    // Valid county
    origin_city_id: 427,    // Valid city
    dest_province_id: 64,   // Valid province
    dest_county_id: 24,     // Valid county
    dest_city_id: 449,      // Valid city
    contact_phone: "09123456789",
    customer_first_name: "علی",
    customer_last_name: "احمدی",
    domestic_transport_method: "road_transport",
    transport_method_preference: "customer_choice",
    cargo_description: "محصولات الکترونیکی",
    cargo_weight: 25.5,
    cargo_volume: 2.3,
    cargo_value: 5000000,
    special_instructions: "مراقبت ویژه",
    pickup_date: "2024-12-15",
    delivery_date: "2024-12-20"
  },
  international: {
    shipping_type: "international",
    origin_country: "China",
    origin_city_international: "Shanghai",
    origin_address_international: "Shanghai Port, China",
    dest_country: "Iran",
    dest_city_international: "Bandar Abbas",
    dest_address_international: "Bandar Abbas Port, Iran",
    contact_phone: "09123456789",
    customer_first_name: "محمد",
    customer_last_name: "رضایی",
    international_transport_method: "sea_freight",
    transport_method_preference: "forwarder_suggestion",
    cargo_description: "ماشین آلات صنعتی",
    cargo_weight: 1500.0,
    cargo_volume: 15.8,
    cargo_value: 50000000,
    special_instructions: "نیاز به گمرک",
    pickup_date: "2024-12-10",
    delivery_date: "2024-12-25"
  },
  gamificationCustomer: {
    email: "test.customer@example.com",
    phone: "09123456789",
    first_name: "تست",
    last_name: "مشتری"
  }
};

let createdRequestIds = [];
let gamificationCustomerId = null;

async function makeRequest(url, method = 'GET', data = null, headers = {}) {
  const options = {
    method,
    headers: {
      'Origin': TEST_ORIGIN,
      'Content-Type': 'application/json',
      ...headers
    }
  };
  
  if (data) {
    options.body = JSON.stringify(data);
  }
  
  const response = await fetch(`${API_BASE_URL}${url}`, options);
  const responseData = await response.json().catch(() => ({}));
  
  return {
    status: response.status,
    data: responseData,
    headers: response.headers
  };
}

async function testTransportMethods() {
  console.log('🚛 Testing Transport Methods API...');
  
  const result = await makeRequest('/api/transport-methods');
  
  if (result.status === 200) {
    console.log('✅ Transport methods retrieved successfully');
    console.log(`   International methods: ${result.data.international_methods?.length || 0}`);
    console.log(`   Domestic methods: ${result.data.domestic_methods?.length || 0}`);
    console.log(`   Preference options: ${result.data.preference_options?.length || 0}`);
    return true;
  } else {
    console.log(`❌ Failed to get transport methods: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return false;
  }
}

async function testDomesticShipmentRequest() {
  console.log('\n🏠 Testing Domestic Shipment Request...');
  
  const result = await makeRequest('/api/shipment-request', 'POST', testData.domestic);
  
  if (result.status === 201) {
    console.log('✅ Domestic shipment request created successfully');
    console.log(`   Request ID: ${result.data.id}`);
    console.log(`   Message: ${result.data.message}`);
    createdRequestIds.push(result.data.id);
    return result.data.id;
  } else {
    console.log(`❌ Failed to create domestic shipment request: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return null;
  }
}

async function testInternationalShipmentRequest() {
  console.log('\n🌍 Testing International Shipment Request...');
  
  const result = await makeRequest('/api/shipment-request', 'POST', testData.international);
  
  if (result.status === 201) {
    console.log('✅ International shipment request created successfully');
    console.log(`   Request ID: ${result.data.id}`);
    console.log(`   Message: ${result.data.message}`);
    createdRequestIds.push(result.data.id);
    return result.data.id;
  } else {
    console.log(`❌ Failed to create international shipment request: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return null;
  }
}

async function testDataValidation() {
  console.log('\n🔍 Testing Data Validation...');
  
  const validationTests = [
    {
      name: 'Invalid shipping type',
      data: { ...testData.domestic, shipping_type: 'invalid' },
      expectedStatus: 400
    },
    {
      name: 'Missing domestic location data',
      data: { ...testData.domestic, origin_province_id: null },
      expectedStatus: 400
    },
    {
      name: 'Missing international location data',
      data: { ...testData.international, origin_country: '' },
      expectedStatus: 400
    },
    {
      name: 'Invalid phone number',
      data: { ...testData.domestic, contact_phone: '123456789' },
      expectedStatus: 400
    },
    {
      name: 'Invalid transport method preference',
      data: { ...testData.domestic, transport_method_preference: 'invalid' },
      expectedStatus: 201 // Should default to customer_choice
    }
  ];
  
  let passedTests = 0;
  
  for (const test of validationTests) {
    const result = await makeRequest('/api/shipment-request', 'POST', test.data);
    
    if (result.status === test.expectedStatus) {
      console.log(`✅ ${test.name}: ${result.status} (expected ${test.expectedStatus})`);
      passedTests++;
    } else {
      console.log(`❌ ${test.name}: ${result.status} (expected ${test.expectedStatus})`);
      console.log(`   Response: ${JSON.stringify(result.data)}`);
    }
  }
  
  console.log(`   Validation tests: ${passedTests}/${validationTests.length} passed`);
  return passedTests === validationTests.length;
}

async function createGamificationCustomer() {
  console.log('\n🎮 Creating Gamification Customer...');
  
  // Try to register gamification customer
  const result = await makeRequest('/api/customer/register', 'POST', testData.gamificationCustomer);
  
  if (result.status === 201 || result.status === 200) {
    console.log('✅ Gamification customer ready');
    console.log(`   Customer ID: ${result.data.customer_id}`);
    console.log(`   Message: ${result.data.message}`);
    gamificationCustomerId = result.data.customer_id;
    return result.data.customer_id;
  } else {
    console.log(`❌ Failed to create gamification customer: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return null;
  }
}

async function testGamificationWithShipment() {
  console.log('\n🎯 Testing Gamification with Shipment Request...');
  
  if (!gamificationCustomerId) {
    console.log('❌ No gamification customer available for testing');
    return false;
  }
  
  const gamificationData = {
    ...testData.domestic,
    gamification_customer_id: gamificationCustomerId
  };
  
  const result = await makeRequest('/api/shipment-request', 'POST', gamificationData);
  
  if (result.status === 201) {
    console.log('✅ Gamification shipment request created successfully');
    console.log(`   Request ID: ${result.data.id}`);
    createdRequestIds.push(result.data.id);
    
    // Check if gamification data was updated
    const customerResult = await makeRequest(`/api/crm/customers/${gamificationCustomerId}`, 'GET');
    if (customerResult.status === 200) {
      console.log(`   Customer total requests: ${customerResult.data.total_requests}`);
      console.log(`   Customer loyalty points: ${customerResult.data.loyalty_points}`);
      console.log(`   Customer level: ${customerResult.data.customer_level}`);
    }
    
    return result.data.id;
  } else {
    console.log(`❌ Failed to create gamification shipment request: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return null;
  }
}

async function testPublicTracking(requestId) {
  console.log(`\n🔍 Testing Public Tracking for Request ${requestId}...`);
  
  if (!requestId) {
    console.log('❌ No request ID available for tracking test');
    return false;
  }
  
  const result = await makeRequest(`/api/public/track/${requestId}`);
  
  if (result.status === 200) {
    console.log('✅ Public tracking information retrieved successfully');
    console.log(`   Tracking Number: ${result.data.tracking_number}`);
    console.log(`   Status: ${result.data.status}`);
    console.log(`   Shipping Type: ${result.data.shipping_type}`);
    console.log(`   Contact Phone: ${result.data.contact_phone}`);
    
    if (result.data.route) {
      console.log('   Route Information:');
      if (result.data.route.origin) {
        console.log(`     Origin: ${result.data.route.origin.province || result.data.route.origin.country}`);
      }
      if (result.data.route.destination) {
        console.log(`     Destination: ${result.data.route.destination.province || result.data.route.destination.country}`);
      }
    }
    
    if (result.data.assigned_expert) {
      console.log(`   Assigned Expert: ${result.data.assigned_expert.full_name}`);
    }
    
    return true;
  } else {
    console.log(`❌ Failed to get public tracking info: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return false;
  }
}

async function testPublicTrackingLimitations() {
  console.log('\n🚫 Testing Public Tracking Limitations...');
  
  const limitationTests = [
    {
      name: 'Non-existent request ID',
      requestId: 999999,
      expectedStatus: 404
    },
    {
      name: 'Invalid request ID format',
      requestId: 'invalid',
      expectedStatus: 404
    }
  ];
  
  let passedTests = 0;
  
  for (const test of limitationTests) {
    const result = await makeRequest(`/api/public/track/${test.requestId}`);
    
    if (result.status === test.expectedStatus) {
      console.log(`✅ ${test.name}: ${result.status} (expected ${test.expectedStatus})`);
      passedTests++;
    } else {
      console.log(`❌ ${test.name}: ${result.status} (expected ${test.expectedStatus})`);
      console.log(`   Response: ${JSON.stringify(result.data)}`);
    }
  }
  
  console.log(`   Limitation tests: ${passedTests}/${limitationTests.length} passed`);
  return passedTests === limitationTests.length;
}

async function testIranPortsIntegration() {
  console.log('\n⚓ Testing Iran Ports Integration...');
  
  // Test with Bandar Abbas (major Iranian port)
  const iranPortData = {
    ...testData.international,
    dest_city_international: "Bandar Abbas",
    dest_address_international: "Bandar Abbas Port, Iran",
    international_transport_method: "sea_freight"
  };
  
  const result = await makeRequest('/api/shipment-request', 'POST', iranPortData);
  
  if (result.status === 201) {
    console.log('✅ Iran port shipment request created successfully');
    console.log(`   Request ID: ${result.data.id}`);
    console.log(`   Destination: ${iranPortData.dest_city_international}`);
    console.log(`   Transport Method: ${iranPortData.international_transport_method}`);
    createdRequestIds.push(result.data.id);
    return result.data.id;
  } else {
    console.log(`❌ Failed to create Iran port shipment request: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return null;
  }
}

async function runAllTests() {
  console.log('🚀 Starting Comprehensive Shipment Request Tests\n');
  console.log(`🔗 API Base URL: ${API_BASE_URL}`);
  console.log(`🌐 Test Origin: ${TEST_ORIGIN}\n`);
  
  const results = [];
  
  // Test 1: Transport Methods
  const transportMethodsResult = await testTransportMethods();
  results.push({ name: 'Transport Methods API', success: transportMethodsResult });
  
  // Test 2: Domestic Shipment Request
  const domesticRequestId = await testDomesticShipmentRequest();
  results.push({ name: 'Domestic Shipment Request', success: !!domesticRequestId });
  
  // Test 3: International Shipment Request
  const internationalRequestId = await testInternationalShipmentRequest();
  results.push({ name: 'International Shipment Request', success: !!internationalRequestId });
  
  // Test 4: Data Validation
  const validationResult = await testDataValidation();
  results.push({ name: 'Data Validation', success: validationResult });
  
  // Test 5: Gamification Customer Creation
  const customerId = await createGamificationCustomer();
  results.push({ name: 'Gamification Customer Creation', success: !!customerId });
  
  // Test 6: Gamification with Shipment
  const gamificationRequestId = await testGamificationWithShipment();
  results.push({ name: 'Gamification with Shipment', success: !!gamificationRequestId });
  
  // Test 7: Public Tracking
  const trackingResult = await testPublicTracking(domesticRequestId);
  results.push({ name: 'Public Tracking', success: trackingResult });
  
  // Test 8: Public Tracking Limitations
  const trackingLimitationsResult = await testPublicTrackingLimitations();
  results.push({ name: 'Public Tracking Limitations', success: trackingLimitationsResult });
  
  // Test 9: Iran Ports Integration
  const iranPortsRequestId = await testIranPortsIntegration();
  results.push({ name: 'Iran Ports Integration', success: !!iranPortsRequestId });
  
  // Summary
  console.log('\n📊 Test Summary:');
  console.log('================');
  
  const passed = results.filter(r => r.success).length;
  const total = results.length;
  
  results.forEach(result => {
    const icon = result.success ? '✅' : '❌';
    console.log(`${icon} ${result.name}`);
  });
  
  console.log(`\n🎯 Results: ${passed}/${total} tests passed`);
  console.log(`📝 Created ${createdRequestIds.length} test requests: ${createdRequestIds.join(', ')}`);
  
  if (passed === total) {
    console.log('🎉 All shipment request tests passed!');
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

export { runAllTests };
