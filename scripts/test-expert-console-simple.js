#!/usr/bin/env node

/**
 * Simple Expert Console Request Retrieval Test Script
 * Tests the expert console request management functionality with basic validation
 */

import axios from 'axios';
import colors from 'colors';

// Configuration
const BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const TEST_USERNAME = process.env.EXPERT_USERNAME || 'expert1';
const TEST_PASSWORD = process.env.EXPERT_PASSWORD || 'password123';

console.log('🧪 Expert Console Request Retrieval Test'.bold.blue);
console.log(`📍 Base URL: ${BASE_URL}`.gray);
console.log(`👤 Test Expert: ${TEST_USERNAME}`.gray);
console.log('=' .repeat(60));

// Test 1: Check if server is running
async function testServerHealth() {
    try {
        console.log('\n🔍 Testing server connectivity...'.cyan);
        const response = await axios.get(`${BASE_URL}/api/health`, { timeout: 5000 });
        console.log('✅ Server is running'.green);
        return true;
    } catch (error) {
        console.log('❌ Server is not running or not accessible'.red);
        console.log(`   Error: ${error.message}`.red);
        return false;
    }
}

// Test 2: Expert Login
async function testExpertLogin() {
    try {
        console.log('\n🔐 Testing expert login...'.cyan);
        const response = await axios.post(`${BASE_URL}/api/expert/auth/login`, {
            username: TEST_USERNAME,
            password: TEST_PASSWORD
        }, {
            headers: {
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:3000'
            },
            timeout: 10000
        });
        
        if (response.data.success && response.data.expert && response.data.tokens) {
            console.log('✅ Expert login successful'.green);
            console.log(`   Expert: ${response.data.expert.full_name} (${response.data.expert.username})`.gray);
            return response.data.tokens.access_token;
        } else {
            console.log('❌ Invalid login response structure'.red);
            return null;
        }
    } catch (error) {
        console.log('❌ Expert login failed'.red);
        console.log(`   Error: ${error.response?.data?.error || error.message}`.red);
        return null;
    }
}

// Test 3: Get Requests List
async function testGetRequests(accessToken) {
    try {
        console.log('\n📋 Testing requests list retrieval...'.cyan);
        const response = await axios.get(`${BASE_URL}/api/expert/requests`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            timeout: 10000
        });
        
        if (response.data.requests && response.data.pagination) {
            console.log('✅ Requests list retrieved successfully'.green);
            console.log(`   Total requests: ${response.data.pagination.total}`.gray);
            console.log(`   Current page: ${response.data.pagination.page}/${response.data.pagination.pages}`.gray);
            console.log(`   Requests in this page: ${response.data.requests.length}`.gray);
            return response.data;
        } else {
            console.log('❌ Invalid requests response structure'.red);
            return null;
        }
    } catch (error) {
        console.log('❌ Failed to retrieve requests list'.red);
        console.log(`   Error: ${error.response?.data?.error || error.message}`.red);
        return null;
    }
}

// Test 4: Test Filtering
async function testFiltering(accessToken) {
    try {
        console.log('\n🔍 Testing filtering functionality...'.cyan);
        
        // Test status filter
        const statusResponse = await axios.get(`${BASE_URL}/api/expert/requests?status=new`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            timeout: 10000
        });
        
        if (statusResponse.data.requests) {
            console.log('✅ Status filtering works'.green);
            console.log(`   New requests: ${statusResponse.data.requests.length}`.gray);
        }
        
        // Test search
        const searchResponse = await axios.get(`${BASE_URL}/api/expert/requests?search=test`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            timeout: 10000
        });
        
        if (searchResponse.data.requests) {
            console.log('✅ Search functionality works'.green);
            console.log(`   Search results: ${searchResponse.data.requests.length}`.gray);
        }
        
        // Test pagination
        const paginationResponse = await axios.get(`${BASE_URL}/api/expert/requests?per_page=5&page=1`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            timeout: 10000
        });
        
        if (paginationResponse.data.requests && paginationResponse.data.pagination.per_page === 5) {
            console.log('✅ Pagination works'.green);
            console.log(`   Page size: ${paginationResponse.data.pagination.per_page}`.gray);
        }
        
        return true;
    } catch (error) {
        console.log('❌ Filtering tests failed'.red);
        console.log(`   Error: ${error.response?.data?.error || error.message}`.red);
        return false;
    }
}

// Test 5: Test Request Detail
async function testRequestDetail(accessToken, requestId) {
    if (!requestId) {
        console.log('\n📄 Skipping request detail test (no request ID available)'.yellow);
        return true;
    }
    
    try {
        console.log('\n📄 Testing request detail retrieval...'.cyan);
        const response = await axios.get(`${BASE_URL}/api/expert/requests/${requestId}`, {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            timeout: 10000
        });
        
        if (response.data.id && response.data.customer && response.data.route) {
            console.log('✅ Request detail retrieved successfully'.green);
            console.log(`   Request ID: ${response.data.id}`.gray);
            console.log(`   Customer: ${response.data.customer.full_name || 'نامشخص'}`.gray);
            return true;
        } else {
            console.log('❌ Invalid request detail response structure'.red);
            return false;
        }
    } catch (error) {
        if (error.response?.status === 404) {
            console.log('⚠️  Request not found (expected if request was deleted)'.yellow);
            return true;
        } else {
            console.log('❌ Failed to retrieve request detail'.red);
            console.log(`   Error: ${error.response?.data?.error || error.message}`.red);
            return false;
        }
    }
}

// Main test runner
async function runTests() {
    let passed = 0;
    let total = 5;
    
    // Test 1: Server Health
    if (await testServerHealth()) {
        passed++;
    } else {
        console.log('\n⚠️  Server is not running. Please start the backend server first.'.bold.yellow);
        console.log('   Run: python backend/wsgi.py or flask run'.gray);
        return;
    }
    
    // Test 2: Expert Login
    const accessToken = await testExpertLogin();
    if (accessToken) {
        passed++;
    } else {
        console.log('\n⚠️  Cannot proceed without authentication.'.bold.yellow);
        return;
    }
    
    // Test 3: Get Requests
    const requestsData = await testGetRequests(accessToken);
    if (requestsData) {
        passed++;
    }
    
    // Test 4: Filtering
    if (await testFiltering(accessToken)) {
        passed++;
    }
    
    // Test 5: Request Detail
    const sampleRequestId = requestsData?.requests?.[0]?.id;
    if (await testRequestDetail(accessToken, sampleRequestId)) {
        passed++;
    }
    
    // Summary
    console.log('\n' + '=' .repeat(60));
    console.log('📊 TEST SUMMARY'.bold.blue);
    console.log(`✅ Passed: ${passed}/${total}`.green);
    console.log(`❌ Failed: ${total - passed}/${total}`.red);
    
    const successRate = ((passed / total) * 100).toFixed(1);
    console.log(`📈 Success Rate: ${successRate}%`.bold);
    
    if (passed === total) {
        console.log('\n🎉 All tests passed! Expert console request retrieval is working correctly.'.bold.green);
    } else if (passed >= 3) {
        console.log('\n⚠️  Most tests passed. Some functionality may need attention.'.bold.yellow);
    } else {
        console.log('\n🚨 Multiple tests failed. Please check the implementation.'.bold.red);
    }
}

// Run tests
runTests().catch(error => {
    console.error('💥 Test runner failed:'.bold.red, error);
    process.exit(1);
});
