#!/usr/bin/env node

/**
 * Location Hierarchy Flow Test
 * Tests the complete flow from provinces to counties to cities
 */

import fetch from 'node-fetch';

const API_BASE_URL = 'http://127.0.0.1:5000';
const TEST_ORIGIN = 'http://localhost:8109';

async function testHierarchy() {
  console.log('🔗 Testing Location Hierarchy Flow\n');
  
  try {
    // Step 1: Get provinces
    console.log('📍 Step 1: Getting provinces...');
    const provincesResponse = await fetch(`${API_BASE_URL}/api/provinces`, {
      headers: { 'Origin': TEST_ORIGIN }
    });
    
    if (provincesResponse.status !== 200) {
      console.log('❌ Failed to get provinces');
      return false;
    }
    
    const provinces = await provincesResponse.json();
    console.log(`✅ Found ${provinces.length} provinces`);
    
    if (provinces.length === 0) {
      console.log('⚠️  No provinces found, cannot test hierarchy');
      return false;
    }
    
    // Step 2: Get counties for first province
    const firstProvince = provinces[0];
    console.log(`\n📍 Step 2: Getting counties for province "${firstProvince.name}" (ID: ${firstProvince.id})...`);
    
    const countiesResponse = await fetch(`${API_BASE_URL}/api/counties?province_id=${firstProvince.id}`, {
      headers: { 'Origin': TEST_ORIGIN }
    });
    
    if (countiesResponse.status !== 200) {
      console.log('❌ Failed to get counties');
      return false;
    }
    
    const counties = await countiesResponse.json();
    console.log(`✅ Found ${counties.length} counties`);
    
    if (counties.length === 0) {
      console.log('⚠️  No counties found for this province, cannot test cities');
      return true; // This is still a valid result
    }
    
    // Step 3: Get cities for first county
    const firstCounty = counties[0];
    console.log(`\n📍 Step 3: Getting cities for county "${firstCounty.name}" (ID: ${firstCounty.id})...`);
    
    const citiesResponse = await fetch(`${API_BASE_URL}/api/cities?county_id=${firstCounty.id}`, {
      headers: { 'Origin': TEST_ORIGIN }
    });
    
    if (citiesResponse.status !== 200) {
      console.log('❌ Failed to get cities');
      return false;
    }
    
    const cities = await citiesResponse.json();
    console.log(`✅ Found ${cities.length} cities`);
    
    console.log('\n🎯 Hierarchy Test Summary:');
    console.log(`   Province: ${firstProvince.name} (${provinces.length} total provinces)`);
    console.log(`   County: ${firstCounty.name} (${counties.length} counties in province)`);
    console.log(`   Cities: ${cities.length} cities in county`);
    
    if (cities.length > 0) {
      console.log(`   Sample cities: ${cities.slice(0, 3).map(c => c.name).join(', ')}`);
    }
    
    console.log('\n✅ Location hierarchy test completed successfully!');
    return true;
    
  } catch (error) {
    console.log(`❌ Hierarchy test error: ${error.message}`);
    return false;
  }
}

// Run hierarchy test
testHierarchy().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Hierarchy test error:', error);
  process.exit(1);
});
