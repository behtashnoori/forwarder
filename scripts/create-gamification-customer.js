#!/usr/bin/env node

/**
 * Create a gamification customer for testing
 */

import fetch from 'node-fetch';

const API_BASE_URL = 'http://127.0.0.1:5000';

async function createGamificationCustomer() {
  const customerData = {
    email: "gamification.test@example.com",
    phone: "09123456789",
    first_name: "تست",
    last_name: "گیمیفیکیشن"
  };

  try {
    console.log('🎮 Creating gamification customer...');
    
    const response = await fetch(`${API_BASE_URL}/api/customer/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:8109'
      },
      body: JSON.stringify(customerData)
    });

    const result = await response.json();
    
    console.log(`   Status: ${response.status}`);
    console.log(`   Response: ${JSON.stringify(result, null, 2)}`);
    
    if (response.status === 201) {
      console.log('✅ Gamification customer created successfully');
      console.log(`   Customer ID: ${result.id}`);
      console.log(`   Email: ${result.email}`);
      return result.id;
    } else {
      console.log(`❌ Failed to create gamification customer: ${response.status}`);
      return null;
    }
  } catch (error) {
    console.error('❌ Error creating gamification customer:', error.message);
    return null;
  }
}

createGamificationCustomer();
