#!/usr/bin/env python3
"""
Comprehensive test for expert console request details functionality.
Tests GET /api/expert/requests/{id} endpoint with timeline, logs, and messages.
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

# Import Flask app and database models
from backend import create_app
from backend.models import (
    ShipmentRequest, ExpertUser, ExpertConsoleLog, ExpertConsoleMessage,
    ExpertConsoleNotification, Province, County, City
)
from backend.extensions import db

class ExpertRequestDetailsTester:
    """Test expert console request details functionality."""
    
    def __init__(self):
        self.app = create_app()
        self.base_url = "http://localhost:5000"
        self.test_data = {}
        self.results = []
        
    def log_result(self, test_name: str, success: bool, message: str, data: Any = None):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if data and not success:
            print(f"   Data: {json.dumps(data, indent=2, default=str)}")
    
    def setup_test_data(self):
        """Set up test data for request details testing."""
        with self.app.app_context():
            try:
                # Create test expert user
                expert = ExpertUser(
                    username="test_expert_details",
                    password_hash="hashed_password",
                    full_name="Test Expert Details",
                    email="test_details@example.com",
                    role="expert",
                    is_active=True
                )
                db.session.add(expert)
                db.session.flush()
                
                # Get or create test provinces, counties, and cities
                province1 = Province.query.filter_by(name_fa="تهران").first()
                if not province1:
                    province1 = Province(name_fa="تهران", code="TH")
                    db.session.add(province1)
                    db.session.flush()
                
                province2 = Province.query.filter_by(name_fa="اصفهان").first()
                if not province2:
                    province2 = Province(name_fa="اصفهان", code="ES")
                    db.session.add(province2)
                    db.session.flush()
                
                county1 = County.query.filter_by(name_fa="تهران", province_id=province1.id).first()
                if not county1:
                    county1 = County(name_fa="تهران", province_id=province1.id)
                    db.session.add(county1)
                    db.session.flush()
                
                county2 = County.query.filter_by(name_fa="اصفهان", province_id=province2.id).first()
                if not county2:
                    county2 = County(name_fa="اصفهان", province_id=province2.id)
                    db.session.add(county2)
                    db.session.flush()
                
                city1 = City.query.filter_by(name_fa="تهران", county_id=county1.id).first()
                if not city1:
                    city1 = City(name_fa="تهران", county_id=county1.id, province_id=province1.id)
                    db.session.add(city1)
                    db.session.flush()
                
                city2 = City.query.filter_by(name_fa="اصفهان", county_id=county2.id).first()
                if not city2:
                    city2 = City(name_fa="اصفهان", county_id=county2.id, province_id=province2.id)
                    db.session.add(city2)
                    db.session.flush()
                
                # Create test shipment request
                shipment_request = ShipmentRequest(
                    contact_phone="09123456789",
                    customer_first_name="علی",
                    customer_last_name="احمدی",
                    origin_province_id=province1.id,
                    origin_county_id=county1.id,
                    origin_city_id=city1.id,
                    dest_province_id=province2.id,
                    dest_county_id=county2.id,
                    dest_city_id=city2.id,
                    transport_method="truck",
                    cargo_description="محصولات الکترونیکی",
                    cargo_weight=100.5,
                    cargo_volume=2.3,
                    cargo_value=5000000,
                    special_instructions="مراقبت ویژه",
                    pickup_date=datetime.now().date() + timedelta(days=1),
                    delivery_date=datetime.now().date() + timedelta(days=3),
                    status="assigned",
                    assigned_to=expert.id,
                    priority="high",
                    sla_due_at=datetime.now() + timedelta(hours=1),
                    has_unread_for_assignee=True
                )
                db.session.add(shipment_request)
                db.session.flush()
                
                # Create timeline logs
                log1 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    action="created",
                    old_status=None,
                    new_status="new",
                    note="درخواست ایجاد شد",
                    ip_address="127.0.0.1",
                    created_at=datetime.now() - timedelta(hours=2)
                )
                
                log2 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    action="assignment",
                    old_status="new",
                    new_status="assigned",
                    note="ارجاع به کارشناس",
                    ip_address="127.0.0.1",
                    created_at=datetime.now() - timedelta(hours=1)
                )
                
                log3 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    action="status_change",
                    old_status="assigned",
                    new_status="in_progress",
                    note="شروع کار بر روی درخواست",
                    ip_address="127.0.0.1",
                    created_at=datetime.now() - timedelta(minutes=30)
                )
                
                db.session.add(log1)
                db.session.add(log2)
                db.session.add(log3)
                
                # Create messages
                message1 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    message_type="internal_note",
                    subject="یادداشت داخلی",
                    content="این یک یادداشت داخلی برای همکاران است",
                    is_read_by_customer=False,
                    created_at=datetime.now() - timedelta(minutes=45)
                )
                
                message2 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    message_type="customer_message",
                    subject="پیام به مشتری",
                    content="درخواست شما در حال بررسی است",
                    is_read_by_customer=False,
                    customer_response=None,
                    created_at=datetime.now() - timedelta(minutes=20)
                )
                
                message3 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert.id,
                    message_type="customer_message",
                    subject="پاسخ مشتری",
                    content="لطفاً قیمت را اعلام کنید",
                    is_read_by_customer=True,
                    customer_response="ممنون از اطلاع‌رسانی",
                    created_at=datetime.now() - timedelta(minutes=10)
                )
                
                db.session.add(message1)
                db.session.add(message2)
                db.session.add(message3)
                
                # Create notification
                notification = ExpertConsoleNotification(
                    expert_user_id=expert.id,
                    shipment_request_id=shipment_request.id,
                    notification_type="assignment",
                    title="ارجاع درخواست جدید",
                    message=f"درخواست {shipment_request.id} به شما ارجاع داده شد",
                    is_read=False,
                    created_at=datetime.now() - timedelta(hours=1)
                )
                db.session.add(notification)
                
                db.session.commit()
                
                self.test_data = {
                    "expert_id": expert.id,
                    "expert_username": expert.username,
                    "request_id": shipment_request.id,
                    "province1_id": province1.id,
                    "province2_id": province2.id,
                    "county1_id": county1.id,
                    "county2_id": county2.id,
                    "city1_id": city1.id,
                    "city2_id": city2.id
                }
                
                self.log_result("setup_test_data", True, "Test data created successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("setup_test_data", False, f"Failed to create test data: {str(e)}")
                raise
    
    def test_request_details_basic(self):
        """Test basic request details retrieval."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate basic structure
                required_fields = [
                    "id", "tracking_number", "status", "priority", "created_at",
                    "customer", "route", "cargo", "timeline", "messages"
                ]
                
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_result(
                        "test_request_details_basic", True,
                        "Basic request details retrieved successfully",
                        {
                            "request_id": data["id"],
                            "tracking_number": data["tracking_number"],
                            "status": data["status"],
                            "timeline_count": len(data["timeline"]),
                            "messages_count": len(data["messages"])
                        }
                    )
                else:
                    self.log_result(
                        "test_request_details_basic", False,
                        f"Missing required fields: {missing_fields}",
                        data
                    )
            else:
                self.log_result(
                    "test_request_details_basic", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_basic", False, f"Exception: {str(e)}")
    
    def test_request_details_customer_info(self):
        """Test customer information in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                customer = data.get("customer", {})
                
                expected_customer_fields = ["first_name", "last_name", "phone", "full_name"]
                missing_fields = [field for field in expected_customer_fields if field not in customer]
                
                if not missing_fields:
                    # Validate customer data
                    if (customer["first_name"] == "علی" and 
                        customer["last_name"] == "احمدی" and
                        customer["phone"] == "09123456789" and
                        customer["full_name"] == "علی احمدی"):
                        
                        self.log_result(
                            "test_request_details_customer_info", True,
                            "Customer information is correct",
                            customer
                        )
                    else:
                        self.log_result(
                            "test_request_details_customer_info", False,
                            "Customer information doesn't match expected values",
                            customer
                        )
                else:
                    self.log_result(
                        "test_request_details_customer_info", False,
                        f"Missing customer fields: {missing_fields}",
                        customer
                    )
            else:
                self.log_result(
                    "test_request_details_customer_info", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_customer_info", False, f"Exception: {str(e)}")
    
    def test_request_details_route_info(self):
        """Test route information in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                route = data.get("route", {})
                
                # Validate route structure
                if "origin" in route and "destination" in route:
                    origin = route["origin"]
                    destination = route["destination"]
                    
                    origin_fields = ["province", "county", "city"]
                    dest_fields = ["province", "county", "city"]
                    
                    origin_complete = all(field in origin for field in origin_fields)
                    dest_complete = all(field in destination for field in dest_fields)
                    
                    if origin_complete and dest_complete:
                        self.log_result(
                            "test_request_details_route_info", True,
                            "Route information is complete",
                            {
                                "origin": origin,
                                "destination": destination
                            }
                        )
                    else:
                        self.log_result(
                            "test_request_details_route_info", False,
                            "Route information is incomplete",
                            route
                        )
                else:
                    self.log_result(
                        "test_request_details_route_info", False,
                        "Missing origin or destination in route",
                        route
                    )
            else:
                self.log_result(
                    "test_request_details_route_info", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_route_info", False, f"Exception: {str(e)}")
    
    def test_request_details_cargo_info(self):
        """Test cargo information in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                cargo = data.get("cargo", {})
                
                expected_cargo_fields = [
                    "description", "weight", "volume", "value", "special_instructions"
                ]
                missing_fields = [field for field in expected_cargo_fields if field not in cargo]
                
                if not missing_fields:
                    # Validate cargo data
                    if (cargo["description"] == "محصولات الکترونیکی" and
                        cargo["weight"] == 100.5 and
                        cargo["volume"] == 2.3 and
                        cargo["value"] == 5000000 and
                        cargo["special_instructions"] == "مراقبت ویژه"):
                        
                        self.log_result(
                            "test_request_details_cargo_info", True,
                            "Cargo information is correct",
                            cargo
                        )
                    else:
                        self.log_result(
                            "test_request_details_cargo_info", False,
                            "Cargo information doesn't match expected values",
                            cargo
                        )
                else:
                    self.log_result(
                        "test_request_details_cargo_info", False,
                        f"Missing cargo fields: {missing_fields}",
                        cargo
                    )
            else:
                self.log_result(
                    "test_request_details_cargo_info", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_cargo_info", False, f"Exception: {str(e)}")
    
    def test_request_details_timeline(self):
        """Test timeline/logs functionality in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                
                if len(timeline) >= 3:  # We created 3 logs
                    # Validate timeline structure
                    required_log_fields = [
                        "id", "action", "old_status", "new_status", 
                        "note", "created_at", "created_by"
                    ]
                    
                    valid_logs = 0
                    for log in timeline:
                        if all(field in log for field in required_log_fields):
                            valid_logs += 1
                    
                    if valid_logs == len(timeline):
                        # Check if logs are in descending order (newest first)
                        timestamps = [datetime.fromisoformat(log["created_at"].replace('Z', '+00:00')) 
                                    for log in timeline]
                        is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                        
                        if is_sorted:
                            self.log_result(
                                "test_request_details_timeline", True,
                                f"Timeline with {len(timeline)} logs is valid and sorted",
                                {
                                    "log_count": len(timeline),
                                    "actions": [log["action"] for log in timeline]
                                }
                            )
                        else:
                            self.log_result(
                                "test_request_details_timeline", False,
                                "Timeline logs are not in descending order",
                                timeline
                            )
                    else:
                        self.log_result(
                            "test_request_details_timeline", False,
                            f"Only {valid_logs}/{len(timeline)} logs have valid structure",
                            timeline
                        )
                else:
                    self.log_result(
                        "test_request_details_timeline", False,
                        f"Expected at least 3 logs, got {len(timeline)}",
                        timeline
                    )
            else:
                self.log_result(
                    "test_request_details_timeline", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_timeline", False, f"Exception: {str(e)}")
    
    def test_request_details_messages(self):
        """Test messages functionality in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                if len(messages) >= 3:  # We created 3 messages
                    # Validate message structure
                    required_message_fields = [
                        "id", "type", "subject", "content", "is_read_by_customer",
                        "customer_response", "created_at", "created_by"
                    ]
                    
                    valid_messages = 0
                    message_types = []
                    for message in messages:
                        if all(field in message for field in required_message_fields):
                            valid_messages += 1
                            message_types.append(message["type"])
                    
                    if valid_messages == len(messages):
                        # Check if messages are in descending order (newest first)
                        timestamps = [datetime.fromisoformat(msg["created_at"].replace('Z', '+00:00')) 
                                    for msg in messages]
                        is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                        
                        if is_sorted:
                            self.log_result(
                                "test_request_details_messages", True,
                                f"Messages with {len(messages)} items are valid and sorted",
                                {
                                    "message_count": len(messages),
                                    "message_types": message_types
                                }
                            )
                        else:
                            self.log_result(
                                "test_request_details_messages", False,
                                "Messages are not in descending order",
                                messages
                            )
                    else:
                        self.log_result(
                            "test_request_details_messages", False,
                            f"Only {valid_messages}/{len(messages)} messages have valid structure",
                            messages
                        )
                else:
                    self.log_result(
                        "test_request_details_messages", False,
                        f"Expected at least 3 messages, got {len(messages)}",
                        messages
                    )
            else:
                self.log_result(
                    "test_request_details_messages", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_messages", False, f"Exception: {str(e)}")
    
    def test_request_details_assignment_info(self):
        """Test assignment information in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                assigned_to = data.get("assigned_to")
                
                if assigned_to:
                    required_assignment_fields = ["id", "name", "username"]
                    missing_fields = [field for field in required_assignment_fields if field not in assigned_to]
                    
                    if not missing_fields:
                        if (assigned_to["id"] == self.test_data["expert_id"] and
                            assigned_to["name"] == "Test Expert Details" and
                            assigned_to["username"] == "test_expert_details"):
                            
                            self.log_result(
                                "test_request_details_assignment_info", True,
                                "Assignment information is correct",
                                assigned_to
                            )
                        else:
                            self.log_result(
                                "test_request_details_assignment_info", False,
                                "Assignment information doesn't match expected values",
                                assigned_to
                            )
                    else:
                        self.log_result(
                            "test_request_details_assignment_info", False,
                            f"Missing assignment fields: {missing_fields}",
                            assigned_to
                        )
                else:
                    self.log_result(
                        "test_request_details_assignment_info", False,
                        "No assignment information found",
                        data
                    )
            else:
                self.log_result(
                    "test_request_details_assignment_info", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_assignment_info", False, f"Exception: {str(e)}")
    
    def test_request_details_sla_status(self):
        """Test SLA status calculation in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                sla_status = data.get("sla_status")
                sla_due_at = data.get("sla_due_at")
                
                if sla_status and sla_due_at:
                    # Since we set SLA due at 1 hour from now, it should be "due_soon"
                    if sla_status in ["on_time", "due_soon", "overdue"]:
                        self.log_result(
                            "test_request_details_sla_status", True,
                            f"SLA status is valid: {sla_status}",
                            {
                                "sla_status": sla_status,
                                "sla_due_at": sla_due_at
                            }
                        )
                    else:
                        self.log_result(
                            "test_request_details_sla_status", False,
                            f"Invalid SLA status: {sla_status}",
                            data
                        )
                else:
                    self.log_result(
                        "test_request_details_sla_status", False,
                        "Missing SLA status or due date",
                        data
                    )
            else:
                self.log_result(
                    "test_request_details_sla_status", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_sla_status", False, f"Exception: {str(e)}")
    
    def test_request_details_not_found(self):
        """Test request details for non-existent request."""
        try:
            url = f"{self.base_url}/api/expert/requests/999999"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 404:
                data = response.json()
                if "error" in data and "یافت نشد" in data["error"]:
                    self.log_result(
                        "test_request_details_not_found", True,
                        "Correctly returns 404 for non-existent request",
                        data
                    )
                else:
                    self.log_result(
                        "test_request_details_not_found", False,
                        "404 response doesn't contain expected error message",
                        data
                    )
            else:
                self.log_result(
                    "test_request_details_not_found", False,
                    f"Expected 404, got {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_not_found", False, f"Exception: {str(e)}")
    
    def test_request_details_dates(self):
        """Test date information in request details."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                dates = data.get("dates", {})
                
                if "pickup_date" in dates and "delivery_date" in dates:
                    pickup_date = dates["pickup_date"]
                    delivery_date = dates["delivery_date"]
                    
                    # Validate date format (ISO format)
                    try:
                        if pickup_date:
                            datetime.fromisoformat(pickup_date.replace('Z', '+00:00'))
                        if delivery_date:
                            datetime.fromisoformat(delivery_date.replace('Z', '+00:00'))
                        
                        self.log_result(
                            "test_request_details_dates", True,
                            "Date information is valid",
                            {
                                "pickup_date": pickup_date,
                                "delivery_date": delivery_date
                            }
                        )
                    except ValueError:
                        self.log_result(
                            "test_request_details_dates", False,
                            "Invalid date format",
                            dates
                        )
                else:
                    self.log_result(
                        "test_request_details_dates", False,
                        "Missing pickup_date or delivery_date",
                        dates
                    )
            else:
                self.log_result(
                    "test_request_details_dates", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_request_details_dates", False, f"Exception: {str(e)}")
    
    def cleanup_test_data(self):
        """Clean up test data."""
        with self.app.app_context():
            try:
                # Delete in reverse order of dependencies
                ExpertConsoleNotification.query.filter_by(expert_user_id=self.test_data["expert_id"]).delete()
                ExpertConsoleMessage.query.filter_by(shipment_request_id=self.test_data["request_id"]).delete()
                ExpertConsoleLog.query.filter_by(shipment_request_id=self.test_data["request_id"]).delete()
                ShipmentRequest.query.filter_by(id=self.test_data["request_id"]).delete()
                ExpertUser.query.filter_by(id=self.test_data["expert_id"]).delete()
                
                # Clean up location data
                City.query.filter(City.id.in_([self.test_data["city1_id"], self.test_data["city2_id"]])).delete()
                County.query.filter(County.id.in_([self.test_data["county1_id"], self.test_data["county2_id"]])).delete()
                Province.query.filter(Province.id.in_([self.test_data["province1_id"], self.test_data["province2_id"]])).delete()
                
                db.session.commit()
                self.log_result("cleanup_test_data", True, "Test data cleaned up successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("cleanup_test_data", False, f"Failed to clean up test data: {str(e)}")
    
    def run_all_tests(self):
        """Run all request details tests."""
        print("🧪 Starting Expert Request Details Tests")
        print("=" * 60)
        
        try:
            # Setup
            self.setup_test_data()
            
            # Run tests
            self.test_request_details_basic()
            self.test_request_details_customer_info()
            self.test_request_details_route_info()
            self.test_request_details_cargo_info()
            self.test_request_details_timeline()
            self.test_request_details_messages()
            self.test_request_details_assignment_info()
            self.test_request_details_sla_status()
            self.test_request_details_dates()
            self.test_request_details_not_found()
            
        finally:
            # Cleanup
            self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        passed = len([r for r in self.results if r["success"]])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [r for r in self.results if not r["success"]]
        if failed_tests:
            print("\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['message']}")
        
        return passed == total


def main():
    """Main function to run the tests."""
    tester = ExpertRequestDetailsTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
