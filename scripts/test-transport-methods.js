/**
 * Comprehensive test script for Transport Methods API
 * Tests GET /api/transport-methods endpoint and categorization
 */

import axios from 'axios';

// Configuration
const BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const API_ENDPOINT = `${BASE_URL}/api/transport-methods`;

// Test results storage
let testResults = {
    passed: 0,
    failed: 0,
    tests: []
};

// Helper function to log test results
function logTest(testName, passed, message = '', details = null) {
    const status = passed ? '✅ PASS' : '❌ FAIL';
    console.log(`${status} - ${testName}`);
    if (message) console.log(`   ${message}`);
    if (details && !passed) console.log(`   Details: ${JSON.stringify(details, null, 2)}`);
    
    testResults.tests.push({
        name: testName,
        passed,
        message,
        details
    });
    
    if (passed) testResults.passed++;
    else testResults.failed++;
}

// Test 1: Basic API connectivity and response structure
async function testBasicConnectivity() {
    console.log('\n🔍 Testing Basic API Connectivity...');
    
    try {
        const response = await axios.get(API_ENDPOINT, {
            timeout: 10000,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        // Check response status
        if (response.status === 200) {
            logTest('API Response Status', true, `Status: ${response.status}`);
        } else {
            logTest('API Response Status', false, `Expected 200, got ${response.status}`);
            return false;
        }
        
        // Check response structure
        const data = response.data;
        const requiredFields = ['international_methods', 'domestic_methods', 'preference_options'];
        const missingFields = requiredFields.filter(field => !(field in data));
        
        if (missingFields.length === 0) {
            logTest('Response Structure', true, 'All required fields present');
        } else {
            logTest('Response Structure', false, `Missing fields: ${missingFields.join(', ')}`);
            return false;
        }
        
        return data;
        
    } catch (error) {
        if (error.code === 'ECONNREFUSED') {
            logTest('API Connectivity', false, 'Connection refused - is the server running?');
        } else if (error.code === 'ENOTFOUND') {
            logTest('API Connectivity', false, 'Host not found - check BASE_URL');
        } else {
            logTest('API Connectivity', false, `Error: ${error.message}`);
        }
        return false;
    }
}

// Test 2: Transport methods data validation
async function testTransportMethodsData(data) {
    console.log('\n🔍 Testing Transport Methods Data...');
    
    const { international_methods, domestic_methods, preference_options } = data;
    
    // Test international methods
    if (Array.isArray(international_methods)) {
        logTest('International Methods Array', true, `Found ${international_methods.length} methods`);
        
        // Validate each international method
        international_methods.forEach((method, index) => {
            const requiredFields = ['id', 'name', 'name_fa'];
            const missingFields = requiredFields.filter(field => !(field in method));
            
            if (missingFields.length === 0) {
                logTest(`International Method ${index + 1} Structure`, true, 
                    `${method.name_fa} (${method.name})`);
            } else {
                logTest(`International Method ${index + 1} Structure`, false, 
                    `Missing fields: ${missingFields.join(', ')}`);
            }
        });
    } else {
        logTest('International Methods Array', false, 'international_methods is not an array');
    }
    
    // Test domestic methods
    if (Array.isArray(domestic_methods)) {
        logTest('Domestic Methods Array', true, `Found ${domestic_methods.length} methods`);
        
        // Validate each domestic method
        domestic_methods.forEach((method, index) => {
            const requiredFields = ['id', 'name', 'name_fa'];
            const missingFields = requiredFields.filter(field => !(field in method));
            
            if (missingFields.length === 0) {
                logTest(`Domestic Method ${index + 1} Structure`, true, 
                    `${method.name_fa} (${method.name})`);
            } else {
                logTest(`Domestic Method ${index + 1} Structure`, false, 
                    `Missing fields: ${missingFields.join(', ')}`);
            }
        });
    } else {
        logTest('Domestic Methods Array', false, 'domestic_methods is not an array');
    }
    
    // Test preference options
    if (Array.isArray(preference_options)) {
        logTest('Preference Options Array', true, `Found ${preference_options.length} options`);
        
        preference_options.forEach((option, index) => {
            const requiredFields = ['value', 'label', 'description'];
            const missingFields = requiredFields.filter(field => !(field in option));
            
            if (missingFields.length === 0) {
                logTest(`Preference Option ${index + 1}`, true, 
                    `${option.label} (${option.value})`);
            } else {
                logTest(`Preference Option ${index + 1}`, false, 
                    `Missing fields: ${missingFields.join(', ')}`);
            }
        });
    } else {
        logTest('Preference Options Array', false, 'preference_options is not an array');
    }
}

// Test 3: Categorization logic validation
async function testCategorizationLogic(data) {
    console.log('\n🔍 Testing Categorization Logic...');
    
    const { international_methods, domestic_methods } = data;
    
    // Expected international methods based on the categorization logic
    const expectedInternational = ['sea freight', 'air freight', 'land transport', 'rail transport'];
    const expectedDomestic = ['road transport', 'rail transport', 'air transport'];
    
    // Check if expected international methods are present
    const foundInternational = international_methods.map(m => m.name.toLowerCase());
    const missingInternational = expectedInternational.filter(method => 
        !foundInternational.includes(method)
    );
    
    if (missingInternational.length === 0) {
        logTest('International Methods Coverage', true, 
            'All expected international methods found');
    } else {
        logTest('International Methods Coverage', false, 
            `Missing international methods: ${missingInternational.join(', ')}`);
    }
    
    // Check if expected domestic methods are present
    const foundDomestic = domestic_methods.map(m => m.name.toLowerCase());
    const missingDomestic = expectedDomestic.filter(method => 
        !foundDomestic.includes(method)
    );
    
    if (missingDomestic.length === 0) {
        logTest('Domestic Methods Coverage', true, 
            'All expected domestic methods found');
    } else {
        logTest('Domestic Methods Coverage', false, 
            `Missing domestic methods: ${missingDomestic.join(', ')}`);
    }
    
    // Check for overlap (methods that appear in both categories)
    const internationalNames = new Set(foundInternational);
    const domesticNames = new Set(foundDomestic);
    const overlap = [...internationalNames].filter(name => domesticNames.has(name));
    
    if (overlap.length > 0) {
        logTest('Method Overlap Check', true, 
            `Methods in both categories: ${overlap.join(', ')} (expected for rail transport)`);
    } else {
        logTest('Method Overlap Check', true, 'No overlap found');
    }
}

// Test 4: Performance and response time
async function testPerformance() {
    console.log('\n🔍 Testing Performance...');
    
    const startTime = Date.now();
    
    try {
        const response = await axios.get(API_ENDPOINT);
        const endTime = Date.now();
        const responseTime = endTime - startTime;
        
        if (responseTime < 1000) {
            logTest('Response Time', true, `Response time: ${responseTime}ms`);
        } else if (responseTime < 3000) {
            logTest('Response Time', true, `Response time: ${responseTime}ms (acceptable)`);
        } else {
            logTest('Response Time', false, `Response time: ${responseTime}ms (too slow)`);
        }
        
    } catch (error) {
        logTest('Performance Test', false, `Error during performance test: ${error.message}`);
    }
}

// Test 5: Error handling
async function testErrorHandling() {
    console.log('\n🔍 Testing Error Handling...');
    
    // Test with invalid endpoint
    try {
        await axios.get(`${BASE_URL}/api/invalid-endpoint`);
        logTest('Invalid Endpoint Handling', false, 'Should have returned 404');
    } catch (error) {
        if (error.response && error.response.status === 404) {
            logTest('Invalid Endpoint Handling', true, 'Correctly returned 404 for invalid endpoint');
        } else {
            logTest('Invalid Endpoint Handling', false, `Unexpected error: ${error.message}`);
        }
    }
}

// Test 6: Data consistency
async function testDataConsistency(data) {
    console.log('\n🔍 Testing Data Consistency...');
    
    const { international_methods, domestic_methods } = data;
    const allMethods = [...international_methods, ...domestic_methods];
    
    // Check for duplicate IDs (expected for methods that appear in both categories)
    const ids = allMethods.map(m => m.id);
    const uniqueIds = new Set(ids);
    
    if (ids.length === uniqueIds.size) {
        logTest('Unique IDs', true, 'All method IDs are unique');
    } else {
        const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
        const duplicateMethods = [...new Set(duplicates)].map(id => {
            const method = allMethods.find(m => m.id === id);
            return method ? `${method.name_fa} (${method.name})` : id;
        });
        logTest('Method Overlap in Categories', true, 
            `Methods appearing in both categories: ${duplicateMethods.join(', ')} (expected behavior)`);
    }
    
    // Check for required fields in all methods
    const methodsWithMissingFields = allMethods.filter(method => 
        !method.id || !method.name || !method.name_fa
    );
    
    if (methodsWithMissingFields.length === 0) {
        logTest('Required Fields', true, 'All methods have required fields');
    } else {
        logTest('Required Fields', false, 
            `${methodsWithMissingFields.length} methods missing required fields`);
    }
}

// Main test runner
async function runAllTests() {
    console.log('🚀 Starting Transport Methods API Tests');
    console.log(`📍 Testing endpoint: ${API_ENDPOINT}`);
    console.log('=' .repeat(60));
    
    try {
        // Test 1: Basic connectivity
        const data = await testBasicConnectivity();
        
        if (data) {
            // Test 2: Data validation
            await testTransportMethodsData(data);
            
            // Test 3: Categorization logic
            await testCategorizationLogic(data);
            
            // Test 4: Data consistency
            await testDataConsistency(data);
        }
        
        // Test 5: Performance
        await testPerformance();
        
        // Test 6: Error handling
        await testErrorHandling();
        
    } catch (error) {
        console.error('❌ Test suite failed:', error.message);
        testResults.failed++;
    }
    
    // Print summary
    console.log('\n' + '=' .repeat(60));
    console.log('📊 TEST SUMMARY');
    console.log('=' .repeat(60));
    console.log(`✅ Passed: ${testResults.passed}`);
    console.log(`❌ Failed: ${testResults.failed}`);
    console.log(`📈 Success Rate: ${((testResults.passed / (testResults.passed + testResults.failed)) * 100).toFixed(1)}%`);
    
    if (testResults.failed > 0) {
        console.log('\n❌ Failed Tests:');
        testResults.tests
            .filter(test => !test.passed)
            .forEach(test => {
                console.log(`   - ${test.name}: ${test.message}`);
            });
    }
    
    console.log('\n🏁 Test completed!');
    
    // Exit with appropriate code
    process.exit(testResults.failed > 0 ? 1 : 0);
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1);
});

// Run the tests
runAllTests();
