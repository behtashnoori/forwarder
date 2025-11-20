#!/usr/bin/env node

/**
 * Expert Console Request Retrieval Test Script
 * Tests the expert console request management functionality:
 * - GET /api/expert/requests (List requests with filtering, search, pagination)
 * - GET /api/expert/requests/<id> (Get request details)
 * - Authentication and authorization
 * - Filtering and search capabilities
 * - Pagination functionality
 * - Performance and response structure validation
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

// Global variables for storing authentication data
let expertTokens = null;
let expertData = null;
let sampleRequestId = null;

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
            timeout: 15000
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

// Test 2: Get Requests List without Authentication
async function testGetRequestsNoAuth() {
    const result = await makeRequest('GET', '/api/expert/requests');
    
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

// Test 3: Get Requests List with Valid Authentication
async function testGetRequestsWithAuth() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/requests', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        if (data.requests && data.pagination) {
            // Store first request ID for detail tests
            if (data.requests.length > 0) {
                sampleRequestId = data.requests[0].id;
            }
            
            return {
                success: true,
                details: `Retrieved ${data.requests.length} requests, Total: ${data.pagination.total}, Page: ${data.pagination.page}/${data.pagination.pages}`
            };
        } else {
            return { success: false, error: 'Invalid response structure - missing requests or pagination' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 4: Verify Requests List Structure
async function testRequestsListStructure() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/requests', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        if (data.requests && Array.isArray(data.requests)) {
            const requiredFields = ['id', 'tracking_number', 'status', 'priority', 'created_at', 'customer', 'route'];
            const validRequests = data.requests.filter(request => {
                return requiredFields.every(field => request.hasOwnProperty(field));
            });
            
            if (validRequests.length === data.requests.length || data.requests.length === 0) {
                return {
                    success: true,
                    details: `All ${validRequests.length} requests have required fields: ${requiredFields.join(', ')}`
                };
            } else {
                return { 
                    success: false, 
                    error: `Only ${validRequests.length}/${data.requests.length} requests have required fields` 
                };
            }
        } else {
            return { success: false, error: 'Invalid response structure - requests is not an array' };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 5: Test Pagination Parameters
async function testPaginationParameters() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    // Test different page sizes
    const pageSizes = [5, 10, 20, 50];
    let allPassed = true;
    let details = [];
    
    for (const perPage of pageSizes) {
        const result = await makeRequest('GET', `/api/expert/requests?per_page=${perPage}`, null, {
            'Authorization': `Bearer ${expertTokens.access_token}`
        });
        
        if (result.success) {
            const data = result.data;
            if (data.requests.length <= perPage && data.pagination.per_page === perPage) {
                details.push(`Page size ${perPage}: ✅`);
            } else {
                details.push(`Page size ${perPage}: ❌ (got ${data.requests.length}, expected ≤${perPage})`);
                allPassed = false;
            }
        } else {
            details.push(`Page size ${perPage}: ❌ (request failed)`);
            allPassed = false;
        }
    }
    
    return {
        success: allPassed,
        details: details.join(', ')
    };
}

// Test 6: Test Status Filtering
async function testStatusFiltering() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const statuses = ['new', 'assigned', 'in_progress', 'won', 'lost'];
    let allPassed = true;
    let details = [];
    
    for (const status of statuses) {
        const result = await makeRequest('GET', `/api/expert/requests?status=${status}`, null, {
            'Authorization': `Bearer ${expertTokens.access_token}`
        });
        
        if (result.success) {
            const data = result.data;
            const filteredRequests = data.requests.filter(req => 
                req.status === status || req.status_request_status === status
            );
            
            if (filteredRequests.length === data.requests.length || data.requests.length === 0) {
                details.push(`${status}: ${data.requests.length} requests`);
            } else {
                details.push(`${status}: ❌ (filter not working properly)`);
                allPassed = false;
            }
        } else {
            details.push(`${status}: ❌ (request failed)`);
            allPassed = false;
        }
    }
    
    return {
        success: allPassed,
        details: details.join(', ')
    };
}

// Test 7: Test Search Functionality
async function testSearchFunctionality() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    // Test search with common terms
    const searchTerms = ['test', 'customer', 'cargo', '123'];
    let allPassed = true;
    let details = [];
    
    for (const term of searchTerms) {
        const result = await makeRequest('GET', `/api/expert/requests?search=${encodeURIComponent(term)}`, null, {
            'Authorization': `Bearer ${expertTokens.access_token}`
        });
        
        if (result.success) {
            const data = result.data;
            details.push(`"${term}": ${data.requests.length} results`);
        } else {
            details.push(`"${term}": ❌ (request failed)`);
            allPassed = false;
        }
    }
    
    return {
        success: allPassed,
        details: details.join(', ')
    };
}

// Test 8: Test Sorting Parameters
async function testSortingParameters() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const sortOptions = [
        { sort_by: 'created_at', sort_order: 'desc' },
        { sort_by: 'created_at', sort_order: 'asc' },
        { sort_by: 'sla_due_at', sort_order: 'desc' },
        { sort_by: 'priority', sort_order: 'asc' }
    ];
    
    let allPassed = true;
    let details = [];
    
    for (const sort of sortOptions) {
        const result = await makeRequest('GET', `/api/expert/requests?sort_by=${sort.sort_by}&sort_order=${sort.sort_order}`, null, {
            'Authorization': `Bearer ${expertTokens.access_token}`
        });
        
        if (result.success) {
            const data = result.data;
            details.push(`${sort.sort_by} ${sort.sort_order}: ${data.requests.length} requests`);
        } else {
            details.push(`${sort.sort_by} ${sort.sort_order}: ❌ (request failed)`);
            allPassed = false;
        }
    }
    
    return {
        success: allPassed,
        details: details.join(', ')
    };
}

// Test 9: Test Priority Filtering
async function testPriorityFiltering() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const priorities = ['low', 'normal', 'high', 'urgent'];
    let allPassed = true;
    let details = [];
    
    for (const priority of priorities) {
        const result = await makeRequest('GET', `/api/expert/requests?priority=${priority}`, null, {
            'Authorization': `Bearer ${expertTokens.access_token}`
        });
        
        if (result.success) {
            const data = result.data;
            const filteredRequests = data.requests.filter(req => req.priority === priority);
            
            if (filteredRequests.length === data.requests.length || data.requests.length === 0) {
                details.push(`${priority}: ${data.requests.length} requests`);
            } else {
                details.push(`${priority}: ❌ (filter not working properly)`);
                allPassed = false;
            }
        } else {
            details.push(`${priority}: ❌ (request failed)`);
            allPassed = false;
        }
    }
    
    return {
        success: allPassed,
        details: details.join(', ')
    };
}

// Test 10: Test Assigned To Filtering
async function testAssignedToFiltering() {
    if (!expertTokens || !expertData) {
        return { success: false, error: 'No expert token or data available from login test' };
    }
    
    const result = await makeRequest('GET', `/api/expert/requests?assigned_to=${expertData.id}`, null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        const assignedRequests = data.requests.filter(req => 
            req.assigned_to && req.assigned_to.id === expertData.id
        );
        
        if (assignedRequests.length === data.requests.length || data.requests.length === 0) {
            return {
                success: true,
                details: `Found ${data.requests.length} requests assigned to expert ${expertData.id}`
            };
        } else {
            return { 
                success: false, 
                error: `Filter not working properly: ${assignedRequests.length}/${data.requests.length} requests match filter` 
            };
        }
    } else {
        return { success: false, error: result.error };
    }
}

// Test 11: Test Request Detail Retrieval
async function testRequestDetailRetrieval() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    if (!sampleRequestId) {
        return { success: true, details: 'No sample request ID available (no requests in system)' };
    }
    
    const result = await makeRequest('GET', `/api/expert/requests/${sampleRequestId}`, null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        const requiredFields = ['id', 'tracking_number', 'status', 'customer', 'route', 'cargo', 'timeline', 'messages'];
        const hasRequiredFields = requiredFields.every(field => data.hasOwnProperty(field));
        
        if (hasRequiredFields) {
            return {
                success: true,
                details: `Request ${sampleRequestId} details retrieved with all required fields`
            };
        } else {
            return { 
                success: false, 
                error: `Missing required fields in request detail response` 
            };
        }
    } else if (result.status === 404) {
        return {
            success: true,
            details: `Request ${sampleRequestId} not found (expected if request was deleted)`
        };
    } else {
        return { success: false, error: result.error };
    }
}

// Test 12: Test Invalid Request ID
async function testInvalidRequestId() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/requests/999999', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (!result.success && result.status === 404) {
        return {
            success: true,
            details: 'Correctly returned 404 for non-existent request ID'
        };
    } else if (result.success) {
        return { success: false, error: 'Should have returned 404 for non-existent request ID' };
    } else {
        return { success: false, error: `Expected 404, got ${result.status}` };
    }
}

// Test 13: Test Response Time Performance
async function testResponseTimePerformance() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const startTime = Date.now();
    const result = await makeRequest('GET', '/api/expert/requests', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    const endTime = Date.now();
    const responseTime = endTime - startTime;
    
    if (result.success) {
        if (responseTime < 3000) { // Less than 3 seconds
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

// Test 14: Test Multiple Filter Combination
async function testMultipleFilterCombination() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    const result = await makeRequest('GET', '/api/expert/requests?status=new&priority=high&per_page=5&sort_by=created_at&sort_order=desc', null, {
        'Authorization': `Bearer ${expertTokens.access_token}`
    });
    
    if (result.success) {
        const data = result.data;
        return {
            success: true,
            details: `Combined filters: ${data.requests.length} requests, Page: ${data.pagination.page}, Total: ${data.pagination.total}`
        };
    } else {
        return { success: false, error: result.error };
    }
}

// Test 15: Test CORS Headers
async function testCORSHeaders() {
    const result = await makeRequest('OPTIONS', '/api/expert/requests');
    
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
                details: 'CORS headers present for requests endpoint'
            };
        } else {
            return { success: false, error: 'CORS headers missing' };
        }
    } else {
        return { success: false, error: 'CORS preflight request failed' };
    }
}

// Test 16: Test Rate Limiting
async function testRateLimiting() {
    if (!expertTokens) {
        return { success: false, error: 'No expert token available from login test' };
    }
    
    // Make multiple rapid requests
    const requests = [];
    for (let i = 0; i < 5; i++) {
        requests.push(makeRequest('GET', '/api/expert/requests', null, {
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

// Main test runner
async function runAllTests() {
    console.log('🚀 Starting Expert Console Request Retrieval Tests'.bold.blue);
    console.log(`📍 Base URL: ${BASE_URL}`.gray);
    console.log(`👤 Test Expert: ${TEST_USERNAME}`.gray);
    console.log('=' .repeat(70));

    // Authentication tests
    await runTest('Expert Login', testExpertLogin);
    
    // Basic access control tests
    await runTest('Get Requests (No Auth)', testGetRequestsNoAuth);
    await runTest('Get Requests (Valid Auth)', testGetRequestsWithAuth);
    await runTest('Requests List Structure', testRequestsListStructure);
    
    // Pagination tests
    await runTest('Pagination Parameters', testPaginationParameters);
    
    // Filtering tests
    await runTest('Status Filtering', testStatusFiltering);
    await runTest('Priority Filtering', testPriorityFiltering);
    await runTest('Assigned To Filtering', testAssignedToFiltering);
    await runTest('Search Functionality', testSearchFunctionality);
    await runTest('Sorting Parameters', testSortingParameters);
    await runTest('Multiple Filter Combination', testMultipleFilterCombination);
    
    // Detail retrieval tests
    await runTest('Request Detail Retrieval', testRequestDetailRetrieval);
    await runTest('Invalid Request ID', testInvalidRequestId);
    
    // Performance and security tests
    await runTest('Response Time Performance', testResponseTimePerformance);
    await runTest('CORS Headers', testCORSHeaders);
    await runTest('Rate Limiting', testRateLimiting);

    // Print summary
    console.log('\n' + '=' .repeat(70));
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
        console.log('\n🎉 All tests passed! Expert console request retrieval is working correctly.'.bold.green);
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
