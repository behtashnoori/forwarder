#!/usr/bin/env node

/**
 * Expert Authentication Test Script
 * Tests the expert authentication endpoints:
 * - POST /api/expert/auth/login
 * - POST /api/expert/auth/refresh
 * - POST /api/expert/auth/logout
 */

import axios from 'axios';
import colors from 'colors';

// Configuration
const BASE_URL = process.env.API_BASE_URL || 'http://localhost:5000';
const TEST_USERNAME = process.env.EXPERT_USERNAME || 'expert1';
const TEST_PASSWORD = process.env.EXPERT_PASSWORD || 'password123';

// Test results tracking
let testResults = {
    total: 0,
    passed: 0,
    failed: 0,
    errors: []
};

// Helper function to make HTTP requests
async function makeRequest(method, endpoint, data = null, headers = {}) {
    try {
        const config = {
            method,
            url: `${BASE_URL}${endpoint}`,
            headers: {
                'Content-Type': 'application/json',
                ...headers
            },
            timeout: 10000
        };
        
        if (data) {
            config.data = data;
        }
        
        const response = await axios(config);
        return { success: true, data: response.data, status: response.status };
    } catch (error) {
        return {
            success: false,
            error: error.response?.data || error.message,
            status: error.response?.status || 0
        };
    }
}

// Helper function to run a test
function runTest(testName, testFunction) {
    testResults.total++;
    console.log(`\n🧪 Running: ${testName}`.cyan);
    
    return testFunction()
        .then(result => {
            if (result.success) {
                testResults.passed++;
                console.log(`✅ PASSED: ${testName}`.green);
                if (result.details) {
                    console.log(`   ${result.details}`.gray);
                }
            } else {
                testResults.failed++;
                testResults.errors.push({ test: testName, error: result.error });
                console.log(`❌ FAILED: ${testName}`.red);
                console.log(`   Error: ${JSON.stringify(result.error)}`.red);
            }
        })
        .catch(error => {
            testResults.failed++;
            testResults.errors.push({ test: testName, error: error.message });
            console.log(`💥 ERROR: ${testName}`.red);
            console.log(`   Error: ${error.message}`.red);
        });
}

