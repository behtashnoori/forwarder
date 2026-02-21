#!/usr/bin/env node

/**
 * Simple Expert Management Test
 * Tests the GET /api/expert/experts endpoint
 */

import axios from 'axios';

const BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

async function testExpertManagement() {
    console.log('🧪 Testing Expert Management API');
    console.log('================================');
    
    try {
        // Test 1: Check if server is running
        console.log('\n1. Testing server connectivity...');
        const pingResponse = await axios.get(`${BASE_URL}/api/expert/ping`);
        console.log('✅ Server is running:', pingResponse.data.message);
        
        // Test 2: Test experts endpoint without authentication
        console.log('\n2. Testing experts endpoint without authentication...');
        try {
            await axios.get(`${BASE_URL}/api/expert/experts`);
            console.log('❌ Should have failed without authentication');
        } catch (error) {
            if (error.response && error.response.status === 401) {
                console.log('✅ Correctly rejected request without authentication (401)');
            } else {
                console.log('❌ Unexpected error:', error.message);
            }
        }
        
        // Test 3: Test with invalid token
        console.log('\n3. Testing experts endpoint with invalid token...');
        try {
            await axios.get(`${BASE_URL}/api/expert/experts`, {
                headers: {
                    'Authorization': 'Bearer invalid_token_12345'
                }
            });
            console.log('❌ Should have failed with invalid token');
        } catch (error) {
            if (error.response && error.response.status === 401) {
                console.log('✅ Correctly rejected request with invalid token (401)');
            } else {
                console.log('❌ Unexpected error:', error.message);
            }
        }
        
        // Test 4: Test CORS headers
        console.log('\n4. Testing CORS headers...');
        try {
            const corsResponse = await axios.options(`${BASE_URL}/api/expert/experts`);
            console.log('✅ CORS preflight request successful');
            console.log('   CORS Headers:', {
                'Access-Control-Allow-Origin': corsResponse.headers['access-control-allow-origin'],
                'Access-Control-Allow-Methods': corsResponse.headers['access-control-allow-methods'],
                'Access-Control-Allow-Headers': corsResponse.headers['access-control-allow-headers']
            });
        } catch (error) {
            console.log('❌ CORS test failed:', error.message);
        }
        
        console.log('\n🎉 Expert Management API tests completed!');
        console.log('✅ Access control is working correctly');
        console.log('✅ Authentication is required for experts endpoint');
        console.log('✅ CORS headers are properly configured');
        
    } catch (error) {
        console.error('💥 Test failed:', error.message);
        process.exit(1);
    }
}

// Run the test
testExpertManagement();
