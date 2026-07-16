# API Documentation

## Overview

This document provides comprehensive API documentation for the Forwarder CRM system.

## Base URL

```
http://localhost:5000/api
```

## Authentication

The API uses JWT (JSON Web Token) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Common Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": { ... }
}
```

## Endpoints

### Health Check

#### GET /health/ping
Check API health status.

**Response:**
```json
{
  "message": "API is running",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Authentication

#### POST /expert/auth/login
Authenticate expert user.

**Request Body:**
```json
{
  "username": "expert",
  "password": "expert123"
}
```

**Response:**
```json
{
  "success": true,
  "expert": {
    "id": 1,
    "username": "expert",
    "full_name": "Expert User",
    "email": "expert@company.com",
    "role": "expert"
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

#### POST /expert/auth/refresh
Rotate the refresh token and return a new access/refresh pair. The submitted refresh token is consumed immediately; replay revokes the affected logical session.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### POST /expert/auth/logout
Logout the current logical session (requires authentication). Its access and refresh tokens become invalid while independent sessions remain valid.

#### POST /expert/auth/logout-all
Revoke all active sessions belonging to the authenticated user. The response contains only an aggregate count and never exposes session identifiers.

### Expert Console

#### GET /expert/requests
Get filtered and paginated shipment requests.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20, max: 100)
- `status` (string): Filter by status
- `assigned_to` (int): Filter by assigned expert
- `priority` (string): Filter by priority
- `search` (string): Search term
- `sort_by` (string): Sort field
- `sort_order` (string): Sort order (asc/desc)

**Response:**
```json
{
  "requests": [
    {
      "id": 1,
      "tracking_number": "SR000001",
      "status": "new",
      "priority": "normal",
      "created_at": "2024-01-01T00:00:00Z",
      "sla_due_at": "2024-01-01T02:00:00Z",
      "sla_status": "on_time",
      "assigned_to": {
        "id": 1,
        "name": "Expert User"
      },
      "customer": {
        "name": "John Doe",
        "phone": "1234567890"
      },
      "route": {
        "origin": {
          "province": "Tehran",
          "county": "Tehran",
          "city": "Tehran"
        },
        "destination": {
          "province": "Isfahan",
          "county": "Isfahan",
          "city": "Isfahan"
        }
      },
      "transport_method": "truck",
      "cargo": {
        "description": "Electronics",
        "weight": 100.5,
        "volume": 2.5,
        "value": 5000
      },
      "has_unread": false
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

#### GET /expert/requests/{id}
Get detailed information about a specific shipment request.

#### POST /expert/requests/{id}/assign
Assign a shipment request to an expert.

**Request Body:**
```json
{
  "expert_id": 1
}
```

#### POST /expert/requests/{id}/status
Update the status of a shipment request.

**Request Body:**
```json
{
  "status": "in_progress",
  "note": "Status change note"
}
```

#### GET /expert/dashboard/kpis
Get KPI data for expert console dashboard.

**Response:**
```json
{
  "counts": {
    "new": 10,
    "in_progress": 5,
    "waiting_for_customer": 3,
    "closed_today": 2
  },
  "sla": {
    "overdue": 1,
    "due_soon": 2
  }
}
```

### CRM Endpoints

#### GET /crm/customers
Get filtered and paginated customers.

**Query Parameters:**
- `page` (int): Page number
- `per_page` (int): Items per page
- `search` (string): Search term
- `customer_type` (string): Filter by customer type
- `status` (string): Filter by status
- `sort_by` (string): Sort field
- `sort_order` (string): Sort order

**Response:**
```json
{
  "customers": [
    {
      "id": 1,
      "name": "John Doe",
      "company_name": "Acme Corp",
      "email": "john@acme.com",
      "phone": "1234567890",
      "customer_type": "customer",
      "status": "active",
      "industry": "Technology",
      "last_contact_at": "2024-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z",
      "total_opportunities": 5,
      "total_activities": 10
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

#### POST /crm/customers
Create a new customer.

**Request Body:**
```json
{
  "company_name": "Acme Corp",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@acme.com",
  "phone": "1234567890",
  "mobile": "0987654321",
  "website": "https://acme.com",
  "industry": "Technology",
  "company_size": "medium",
  "customer_type": "customer",
  "status": "active",
  "source": "website",
  "notes": "Important customer",
  "address": "123 Main St",
  "city": "Tehran",
  "province": "Tehran",
  "postal_code": "12345",
  "country": "Iran"
}
```

#### GET /crm/customers/{id}
Get detailed information about a specific customer.

#### PUT /crm/customers/{id}
Update customer information.

#### GET /crm/opportunities
Get filtered and paginated opportunities.

#### POST /crm/opportunities
Create a new opportunity.

#### GET /crm/activities
Get filtered and paginated activities.

#### POST /crm/activities
Create a new activity.

#### GET /crm/dashboard/kpis
Get CRM dashboard KPIs.

**Response:**
```json
{
  "customers": {
    "total": 100,
    "new_this_month": 10
  },
  "opportunities": {
    "total": 50,
    "open": 30,
    "won": 15,
    "pipeline_value": 1000000
  },
  "activities": {
    "total": 200,
    "completed": 150
  },
  "recent_activities": [
    {
      "id": 1,
      "type": "call",
      "subject": "Customer call",
      "customer_name": "John Doe",
      "expert_name": "Expert User",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |

## Rate Limiting

API requests are rate limited to prevent abuse:
- 100 requests per hour per IP address
- 1000 requests per hour for authenticated users

## Security Headers

The API includes the following security headers:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`

## CORS

Cross-Origin Resource Sharing is configured for:
- Origins: `http://localhost:3000`, `http://localhost:5173`
- Methods: GET, POST, PUT, DELETE, OPTIONS
- Headers: Content-Type, Authorization, X-CSRF-Token

## Examples

### cURL Examples

#### Login
```bash
curl -X POST http://localhost:5000/api/expert/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "expert", "password": "expert123"}'
```

#### Get Customers (with authentication)
```bash
curl -X GET http://localhost:5000/api/crm/customers \
  -H "Authorization: Bearer <your-jwt-token>"
```

#### Create Customer
```bash
curl -X POST http://localhost:5000/api/crm/customers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "1234567890",
    "customer_type": "customer"
  }'
```

### JavaScript Examples

#### Using Fetch API
```javascript
// Login
const loginResponse = await fetch('/api/expert/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'expert',
    password: 'expert123'
  })
});

const loginData = await loginResponse.json();
const token = loginData.tokens.access_token;

// Get customers
const customersResponse = await fetch('/api/crm/customers', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const customersData = await customersResponse.json();
```

#### Using Axios
```javascript
import axios from 'axios';

// Login
const loginResponse = await axios.post('/api/expert/auth/login', {
  username: 'expert',
  password: 'expert123'
});

const token = loginResponse.data.tokens.access_token;

// Set default authorization header
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;

// Get customers
const customersResponse = await axios.get('/api/crm/customers');
```

## Changelog

### Version 1.0.0
- Initial API release
- Authentication system
- Expert console endpoints
- CRM endpoints
- Security improvements
- Performance optimizations