// Test 1: Expert Login with Valid Credentials
async function testExpertLogin() {
    const result = await makeRequest('POST', '/api/expert/auth/login', {
        username: TEST_USERNAME,
        password: TEST_PASSWORD
    });
    
    if (result.success) {
        const data = result.data;
        if (data.success && data.expert && data.tokens) {
            // Store tokens for subsequent tests
            global.accessToken = data.tokens.access_token;
            global.refreshToken = data.tokens.refresh_token;
            global.expertData = data.expert;
            
            return {
                success: true,
                details: `Expert: ${data.expert.full_name} (${data.expert.username}), Token expires in: ${data.tokens.expires_in}s`
            };
        } else {
            return { success: false, error: 'Invalid response structure' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 2: Expert Login with Invalid Credentials
async function testExpertLoginInvalid() {
    const result = await makeRequest('POST', '/api/expert/auth/login', {
        username: 'invalid_user',
        password: 'wrong_password'
    });
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Correctly rejected invalid credentials'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected invalid credentials' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Test 3: Expert Login with Missing Credentials
async function testExpertLoginMissing() {
    const result = await makeRequest('POST', '/api/expert/auth/login', {
        username: TEST_USERNAME
        // Missing password
    });
    
    if (!result.success && (result.status === 400 || result.status === 422)) {
        return {
            success: true,
            details: 'Correctly rejected request with missing password'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected request with missing password' };
    } else {
        return { success: false, error: `Expected 400/422, got ${result.status}` };
    }
}

// Test 4: Token Refresh with Valid Refresh Token
async function testTokenRefresh() {
    if (!global.refreshToken) {
        return { success: false, error: 'No refresh token available from login test' };
    }
    
    const result = await makeRequest('POST', '/api/expert/auth/refresh', {
        refresh_token: global.refreshToken
    });
    
    if (result.success) {
        const data = result.data;
        if (data.access_token && data.refresh_token) {
            // Update tokens
            global.accessToken = data.access_token;
            global.refreshToken = data.refresh_token;
            
            return {
                success: true,
                details: `New tokens generated, expires in: ${data.expires_in}s`
            };
        } else {
            return { success: false, error: 'Invalid token refresh response structure' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 5: Token Refresh with Invalid Refresh Token
async function testTokenRefreshInvalid() {
    const result = await makeRequest('POST', '/api/expert/auth/refresh', {
        refresh_token: 'invalid_refresh_token'
    });
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Correctly rejected invalid refresh token'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected invalid refresh token' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Test 6: Token Refresh with Missing Refresh Token
async function testTokenRefreshMissing() {
    const result = await makeRequest('POST', '/api/expert/auth/refresh', {
        // Missing refresh_token
    });
    
    if (!result.success && (result.status === 400 || result.status === 422)) {
        return {
            success: true,
            details: 'Correctly rejected request with missing refresh token'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected request with missing refresh token' };
    } else {
        return { success: false, error: `Expected 400/422, got ${result.status}` };
    }
}

// Test 7: Expert Logout with Valid Token
async function testExpertLogout() {
    if (!global.accessToken) {
        return { success: false, error: 'No access token available from login test' };
    }
    
    const result = await makeRequest('POST', '/api/expert/auth/logout', null, {
        'Authorization': `Bearer ${global.accessToken}`
    });
    
    if (result.success) {
        return {
            success: true,
            details: 'Successfully logged out'
        };
    } else {
        return { success: false, error: result.error };
    }
}

// Test 8: Expert Logout without Token
async function testExpertLogoutNoToken() {
    const result = await makeRequest('POST', '/api/expert/auth/logout');
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Correctly rejected logout without authentication'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected logout without authentication' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Test 9: Expert Logout with Invalid Token
async function testExpertLogoutInvalidToken() {
    const result = await makeRequest('POST', '/api/expert/auth/logout', null, {
        'Authorization': 'Bearer invalid_token'
    });
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Correctly rejected logout with invalid token'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected logout with invalid token' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Test 10: Test CORS Headers
async function testCORSHeaders() {
    const result = await makeRequest('OPTIONS', '/api/expert/auth/login');
    
    if (result.success || result.status === 200) {
        return {
            success: true,
            details: 'CORS preflight request handled correctly'
        };
    } else {
        return { success: false, error: 'CORS preflight request failed' };
    }
}

// Test 11: Test Protected Endpoint with Valid Token
async function testProtectedEndpoint() {
    if (!global.accessToken) {
        return { success: false, error: 'No access token available from login test' };
    }
    
    // Try to access a protected endpoint (dashboard KPIs)
    const result = await makeRequest('GET', '/api/expert/dashboard/kpis', null, {
        'Authorization': `Bearer ${global.accessToken}`
    });
    
    if (result.success) {
        return {
            success: true,
            details: 'Successfully accessed protected endpoint'
        };
    } else if (result.status === 401) {
        return {
            success: true,
            details: 'Protected endpoint correctly requires authentication'
        };
    } else {
        return { success: false, error: result.error };
    }
}

// Test 12: Test Protected Endpoint without Token
async function testProtectedEndpointNoToken() {
    const result = await makeRequest('GET', '/api/expert/dashboard/kpis');
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Protected endpoint correctly rejected request without token'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected request without token' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Main test runner
async function runAllTests() {
    console.log('🚀 Starting Expert Authentication Tests'.bold.blue);
    console.log(`📍 Base URL: ${BASE_URL}`.gray);
    console.log(`👤 Test Username: ${TEST_USERNAME}`.gray);
    console.log('=' .repeat(60));

    // Login tests
    await runTest('Expert Login (Valid Credentials)', testExpertLogin);
    await runTest('Expert Login (Invalid Credentials)', testExpertLoginInvalid);
    await runTest('Expert Login (Missing Password)', testExpertLoginMissing);
    
    // Token refresh tests
    await runTest('Token Refresh (Valid Token)', testTokenRefresh);
    await runTest('Token Refresh (Invalid Token)', testTokenRefreshInvalid);
    await runTest('Token Refresh (Missing Token)', testTokenRefreshMissing);
    
    // Logout tests
    await runTest('Expert Logout (Valid Token)', testExpertLogout);
    await runTest('Expert Logout (No Token)', testExpertLogoutNoToken);
    await runTest('Expert Logout (Invalid Token)', testExpertLogoutInvalidToken);
    
    // CORS and security tests
    await runTest('CORS Headers', testCORSHeaders);
    await runTest('Protected Endpoint (Valid Token)', testProtectedEndpoint);
    await runTest('Protected Endpoint (No Token)', testProtectedEndpointNoToken);

    // Print summary
    console.log('\n' + '=' .repeat(60));
    console.log('📊 TEST SUMMARY'.bold.blue);
    console.log(`Total Tests: ${testResults.total}`.white);
    console.log(`✅ Passed: ${testResults.passed}`.green);
    console.log(`❌ Failed: ${testResults.failed}`.red);
    
    if (testResults.failed > 0) {
        console.log('\n🚨 FAILED TESTS:'.bold.red);
        testResults.errors.forEach(error => {
            console.log(`   • ${error.test}: ${JSON.stringify(error.error)}`.red);
        });
    }
    
    const successRate = ((testResults.passed / testResults.total) * 100).toFixed(1);
    console.log(`\n📈 Success Rate: ${successRate}%`.bold);
    
    if (testResults.failed === 0) {
        console.log('\n🎉 All tests passed! Expert authentication is working correctly.'.bold.green);
        process.exit(0);
    } else {
        console.log('\n⚠️  Some tests failed. Please check the implementation.'.bold.yellow);
        process.exit(1);
    }
}

// Handle uncaught errors
process.on('unhandledRejection', (error) => {
    console.error('💥 Unhandled Promise Rejection:'.bold.red, error);
    process.exit(1);
});

process.on('uncaughtException', (error) => {
    console.error('💥 Uncaught Exception:'.bold.red, error);
    process.exit(1);
});

// Run tests if this script is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
    runAllTests().catch(error => {
        console.error('💥 Test runner failed:'.bold.red, error);
        process.exit(1);
    });
}

export {
    runAllTests,
    makeRequest,
    runTest
};
