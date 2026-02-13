#!/usr/bin/env node

/**
 * Test Login Credentials Script
 * Tests login functionality for expert and admin users
 */

import axios from 'axios';

const BASE_URL = 'http://localhost:5000';

// Test credentials
const TEST_CREDENTIALS = [
    {
        username: 'expert',
        password: 'expert123',
        role: 'expert',
        description: 'کارشناس'
    },
    {
        username: 'admin',
        password: 'Pirooz13@!',
        role: 'admin',
        description: 'مدیر سیستم'
    }
];

async function testLogin(username, password, description) {
    console.log(`\n${'='.repeat(70)}`);
    console.log(`📋 تست کاربر: ${description} (${username})`);
    console.log(`${'='.repeat(70)}`);
    
    try {
        console.log(`\n🔐 در حال تست ورود...`);
        console.log(`   Username: ${username}`);
        console.log(`   Password: ${password.substring(0, 3)}***`);
        
        const response = await axios.post(`${BASE_URL}/api/expert/auth/login`, {
            username: username,
            password: password
        }, {
            headers: {
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:5173'
            },
            timeout: 10000
        });
        
        if (response.data.success && response.data.expert && response.data.tokens) {
            console.log(`\n✅ ورود موفق!`);
            console.log(`   - نام کاربری: ${response.data.expert.username}`);
            console.log(`   - نام کامل: ${response.data.expert.full_name}`);
            console.log(`   - نقش: ${response.data.expert.role}`);
            console.log(`   - ایمیل: ${response.data.expert.email || 'ندارد'}`);
            console.log(`   - Token: ${response.data.tokens.access_token.substring(0, 20)}...`);
            
            return {
                success: true,
                username: username,
                user: response.data.expert,
                tokens: response.data.tokens
            };
        } else {
            console.log(`\n❌ پاسخ نامعتبر از سرور`);
            console.log(`   Response:`, JSON.stringify(response.data, null, 2));
            return {
                success: false,
                username: username,
                error: 'Invalid response structure'
            };
        }
    } catch (error) {
        if (error.response) {
            // Server responded with error
            const status = error.response.status;
            const errorData = error.response.data;
            
            console.log(`\n❌ ورود ناموفق!`);
            console.log(`   Status: ${status}`);
            console.log(`   Error: ${errorData.error || errorData.message || 'Unknown error'}`);
            
            if (status === 401) {
                console.log(`\n💡 احتمالاً یکی از مشکلات زیر وجود دارد:`);
                console.log(`   1. کاربر ${username} در دیتابیس وجود ندارد`);
                console.log(`   2. رمز عبور اشتباه است`);
                console.log(`   3. کاربر غیرفعال است (is_active = false)`);
                console.log(`\n💡 راه حل:`);
                console.log(`   - برای ایجاد کاربر admin: python backend/create_admin.py`);
                console.log(`   - برای ایجاد کاربر expert: python backend/seed_experts.py`);
            }
            
            return {
                success: false,
                username: username,
                error: errorData.error || errorData.message || `HTTP ${status}`,
                status: status
            };
        } else if (error.request) {
            // Request made but no response
            console.log(`\n❌ خطا در اتصال به سرور`);
            console.log(`   Error: ${error.message}`);
            console.log(`\n💡 مطمئن شوید که backend در حال اجرا است:`);
            console.log(`   python backend/wsgi.py`);
            console.log(`   یا`);
            console.log(`   flask run`);
            
            return {
                success: false,
                username: username,
                error: `Connection error: ${error.message}`
            };
        } else {
            // Error in request setup
            console.log(`\n❌ خطا در تنظیمات درخواست`);
            console.log(`   Error: ${error.message}`);
            
            return {
                success: false,
                username: username,
                error: error.message
            };
        }
    }
}

async function main() {
    console.log(`${'='.repeat(70)}`);
    console.log(`🧪 تست ورود کاربران (Expert و Admin)`);
    console.log(`${'='.repeat(70)}`);
    console.log(`\n🌐 Backend URL: ${BASE_URL}`);
    console.log(`\n⚠️  مطمئن شوید که backend در حال اجرا است!`);
    
    const results = [];
    
    for (const cred of TEST_CREDENTIALS) {
        const result = await testLogin(
            cred.username,
            cred.password,
            cred.description
        );
        results.push(result);
        
        // Small delay between tests
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    // Summary
    console.log(`\n${'='.repeat(70)}`);
    console.log(`📊 خلاصه نتایج`);
    console.log(`${'='.repeat(70)}`);
    
    const successCount = results.filter(r => r.success).length;
    const totalCount = results.length;
    
    for (const result of results) {
        const status = result.success ? '✅ موفق' : '❌ ناموفق';
        console.log(`\n   ${status} - ${result.username}`);
        if (!result.success) {
            console.log(`      خطا: ${result.error}`);
            if (result.status) {
                console.log(`      Status: ${result.status}`);
            }
        } else {
            console.log(`      نقش: ${result.user.role}`);
            console.log(`      نام: ${result.user.full_name}`);
        }
    }
    
    console.log(`\n${'='.repeat(70)}`);
    console.log(`📈 نتیجه کلی: ${successCount}/${totalCount} تست موفق`);
    console.log(`${'='.repeat(70)}`);
    
    if (successCount === totalCount) {
        console.log(`\n✅ همه تست‌ها موفق بودند!`);
        console.log(`\n💡 می‌توانید با این اطلاعات وارد سیستم شوید:`);
        for (const cred of TEST_CREDENTIALS) {
            console.log(`   - ${cred.description}: ${cred.username} / ${cred.password}`);
        }
        process.exit(0);
    } else {
        console.log(`\n❌ برخی تست‌ها ناموفق بودند!`);
        console.log(`\n💡 برای رفع مشکل:`);
        console.log(`   1. مطمئن شوید backend در حال اجرا است`);
        console.log(`   2. کاربران را ایجاد کنید:`);
        console.log(`      - python backend/create_admin.py (برای admin)`);
        console.log(`      - python backend/seed_experts.py (برای expert)`);
        console.log(`   3. دوباره تست کنید`);
        process.exit(1);
    }
}

// Run the test
main().catch(error => {
    console.error('\n💥 خطای غیرمنتظره:', error.message);
    if (error.stack) {
        console.error(error.stack);
    }
    process.exit(1);
});
