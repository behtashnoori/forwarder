#!/usr/bin/env node

/**
 * Simple Expert Authentication Test Script
 */

import axios from 'axios';

// Configuration
const BASE_URL = 'http://localhost:5000';
const TEST_USERNAME = 'expert1';
const TEST_PASSWORD = 'expert123';

console.log('🚀 Starting Expert Authentication Tests');
console.log(`📍 Base URL: ${BASE_URL}`);
console.log(`👤 Test Username: ${TEST_USERNAME}`);

// Test 1: Expert Login
async function testLogin() {
    console.log('\n🧪 Testing Expert Login...');
    
    try {
        const response = await axios.post(`${BASE_URL}/api/expert/auth/login`, {
            username: TEST_USERNAME,
            password: TEST_PASSWORD
        });
        
        console.log('✅ Login successful!');
        console.log('Response:', JSON.stringify(response.data, null, 2));
        
        if (response.data.tokens) {
            console.log('✅ Tokens received');
            return response.data.tokens;
        }
        
        return null;
    } catch (error) {
        console.log('❌ Login failed!');
        console.log('Error:', error.response?.data || error.message);
        return null;
    }
}

// Test 2: Token Refresh
async function testTokenRefresh(refreshToken) {
    console.log('\n🧪 Testing Token Refresh...');
    
    if (!refreshToken) {
        console.log('❌ No refresh token available');
        return null;
    }
    
    try {
        const response = await axios.post(`${BASE_URL}/api/expert/auth/refresh`, {
            refresh_token: refreshToken
        });
        
        console.log('✅ Token refresh successful!');
        console.log('Response:', JSON.stringify(response.data, null, 2));
        return response.data;
    } catch (error) {
        console.log('❌ Token refresh failed!');
        console.log('Error:', error.response?.data || error.message);
        return null;
    }
}

// Test 3: Expert Logout
async function testLogout(accessToken) {
    console.log('\n🧪 Testing Expert Logout...');
    
    if (!accessToken) {
        console.log('❌ No access token available');
        return false;
    }
    
    try {
        const response = await axios.post(`${BASE_URL}/api/expert/auth/logout`, {}, {
            headers: {
                'Authorization': `Bearer ${accessToken}`
            }
        });
        
        console.log('✅ Logout successful!');
        console.log('Response:', JSON.stringify(response.data, null, 2));
        return true;
    } catch (error) {
        console.log('❌ Logout failed!');
        console.log('Error:', error.response?.data || error.message);
        return false;
    }
}

// Test 4: Invalid Login
async function testInvalidLogin() {
    console.log('\n🧪 Testing Invalid Login...');
    
    try {
        const response = await axios.post(`${BASE_URL}/api/expert/auth/login`, {
            username: 'invalid_user',
            password: 'wrong_password'
        });
        
        console.log('❌ Invalid login should have failed!');
        console.log('Response:', JSON.stringify(response.data, null, 2));
        return false;
    } catch (error) {
        if (error.response?.status === 401) {
            console.log('✅ Invalid login correctly rejected!');
            console.log('Error:', error.response?.data || error.message);
            return true;
        } else {
            console.log('❌ Unexpected error for invalid login!');
            console.log('Error:', error.response?.data || error.message);
            return false;
        }
    }
}

// Run all tests
async function runAllTests() {
    console.log('='.repeat(60));
    
    // Test 1: Login
    const tokens = await testLogin();
    
    // Test 2: Invalid Login
    await testInvalidLogin();
    
    // Test 3: Token Refresh (if we have tokens)
    let newTokens = null;
    if (tokens && tokens.refresh_token) {
        newTokens = await testTokenRefresh(tokens.refresh_token);
    }
    
    // Test 4: Logout (use new tokens if available, otherwise original)
    const tokenToUse = newTokens?.access_token || tokens?.access_token;
    if (tokenToUse) {
        await testLogout(tokenToUse);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('🎉 Expert Authentication Tests Completed!');
}

// Run tests
runAllTests().catch(error => {
    console.error('💥 Test runner failed:', error);
    process.exit(1);
});
