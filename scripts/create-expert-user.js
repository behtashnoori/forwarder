#!/usr/bin/env node

/**
 * Create Expert User Script
 */

import axios from 'axios';

const BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

console.log('🔧 Creating Expert User...');

// First, let's try to login with different credentials
const testCredentials = [
    { username: 'expert', password: 'expert123' },
    { username: 'expert1', password: 'expert123' },
    { username: 'expert2', password: 'expert123' },
    { username: 'supervisor', password: 'admin123' },
    { username: 'admin', password: 'admin' },
    { username: 'admin', password: 'admin123' },
    { username: 'test', password: 'test' },
    { username: 'test', password: 'test123' }
];

async function testUserCredentials() {
    for (const cred of testCredentials) {
        console.log(`\n🧪 Testing: ${cred.username} / ${cred.password}`);
        
        try {
            const response = await axios.post(`${BASE_URL}/api/expert/auth/login`, {
                username: cred.username,
                password: cred.password
            });
            
            console.log('✅ Login successful!');
            console.log('Expert:', response.data.expert);
            console.log('Tokens:', response.data.tokens);
            return response.data;
        } catch (error) {
            console.log('❌ Login failed');
            if (error.response?.data) {
                console.log('Error:', error.response.data);
            }
        }
    }
    
    console.log('\n❌ No valid credentials found');
    return null;
}

// Run the test
testUserCredentials().then(result => {
    if (result) {
        console.log('\n🎉 Found working credentials!');
    } else {
        console.log('\n⚠️  Need to create expert users first');
    }
}).catch(error => {
    console.error('💥 Error:', error.message);
});
