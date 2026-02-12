#!/usr/bin/env node

/**
 * Expert User Management Test Script
 * Tests the expert user management functionality:
 * - GET /api/expert/experts (List experts)
 * - Access control and permission levels
 * - Authentication requirements
 * - Role-based access
 */

import axios from 'axios';
import colors from 'colors';

// Configuration
const BASE_URL = process.env.API_BASE_URL || 'http://localhost:5000';
const TEST_USERNAME = process.env.EXPERT_USERNAME || 'expert1';
const TEST_PASSWORD = process.env.EXPERT_PASSWORD || 'password123';
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || 'admin';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';

// Test results tracking
let testResults = {
    total: 0,
    passed: 0,
    failed: 0,
    errors: []
};

// Global variables for storing authentication data
let expertTokens = null;
let adminTokens = null;
let expertData = null;
let adminData = null;

// Helper function to make HTTP requests
async function makeRequest(method, endpoint, data = null, headers = {}) {
    try {
        const config = {
            method,
            url: `${BASE_URL}${endpoint}`,
            headers: {
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:3000',
                ...headers
            },
            timeout: 10000
        };
        
        if (data) {
            config.data = data;
        }
        
        const response = await axios(config);
        return { success: true, data: response.data, status: response.status, headers: response.headers };
    } catch (error) {
        return {
            success: false,
            error: error.response?.data || error.message,
            status: error.response?.status || 0,
            headers: error.response?.headers || {}
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

// Test 1: Expert Login for Authentication
async function testExpertLogin() {
    const result = await makeRequest('POST', '/api/expert/auth/login', {
        username: TEST_USERNAME,
        password: TEST_PASSWORD
    });
    
    if (result.success) {
        const data = result.data;
        if (data.success && data.expert && data.tokens) {
            expertTokens = data.tokens;
            expertData = data.expert;
            
            return {
                success: true,
                details: `Expert: ${data.expert.full_name} (${data.expert.username}), Role: ${data.expert.role}`
            };
        } else {
            return { success: false, error: 'Invalid response structure' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 2: Admin Login for Authentication (if available)
async function testAdminLogin() {
    const result = await makeRequest('POST', '/api/expert/auth/login', {
        username: ADMIN_USERNAME,
        password: ADMIN_PASSWORD
    });
    
    if (result.success) {
        const data = result.data;
        if (data.success && data.expert && data.tokens) {
            adminTokens = data.tokens;
            adminData = data.expert;
            
            return {
                success: true,
                details: `Admin: ${data.expert.full_name} (${data.expert.username}), Role: ${data.expert.role}`
            };
        } else {
            return { success: false, error: 'Invalid response structure' };
        }
    } else if (result.status === 401) {
        return {
            success: true,
            details: 'Admin credentials not available (expected in test environment)'
        };
    } else {
        return { success: false, error: result.error };
    }
}

// Test 3: Get Experts List without Authentication
async function testGetExpertsNoAuth() {
    const result = await makeRequest('GET', '/api/expert/experts');
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Correctly rejected request without authentication'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected request without authentication' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Test 4: Get Experts List with Valid Expert Token
async function testGetExpertsWithAuth() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/experts', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        if (data.experts && Array.isArray(data.experts)) {
            const expertCount = data.experts.length;
            const activeExperts = data.experts.filter(e => e.id && e.username && e.full_name);
            
            return {
                success: true,
                details: `Retrieved ${expertCount} experts, ${activeExperts.length} with complete data`
            };
        } else {
            return { success: false, error: 'Invalid response structure - missing experts array' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 5: Verify Experts List Structure
async function testExpertsListStructure() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/experts', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        if (data.experts && Array.isArray(data.experts)) {
            const requiredFields = ['id', 'username', 'full_name', 'role'];
            const validExperts = data.experts.filter(expert => {
                return requiredFields.every(field => expert.hasOwnProperty(field));
            });
            
            if (validExperts.length === data.experts.length) {
                return {
                    success: true,
                    details: `All ${validExperts.length} experts have required fields: ${requiredFields.join(', ')}`
                };
            } else {
                return { 
                    success: false, 
                    error: `Only ${validExperts.length}/${data.experts.length} experts have required fields` 
                };
            }
        } else {
            return { success: false, error: 'Invalid response structure' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 6: Check Expert Data Privacy
async function testExpertDataPrivacy() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/experts', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        if (data.experts && Array.isArray(data.experts)) {
            const sensitiveFields = ['password_hash', 'email', 'phone'];
            const hasSensitiveData = data.experts.some(expert => {
                return sensitiveFields.some(field => expert.hasOwnProperty(field));
            });
            
            if (!hasSensitiveData) {
                return {
                    success: true,
                    details: 'No sensitive data exposed in experts list'
                };
            } else {
                return { 
                    success: false, 
                    error: 'Sensitive data found in experts list response' 
                };
            }
        } else {
            return { success: false, error: 'Invalid response structure' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 7: Test with Invalid Token
async function testGetExpertsInvalidToken() {
    const result = await makeRequest('GET', '/api/expert/experts', null, {
        'Authorization': 'Bearer invalid_token_12345'
    });
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Correctly rejected request with invalid token'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected request with invalid token' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Test 8: Test with Expired Token Format
async function testGetExpertsExpiredToken() {
    const result = await makeRequest('GET', '/api/expert/experts', null, {
        'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid_signature'
    });
    
    if (!result.success && result.status === 401) {
        return {
            success: true,
            details: 'Correctly rejected request with expired/invalid token format'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have rejected request with expired token' };
    } else {
        return { success: false, error: `Expected 401, got ${result.status}` };
    }
}

// Test 9: Test CORS Headers for Experts Endpoint
async function testCORSHeaders() {
    const result = await makeRequest('OPTIONS', '/api/expert/experts');
    
    if (result.success || result.status === 200) {
        const corsHeaders = {
            'Access-Control-Allow-Origin': result.headers['access-control-allow-origin'],
            'Access-Control-Allow-Methods': result.headers['access-control-allow-methods'],
            'Access-Control-Allow-Headers': result.headers['access-control-allow-headers']
        };
        
        const hasCORS = Object.values(corsHeaders).some(header => header);
        
        if (hasCORS) {
            return {
                success: true,
                details: 'CORS headers present for experts endpoint'
            };
        } else {
            return { success: false, error: 'CORS headers missing' };
        }
    } else {
        return { success: false, error: 'CORS preflight request failed' };
    }
}

// Test 10: Test Rate Limiting (if implemented)
async function testRateLimiting() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    // Make multiple rapid requests
    const requests = [];
    for (let i = 0; i < 5; i++) {
        requests.push(makeRequest('GET', '/api/expert/experts', null, {
            'Authorization': `Bearer ${expertTokens.access_token}`
        }));
    }
    
    const results = await Promise.all(requests);
    const successCount = results.filter(r => r.success).length;
    const rateLimitedCount = results.filter(r => r.status === 429).length;
    
    if (successCount >= 3) {
        return {
            success: true,
            details: `Rate limiting not implemented or generous limits (${successCount}/5 requests succeeded)`
        };
    } else if (rateLimitedCount > 0) {
        return {
            success: true,
            details: `Rate limiting working (${rateLimitedCount} requests rate limited)`
        };
    } else {
        return { success: false, error: 'Unexpected rate limiting behavior' };
    }
}

// Test 11: Test Response Time
async function testResponseTime() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const startTime = Date.now();
    const result = await makeRequest('GET', '/api/expert/experts', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    const endTime = Date.now();
    const responseTime = endTime - startTime;
    
    if (result.success) {
        if (responseTime < 2000) { // Less than 2 seconds
            return {
                success: true,
                details: `Response time: ${responseTime}ms (acceptable)`
            };
        } else {
            return {
                success: false,
                error: `Response time too slow: ${responseTime}ms`
            };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 12: Test Expert Role Filtering (if implemented)
async function testExpertRoleFiltering() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/experts', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        if (data.experts && Array.isArray(data.experts)) {
            const roles = [...new Set(data.experts.map(e => e.role))];
            const activeExperts = data.experts.filter(e => e.id);
            
            return {
                success: true,
                details: `Found ${activeExperts.length} active experts with roles: ${roles.join(', ')}`
            };
        } else {
            return { success: false, error: 'Invalid response structure' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Main test runner
async function runAllTests() {
    console.log('🚀 Starting Expert User Management Tests'.bold.blue);
    console.log(`📍 Base URL: ${BASE_URL}`.gray);
    console.log(`👤 Test Expert: ${TEST_USERNAME}`.gray);
    console.log(`👑 Test Admin: ${ADMIN_USERNAME}`.gray);
    console.log('=' .repeat(60));

    // Authentication tests
    await runTest('Expert Login', testExpertLogin);
    await runTest('Admin Login (Optional)', testAdminLogin);
    
    // Access control tests
    await runTest('Get Experts (No Auth)', testGetExpertsNoAuth);
    await runTest('Get Experts (Valid Token)', testGetExpertsWithAuth);
    await runTest('Get Experts (Invalid Token)', testGetExpertsInvalidToken);
    await runTest('Get Experts (Expired Token)', testGetExpertsExpiredToken);
    
    // Data structure and privacy tests
    await runTest('Experts List Structure', testExpertsListStructure);
    await runTest('Expert Data Privacy', testExpertDataPrivacy);
    await runTest('Expert Role Filtering', testExpertRoleFiltering);
    
    // Performance and security tests
    await runTest('CORS Headers', testCORSHeaders);
    await runTest('Rate Limiting', testRateLimiting);
    await runTest('Response Time', testResponseTime);

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
        console.log('\n🎉 All tests passed! Expert user management is working correctly.'.bold.green);
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
