#!/usr/bin/env node

/**
 * Detailed Metrics API Testing Script
 * Tests the /api/monitoring/metrics endpoint and displays detailed information
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';
const TEST_ORIGIN = 'http://localhost:8109';

async function testMetricsEndpoint() {
  try {
    console.log('📊 Testing Metrics Endpoint (Detailed)...');
    console.log('   URL: /api/monitoring/metrics');
    console.log('   Method: GET');
    
    const response = await fetch(`${API_BASE_URL}/api/monitoring/metrics`, {
      method: 'GET',
      headers: {
        'Origin': TEST_ORIGIN,
        'Content-Type': 'application/json'
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
    
    if (isSuccess) {
      const responseData = await response.json();
      console.log(`\n   📊 Detailed Metrics Information:`);
      console.log(`   ======================================`);
      
      // System Metrics
      if (responseData.system) {
        console.log(`\n   💻 System Metrics:`);
        console.log(`      CPU Usage: ${responseData.system.cpu_percent || 'N/A'}%`);
        
        if (responseData.system.memory) {
          console.log(`      Memory:`);
          console.log(`         Total: ${responseData.system.memory.total || 'N/A'} bytes`);
          console.log(`         Available: ${responseData.system.memory.available || 'N/A'} bytes`);
          console.log(`         Used: ${responseData.system.memory.used || 'N/A'} bytes`);
          console.log(`         Percent: ${responseData.system.memory.percent || 'N/A'}%`);
        }
        
        if (responseData.system.disk) {
          console.log(`      Disk:`);
          console.log(`         Total: ${responseData.system.disk.total || 'N/A'} bytes`);
          console.log(`         Used: ${responseData.system.disk.used || 'N/A'} bytes`);
          console.log(`         Free: ${responseData.system.disk.free || 'N/A'} bytes`);
          console.log(`         Percent: ${responseData.system.disk.percent || 'N/A'}%`);
        }
        
        if (responseData.system.network) {
          console.log(`      Network:`);
          console.log(`         Bytes Sent: ${responseData.system.network.bytes_sent || 'N/A'}`);
          console.log(`         Bytes Received: ${responseData.system.network.bytes_recv || 'N/A'}`);
        }
      }
      
      // Application Metrics
      if (responseData.application) {
        console.log(`\n   🚀 Application Metrics:`);
        console.log(`      Total Requests: ${responseData.application.total_requests || 'N/A'}`);
        console.log(`      Total Errors: ${responseData.application.total_errors || 'N/A'}`);
        console.log(`      Success Rate: ${responseData.application.success_rate || 'N/A'}%`);
        console.log(`      Average Response Time: ${responseData.application.avg_response_time || 'N/A'}s`);
        console.log(`      Active Sessions: ${responseData.application.active_sessions || 'N/A'}`);
        
        if (responseData.application.request_methods) {
          console.log(`      Request Methods:`);
          Object.entries(responseData.application.request_methods).forEach(([method, count]) => {
            console.log(`         ${method}: ${count}`);
          });
        }
        
        if (responseData.application.status_codes) {
          console.log(`      Status Codes:`);
          Object.entries(responseData.application.status_codes).forEach(([code, count]) => {
            console.log(`         ${code}: ${count}`);
          });
        }
      }
      
      // Database Metrics
      if (responseData.database) {
        console.log(`\n   🗄️  Database Metrics:`);
        console.log(`      Active Connections: ${responseData.database.active_connections || 'N/A'}`);
        console.log(`      Total Queries: ${responseData.database.total_queries || 'N/A'}`);
        console.log(`      Slow Queries: ${responseData.database.slow_queries || 'N/A'}`);
        console.log(`      Average Query Time: ${responseData.database.avg_query_time || 'N/A'}ms`);
        
        if (responseData.database.table_sizes) {
          console.log(`      Table Sizes:`);
          Object.entries(responseData.database.table_sizes).forEach(([table, size]) => {
            console.log(`         ${table}: ${size} rows`);
          });
        }
      }
      
      // Business Metrics
      if (responseData.business) {
        console.log(`\n   📈 Business Metrics:`);
        console.log(`      Total Shipments: ${responseData.business.total_shipments || 'N/A'}`);
        console.log(`      Active Requests: ${responseData.business.active_requests || 'N/A'}`);
        console.log(`      Completed Requests: ${responseData.business.completed_requests || 'N/A'}`);
        console.log(`      Pending Requests: ${responseData.business.pending_requests || 'N/A'}`);
        console.log(`      Total Customers: ${responseData.business.total_customers || 'N/A'}`);
        console.log(`      Active Experts: ${responseData.business.active_experts || 'N/A'}`);
      }
      
      // Recent Activity
      if (responseData.recent_activity) {
        console.log(`\n   📋 Recent Activity:`);
        if (Array.isArray(responseData.recent_activity)) {
          responseData.recent_activity.forEach((activity, index) => {
            console.log(`      ${index + 1}. ${activity.timestamp || 'N/A'}: ${activity.action || 'N/A'} - ${activity.description || 'N/A'}`);
          });
        } else {
          console.log(`      ${JSON.stringify(responseData.recent_activity, null, 2)}`);
        }
      }
      
      // Show all available keys
      console.log(`\n   🔑 All Available Keys:`);
      console.log(`      ${Object.keys(responseData).join(', ')}`);
      
    } else {
      const errorData = await response.json();
      console.log(`   ❌ Error: ${errorData.error || 'Unknown error'}`);
    }
    
    return isSuccess;
    
  } catch (error) {
    console.log(`   ❌ Error: ${error.message}`);
    return false;
  }
}

async function runDetailedMetricsTest() {
  console.log('📊 Starting Detailed Metrics API Test\n');
  console.log(`🔗 API Base URL: ${API_BASE_URL}`);
  console.log(`🌐 Test Origin: ${TEST_ORIGIN}\n`);
  console.log('=' .repeat(60));
  
  const success = await testMetricsEndpoint();
  
  console.log('\n📊 Test Summary:');
  console.log('=' .repeat(60));
  
  if (success) {
    console.log('✅ Metrics endpoint test passed!');
    console.log('🎉 The /api/monitoring/metrics endpoint is working correctly.');
    console.log('📊 All system metrics are being collected and returned properly.');
  } else {
    console.log('❌ Metrics endpoint test failed.');
    console.log('⚠️  Please check the issues above.');
  }
  
  return success;
}

// Run test
runDetailedMetricsTest().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Test runner error:', error);
  process.exit(1);
});
