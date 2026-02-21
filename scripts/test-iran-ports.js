#!/usr/bin/env node

/**
 * Iran Ports Integration Testing Script
 * Tests international shipment requests with Iranian ports
 */

import fetch from 'node-fetch';

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const TEST_ORIGIN = 'http://localhost:8109';

// Iranian ports test data
const iranPortsData = [
  {
    name: "Bandar Abbas",
    type: "sea_port",
    description: "Major Iranian port on Persian Gulf"
  },
  {
    name: "Bandar Imam Khomeini",
    type: "sea_port", 
    description: "Major Iranian port on Persian Gulf"
  },
  {
    name: "Bandar Anzali",
    type: "sea_port",
    description: "Caspian Sea port"
  },
  {
    name: "Tehran Imam Khomeini Airport",
    type: "airport",
    description: "Major international airport"
  },
  {
    name: "Mashhad Airport",
    type: "airport", 
    description: "International airport in northeast Iran"
  }
];

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

async function testIranPortShipment(portName, portType) {
  console.log(`\n⚓ Testing ${portType} shipment to ${portName}...`);
  
  const shipmentData = {
    shipping_type: "international",
    origin_country: "China",
    origin_city_international: "Shanghai",
    origin_address_international: "Shanghai Port, China",
    dest_country: "Iran",
    dest_city_international: portName,
    dest_address_international: `${portName}, Iran`,
    contact_phone: "09123456789",
    customer_first_name: "تست",
    customer_last_name: "بندر",
    international_transport_method: portType === "sea_port" ? "sea_freight" : "air_freight",
    transport_method_preference: "forwarder_suggestion",
    cargo_description: portType === "sea_port" ? "کالاهای دریایی" : "کالاهای هوایی",
    cargo_weight: portType === "sea_port" ? 2000.0 : 500.0,
    cargo_volume: portType === "sea_port" ? 20.0 : 5.0,
    cargo_value: 75000000,
    special_instructions: `ارسال به ${portName}`,
    pickup_date: "2024-12-10",
    delivery_date: "2024-12-25"
  };
  
  const result = await makeRequest('/api/shipment-request', 'POST', shipmentData);
  
  if (result.status === 201) {
    console.log(`✅ ${portName} shipment request created successfully`);
    console.log(`   Request ID: ${result.data.id}`);
    console.log(`   Transport Method: ${shipmentData.international_transport_method}`);
    console.log(`   Cargo Weight: ${shipmentData.cargo_weight} kg`);
    console.log(`   Cargo Value: ${shipmentData.cargo_value} Rials`);
    return result.data.id;
  } else {
    console.log(`❌ Failed to create ${portName} shipment request: ${result.status}`);
    console.log(`   Response: ${JSON.stringify(result.data)}`);
    return null;
  }
}

async function testPortValidation() {
  console.log('\n🔍 Testing Port Validation...');
  
  const validationTests = [
    {
      name: 'Invalid Iranian port name',
      data: {
        shipping_type: "international",
        origin_country: "China",
        origin_city_international: "Shanghai",
        dest_country: "Iran",
        dest_city_international: "NonExistentPort",
        contact_phone: "09123456789",
        international_transport_method: "sea_freight"
      },
      shouldPass: true // API should accept any port name
    },
    {
      name: 'Missing port information',
      data: {
        shipping_type: "international",
        origin_country: "China",
        origin_city_international: "Shanghai",
        dest_country: "Iran",
        dest_city_international: "",
        contact_phone: "09123456789"
      },
      shouldPass: false
    },
    {
      name: 'Mismatched transport method and port type',
      data: {
        shipping_type: "international",
        origin_country: "China",
        origin_city_international: "Shanghai",
        dest_country: "Iran",
        dest_city_international: "Bandar Abbas",
        contact_phone: "09123456789",
        international_transport_method: "air_freight" // Using air for sea port
      },
      shouldPass: true // API should accept any combination
    }
  ];
  
  let passedTests = 0;
  
  for (const test of validationTests) {
    const result = await makeRequest('/api/shipment-request', 'POST', test.data);
    
    const success = test.shouldPass ? result.status === 201 : result.status === 400;
    
    if (success) {
      console.log(`✅ ${test.name}: ${result.status} (expected ${test.shouldPass ? 'success' : 'validation error'})`);
      passedTests++;
    } else {
      console.log(`❌ ${test.name}: ${result.status} (expected ${test.shouldPass ? 'success' : 'validation error'})`);
      console.log(`   Response: ${JSON.stringify(result.data)}`);
    }
  }
  
  console.log(`   Port validation tests: ${passedTests}/${validationTests.length} passed`);
  return passedTests === validationTests.length;
}

async function testPublicTrackingForPorts(requestIds) {
  console.log('\n🔍 Testing Public Tracking for Port Shipments...');
  
  let passedTests = 0;
  
  for (const requestId of requestIds) {
    if (!requestId) continue;
    
    const result = await makeRequest(`/api/public/track/${requestId}`);
    
    if (result.status === 200) {
      console.log(`✅ Tracking for request ${requestId}:`);
      console.log(`   Destination: ${result.data.route?.destination?.city_international || 'N/A'}`);
      console.log(`   Country: ${result.data.route?.destination?.country || 'N/A'}`);
      console.log(`   Status: ${result.data.status}`);
      passedTests++;
    } else {
      console.log(`❌ Failed to track request ${requestId}: ${result.status}`);
    }
  }
  
  console.log(`   Port tracking tests: ${passedTests}/${requestIds.filter(id => id).length} passed`);
  return passedTests === requestIds.filter(id => id).length;
}

async function runIranPortsTests() {
  console.log('🚀 Starting Iran Ports Integration Tests\n');
  console.log(`🔗 API Base URL: ${API_BASE_URL}`);
  console.log(`🌐 Test Origin: ${TEST_ORIGIN}\n`);
  
  const results = [];
  const createdRequestIds = [];
  
  // Test each Iranian port
  for (const port of iranPortsData) {
    const requestId = await testIranPortShipment(port.name, port.type);
    createdRequestIds.push(requestId);
    results.push({ 
      name: `${port.name} (${port.type})`, 
      success: !!requestId 
    });
  }
  
  // Test port validation
  const validationResult = await testPortValidation();
  results.push({ name: 'Port Validation', success: validationResult });
  
  // Test public tracking for port shipments
  const trackingResult = await testPublicTrackingForPorts(createdRequestIds);
  results.push({ name: 'Port Tracking', success: trackingResult });
  
  // Summary
  console.log('\n📊 Iran Ports Test Summary:');
  console.log('===========================');
  
  const passed = results.filter(r => r.success).length;
  const total = results.length;
  
  results.forEach(result => {
    const icon = result.success ? '✅' : '❌';
    console.log(`${icon} ${result.name}`);
  });
  
  console.log(`\n🎯 Results: ${passed}/${total} tests passed`);
  console.log(`📝 Created ${createdRequestIds.filter(id => id).length} port shipment requests`);
  
  if (passed === total) {
    console.log('🎉 All Iran ports tests passed!');
  } else {
    console.log('⚠️  Some tests failed. Please check the issues above.');
  }
  
  return passed === total;
}

// Run tests if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runIranPortsTests().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('❌ Test runner error:', error);
    process.exit(1);
  });
}

export { runIranPortsTests };
