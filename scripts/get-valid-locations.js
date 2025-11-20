#!/usr/bin/env node

/**
 * Get valid location IDs for testing
 */

import fetch from 'node-fetch';

const API_BASE_URL = 'http://127.0.0.1:5000';

async function getValidLocations() {
  try {
    console.log('🔍 Getting valid location data...\n');
    
    // Get provinces
    const provincesResponse = await fetch(`${API_BASE_URL}/api/provinces`);
    const provinces = await provincesResponse.json();
    
    console.log('📋 Available Provinces:');
    provinces.slice(0, 5).forEach(p => {
      console.log(`   ID: ${p.id}, Name: ${p.name_fa}`);
    });
    
    if (provinces.length > 0) {
      const firstProvince = provinces[0];
      
      // Get counties for first province
      const countiesResponse = await fetch(`${API_BASE_URL}/api/counties?province_id=${firstProvince.id}`);
      const counties = await countiesResponse.json();
      
      console.log(`\n🏘️ Counties in ${firstProvince.name_fa}:`);
      counties.slice(0, 3).forEach(c => {
        console.log(`   ID: ${c.id}, Name: ${c.name_fa}`);
      });
      
      if (counties.length > 0) {
        const firstCounty = counties[0];
        
        // Get cities for first county
        const citiesResponse = await fetch(`${API_BASE_URL}/api/cities?county_id=${firstCounty.id}`);
        const cities = await citiesResponse.json();
        
        console.log(`\n🏙️ Cities in ${firstCounty.name_fa}:`);
        cities.slice(0, 3).forEach(c => {
          console.log(`   ID: ${c.id}, Name: ${c.name_fa}`);
        });
        
        // Get second province for destination
        const secondProvince = provinces[1] || provinces[0];
        const destCountiesResponse = await fetch(`${API_BASE_URL}/api/counties?province_id=${secondProvince.id}`);
        const destCounties = await destCountiesResponse.json();
        
        console.log(`\n🏘️ Counties in ${secondProvince.name_fa} (destination):`);
        destCounties.slice(0, 3).forEach(c => {
          console.log(`   ID: ${c.id}, Name: ${c.name_fa}`);
        });
        
        if (destCounties.length > 0) {
          const destCounty = destCounties[0];
          const destCitiesResponse = await fetch(`${API_BASE_URL}/api/cities?county_id=${destCounty.id}`);
          const destCities = await destCitiesResponse.json();
          
          console.log(`\n🏙️ Cities in ${destCounty.name_fa} (destination):`);
          destCities.slice(0, 3).forEach(c => {
            console.log(`   ID: ${c.id}, Name: ${c.name_fa}`);
          });
          
          // Return valid test data
          const validData = {
            origin_province_id: firstProvince.id,
            origin_county_id: firstCounty.id,
            origin_city_id: cities[0]?.id,
            dest_province_id: secondProvince.id,
            dest_county_id: destCounty.id,
            dest_city_id: destCities[0]?.id
          };
          
          console.log('\n✅ Valid test data:');
          console.log(JSON.stringify(validData, null, 2));
          
          return validData;
        }
      }
    }
    
  } catch (error) {
    console.error('❌ Error getting location data:', error.message);
  }
}

getValidLocations();
