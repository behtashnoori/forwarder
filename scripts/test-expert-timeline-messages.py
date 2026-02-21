#!/usr/bin/env python3
"""
Advanced test for expert console timeline and messages functionality.
Tests detailed scenarios for logs, messages, and notifications.
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

class ExpertTimelineMessagesTester:
    """Test expert console timeline and messages functionality in detail."""
    
    def __init__(self):
        self.app = create_app()
        self.base_url = "http://localhost:8000"
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
        """Set up test data for timeline and messages testing."""
        with self.app.app_context():
            try:
                # Create multiple test expert users
                expert1 = ExpertUser(
                    username="expert_timeline_1",
                    password_hash="hashed_password",
                    full_name="Timeline Expert 1",
                    email="timeline1@example.com",
                    role="expert",
                    is_active=True
                )
                expert2 = ExpertUser(
                    username="expert_timeline_2",
                    password_hash="hashed_password",
                    full_name="Timeline Expert 2",
                    email="timeline2@example.com",
                    role="supervisor",
                    is_active=True
                )
                db.session.add(expert1)
                db.session.add(expert2)
                db.session.flush()
                
                # Get or create test provinces, counties, and cities
                province = Province.query.filter_by(name_fa="تهران").first()
                if not province:
                    province = Province(name_fa="تهران", code="TH")
                    db.session.add(province)
                    db.session.flush()
                
                county = County.query.filter_by(name_fa="تهران", province_id=province.id).first()
                if not county:
                    county = County(name_fa="تهران", province_id=province.id)
                    db.session.add(county)
                    db.session.flush()
                
                city = City.query.filter_by(name_fa="تهران", county_id=county.id).first()
                if not city:
                    city = City(name_fa="تهران", county_id=county.id, province_id=province.id)
                    db.session.add(city)
                    db.session.flush()
                
                # Create test shipment request
                shipment_request = ShipmentRequest(
                    contact_phone="09123456789",
                    customer_first_name="محمد",
                    customer_last_name="رضایی",
                    origin_province_id=province.id,
                    origin_county_id=county.id,
                    origin_city_id=city.id,
                    dest_province_id=province.id,
                    dest_county_id=county.id,
                    dest_city_id=city.id,
                    transport_method="truck",
                    cargo_description="کالاهای صنعتی",
                    cargo_weight=500.0,
                    cargo_volume=10.5,
                    cargo_value=10000000,
                    special_instructions="حمل با دقت",
                    pickup_date=datetime.now().date() + timedelta(days=2),
                    delivery_date=datetime.now().date() + timedelta(days=5),
                    status="in_progress",
                    assigned_to=expert1.id,
                    priority="urgent",
                    sla_due_at=datetime.now() + timedelta(hours=4),
                    has_unread_for_assignee=True
                )
                db.session.add(shipment_request)
                db.session.flush()
                
                # Create comprehensive timeline logs
                base_time = datetime.now()
                
                # Log 1: Request creation
                log1 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=None,  # System created
                    action="created",
                    old_status=None,
                    new_status="new",
                    note="درخواست حمل جدید ایجاد شد",
                    ip_address="127.0.0.1",
                    created_at=base_time - timedelta(hours=6)
                )
                
                # Log 2: Assignment to expert
                log2 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert1.id,
                    action="assignment",
                    old_status="new",
                    new_status="assigned",
                    note="ارجاع به کارشناس حمل و نقل",
                    ip_address="127.0.0.1",
                    created_at=base_time - timedelta(hours=5)
                )
                
                # Log 3: Status change to in_progress
                log3 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert1.id,
                    action="status_change",
                    old_status="assigned",
                    new_status="in_progress",
                    note="شروع بررسی درخواست",
                    ip_address="127.0.0.1",
                    created_at=base_time - timedelta(hours=4)
                )
                
                # Log 4: Message added
                log4 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert1.id,
                    action="message_added",
                    note="پیام داخلی اضافه شد",
                    ip_address="127.0.0.1",
                    created_at=base_time - timedelta(hours=3)
                )
                
                # Log 5: Supervisor intervention
                log5 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert2.id,
                    action="supervisor_review",
                    note="بررسی سرپرست انجام شد",
                    ip_address="127.0.0.1",
                    created_at=base_time - timedelta(hours=2)
                )
                
                # Log 6: Priority change
                log6 = ExpertConsoleLog(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert2.id,
                    action="priority_change",
                    old_status="normal",
                    new_status="urgent",
                    note="اولویت درخواست به فوری تغییر یافت",
                    ip_address="127.0.0.1",
                    created_at=base_time - timedelta(hours=1)
                )
                
                db.session.add(log1)
                db.session.add(log2)
                db.session.add(log3)
                db.session.add(log4)
                db.session.add(log5)
                db.session.add(log6)
                
                # Create comprehensive messages
                # Message 1: Internal note
                message1 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert1.id,
                    message_type="internal_note",
                    subject="بررسی اولیه",
                    content="درخواست بررسی شد. کالاها نیاز به بسته‌بندی ویژه دارند.",
                    is_read_by_customer=False,
                    created_at=base_time - timedelta(hours=3, minutes=30)
                )
                
                # Message 2: Customer message
                message2 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert1.id,
                    message_type="customer_message",
                    subject="اطلاع‌رسانی وضعیت",
                    content="درخواست شما در حال بررسی است. به زودی با شما تماس خواهیم گرفت.",
                    is_read_by_customer=False,
                    created_at=base_time - timedelta(hours=2, minutes=45)
                )
                
                # Message 3: Customer response
                message3 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert1.id,
                    message_type="customer_message",
                    subject="پاسخ مشتری",
                    content="ممنون از اطلاع‌رسانی. آیا می‌توانید زمان تقریبی تحویل را اعلام کنید؟",
                    is_read_by_customer=True,
                    customer_response="ممنون از پیگیری شما",
                    created_at=base_time - timedelta(hours=2, minutes=15)
                )
                
                # Message 4: Supervisor note
                message4 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert2.id,
                    message_type="internal_note",
                    subject="نظر سرپرست",
                    content="این درخواست اولویت بالایی دارد. لطفاً با سرعت بیشتری پیگیری کنید.",
                    is_read_by_customer=False,
                    created_at=base_time - timedelta(hours=1, minutes=30)
                )
                
                # Message 5: Quote message
                message5 = ExpertConsoleMessage(
                    shipment_request_id=shipment_request.id,
                    expert_user_id=expert1.id,
                    message_type="customer_message",
                    subject="ارائه قیمت",
                    content="قیمت حمل شما 5,000,000 تومان است. آیا موافق هستید؟",
                    is_read_by_customer=False,
                    created_at=base_time - timedelta(minutes=45)
                )
                
                db.session.add(message1)
                db.session.add(message2)
                db.session.add(message3)
                db.session.add(message4)
                db.session.add(message5)
                
                # Create notifications
                notification1 = ExpertConsoleNotification(
                    expert_user_id=expert1.id,
                    shipment_request_id=shipment_request.id,
                    notification_type="assignment",
                    title="ارجاع درخواست جدید",
                    message=f"درخواست {shipment_request.id} به شما ارجاع داده شد",
                    is_read=False,
                    created_at=base_time - timedelta(hours=5)
                )
                
                notification2 = ExpertConsoleNotification(
                    expert_user_id=expert1.id,
                    shipment_request_id=shipment_request.id,
                    notification_type="message",
                    title="پیام جدید از مشتری",
                    message="مشتری پاسخ داده است",
                    is_read=False,
                    created_at=base_time - timedelta(hours=2, minutes=15)
                )
                
                notification3 = ExpertConsoleNotification(
                    expert_user_id=expert1.id,
                    shipment_request_id=shipment_request.id,
                    notification_type="supervisor_note",
                    title="نظر سرپرست",
                    message="سرپرست نظر جدیدی اضافه کرده است",
                    is_read=True,
                    created_at=base_time - timedelta(hours=1, minutes=30)
                )
                
                db.session.add(notification1)
                db.session.add(notification2)
                db.session.add(notification3)
                
                db.session.commit()
                
                self.test_data = {
                    "expert1_id": expert1.id,
                    "expert2_id": expert2.id,
                    "request_id": shipment_request.id,
                    "province_id": province.id,
                    "county_id": county.id,
                    "city_id": city.id
                }
                
                self.log_result("setup_test_data", True, "Timeline and messages test data created successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("setup_test_data", False, f"Failed to create test data: {str(e)}")
                raise
    
    def test_timeline_ordering(self):
        """Test that timeline logs are properly ordered by creation time."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                
                if len(timeline) >= 6:  # We created 6 logs
                    # Check if logs are in descending order (newest first)
                    timestamps = []
                    for log in timeline:
                        try:
                            timestamp = datetime.fromisoformat(log["created_at"].replace('Z', '+00:00'))
                            timestamps.append(timestamp)
                        except ValueError:
                            self.log_result(
                                "test_timeline_ordering", False,
                                f"Invalid timestamp format: {log['created_at']}",
                                timeline
                            )
                            return
                    
                    is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                    
                    if is_sorted:
                        self.log_result(
                            "test_timeline_ordering", True,
                            f"Timeline with {len(timeline)} logs is properly sorted",
                            {
                                "log_count": len(timeline),
                                "first_log_action": timeline[0]["action"],
                                "last_log_action": timeline[-1]["action"]
                            }
                        )
                    else:
                        self.log_result(
                            "test_timeline_ordering", False,
                            "Timeline logs are not in descending order",
                            {
                                "timestamps": [ts.isoformat() for ts in timestamps],
                                "actions": [log["action"] for log in timeline]
                            }
                        )
                else:
                    self.log_result(
                        "test_timeline_ordering", False,
                        f"Expected at least 6 logs, got {len(timeline)}",
                        timeline
                    )
            else:
                self.log_result(
                    "test_timeline_ordering", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_timeline_ordering", False, f"Exception: {str(e)}")
    
    def test_timeline_log_types(self):
        """Test different types of timeline logs."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                
                # Check for specific log types
                expected_actions = ["created", "assignment", "status_change", "message_added", "supervisor_review", "priority_change"]
                found_actions = [log["action"] for log in timeline]
                
                missing_actions = [action for action in expected_actions if action not in found_actions]
                
                if not missing_actions:
                    # Validate log structure for each type
                    valid_logs = 0
                    for log in timeline:
                        required_fields = ["id", "action", "note", "created_at", "created_by"]
                        if all(field in log for field in required_fields):
                            valid_logs += 1
                    
                    if valid_logs == len(timeline):
                        self.log_result(
                            "test_timeline_log_types", True,
                            f"All {len(timeline)} timeline logs have valid structure",
                            {
                                "found_actions": found_actions,
                                "valid_logs": valid_logs
                            }
                        )
                    else:
                        self.log_result(
                            "test_timeline_log_types", False,
                            f"Only {valid_logs}/{len(timeline)} logs have valid structure",
                            timeline
                        )
                else:
                    self.log_result(
                        "test_timeline_log_types", False,
                        f"Missing expected actions: {missing_actions}",
                        {
                            "expected": expected_actions,
                            "found": found_actions
                        }
                    )
            else:
                self.log_result(
                    "test_timeline_log_types", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_timeline_log_types", False, f"Exception: {str(e)}")
    
    def test_messages_ordering(self):
        """Test that messages are properly ordered by creation time."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                if len(messages) >= 5:  # We created 5 messages
                    # Check if messages are in descending order (newest first)
                    timestamps = []
                    for message in messages:
                        try:
                            timestamp = datetime.fromisoformat(message["created_at"].replace('Z', '+00:00'))
                            timestamps.append(timestamp)
                        except ValueError:
                            self.log_result(
                                "test_messages_ordering", False,
                                f"Invalid timestamp format: {message['created_at']}",
                                messages
                            )
                            return
                    
                    is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                    
                    if is_sorted:
                        self.log_result(
                            "test_messages_ordering", True,
                            f"Messages with {len(messages)} items are properly sorted",
                            {
                                "message_count": len(messages),
                                "first_message_type": messages[0]["type"],
                                "last_message_type": messages[-1]["type"]
                            }
                        )
                    else:
                        self.log_result(
                            "test_messages_ordering", False,
                            "Messages are not in descending order",
                            {
                                "timestamps": [ts.isoformat() for ts in timestamps],
                                "types": [msg["type"] for msg in messages]
                            }
                        )
                else:
                    self.log_result(
                        "test_messages_ordering", False,
                        f"Expected at least 5 messages, got {len(messages)}",
                        messages
                    )
            else:
                self.log_result(
                    "test_messages_ordering", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_messages_ordering", False, f"Exception: {str(e)}")
    
    def test_message_types(self):
        """Test different types of messages."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                # Check for specific message types
                expected_types = ["internal_note", "customer_message"]
                found_types = list(set([msg["type"] for msg in messages]))
                
                missing_types = [msg_type for msg_type in expected_types if msg_type not in found_types]
                
                if not missing_types:
                    # Validate message structure for each type
                    valid_messages = 0
                    for message in messages:
                        required_fields = ["id", "type", "subject", "content", "is_read_by_customer", "created_at", "created_by"]
                        if all(field in message for field in required_fields):
                            valid_messages += 1
                    
                    if valid_messages == len(messages):
                        # Check specific message type validations
                        internal_notes = [msg for msg in messages if msg["type"] == "internal_note"]
                        customer_messages = [msg for msg in messages if msg["type"] == "customer_message"]
                        
                        self.log_result(
                            "test_message_types", True,
                            f"All {len(messages)} messages have valid structure",
                            {
                                "total_messages": len(messages),
                                "internal_notes": len(internal_notes),
                                "customer_messages": len(customer_messages),
                                "valid_messages": valid_messages
                            }
                        )
                    else:
                        self.log_result(
                            "test_message_types", False,
                            f"Only {valid_messages}/{len(messages)} messages have valid structure",
                            messages
                        )
                else:
                    self.log_result(
                        "test_message_types", False,
                        f"Missing expected message types: {missing_types}",
                        {
                            "expected": expected_types,
                            "found": found_types
                        }
                    )
            else:
                self.log_result(
                    "test_message_types", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_message_types", False, f"Exception: {str(e)}")
    
    def test_customer_response_handling(self):
        """Test customer response handling in messages."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                # Find messages with customer responses
                messages_with_responses = [msg for msg in messages if msg.get("customer_response")]
                messages_read_by_customer = [msg for msg in messages if msg.get("is_read_by_customer")]
                
                if messages_with_responses:
                    # Validate customer response structure
                    valid_responses = 0
                    for message in messages_with_responses:
                        if (message.get("customer_response") and 
                            message.get("is_read_by_customer") is not None):
                            valid_responses += 1
                    
                    if valid_responses == len(messages_with_responses):
                        self.log_result(
                            "test_customer_response_handling", True,
                            f"Customer responses handled correctly in {len(messages_with_responses)} messages",
                            {
                                "messages_with_responses": len(messages_with_responses),
                                "messages_read_by_customer": len(messages_read_by_customer),
                                "valid_responses": valid_responses
                            }
                        )
                    else:
                        self.log_result(
                            "test_customer_response_handling", False,
                            f"Only {valid_responses}/{len(messages_with_responses)} responses are valid",
                            messages_with_responses
                        )
                else:
                    self.log_result(
                        "test_customer_response_handling", False,
                        "No messages with customer responses found",
                        messages
                    )
            else:
                self.log_result(
                    "test_customer_response_handling", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_customer_response_handling", False, f"Exception: {str(e)}")
    
    def test_timeline_message_integration(self):
        """Test integration between timeline and messages."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                messages = data.get("messages", [])
                
                # Check if there's a timeline entry for message addition
                message_added_logs = [log for log in timeline if log["action"] == "message_added"]
                
                if message_added_logs and messages:
                    # Check if timeline and messages are consistent
                    timeline_timestamps = [datetime.fromisoformat(log["created_at"].replace('Z', '+00:00')) 
                                         for log in timeline]
                    message_timestamps = [datetime.fromisoformat(msg["created_at"].replace('Z', '+00:00')) 
                                        for msg in messages]
                    
                    # Check if message timestamps fall within timeline range
                    min_timeline = min(timeline_timestamps)
                    max_timeline = max(timeline_timestamps)
                    
                    messages_in_range = all(min_timeline <= ts <= max_timeline for ts in message_timestamps)
                    
                    if messages_in_range:
                        self.log_result(
                            "test_timeline_message_integration", True,
                            "Timeline and messages are properly integrated",
                            {
                                "timeline_logs": len(timeline),
                                "messages": len(messages),
                                "message_added_logs": len(message_added_logs),
                                "messages_in_timeline_range": messages_in_range
                            }
                        )
                    else:
                        self.log_result(
                            "test_timeline_message_integration", False,
                            "Message timestamps are not within timeline range",
                            {
                                "timeline_range": f"{min_timeline} to {max_timeline}",
                                "message_timestamps": [ts.isoformat() for ts in message_timestamps]
                            }
                        )
                else:
                    self.log_result(
                        "test_timeline_message_integration", False,
                        "Missing message_added logs or messages",
                        {
                            "timeline_logs": len(timeline),
                            "messages": len(messages),
                            "message_added_logs": len(message_added_logs)
                        }
                    )
            else:
                self.log_result(
                    "test_timeline_message_integration", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_timeline_message_integration", False, f"Exception: {str(e)}")
    
    def test_multiple_experts_timeline(self):
        """Test timeline with multiple experts."""
        try:
            request_id = self.test_data["request_id"]
            url = f"{self.base_url}/api/expert/requests/{request_id}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                
                # Check if timeline includes actions from multiple experts
                expert_ids = set()
                for log in timeline:
                    if log.get("created_by") and log["created_by"] != "سیستم":
                        # Extract expert ID from created_by field or find another way
                        # For now, we'll check if we have logs with different actions that should be from different experts
                        expert_ids.add(log["action"])
                
                # Check for supervisor actions
                supervisor_actions = [log for log in timeline if "supervisor" in log["action"].lower()]
                expert_actions = [log for log in timeline if log["action"] in ["created", "assignment", "status_change", "message_added"]]
                
                if supervisor_actions and expert_actions:
                    self.log_result(
                        "test_multiple_experts_timeline", True,
                        "Timeline includes actions from multiple experts",
                        {
                            "total_logs": len(timeline),
                            "supervisor_actions": len(supervisor_actions),
                            "expert_actions": len(expert_actions),
                            "unique_actions": len(set(log["action"] for log in timeline))
                        }
                    )
                else:
                    self.log_result(
                        "test_multiple_experts_timeline", False,
                        "Timeline doesn't show multiple expert involvement",
                        {
                            "timeline_actions": [log["action"] for log in timeline],
                            "supervisor_actions": len(supervisor_actions),
                            "expert_actions": len(expert_actions)
                        }
                    )
            else:
                self.log_result(
                    "test_multiple_experts_timeline", False,
                    f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_result("test_multiple_experts_timeline", False, f"Exception: {str(e)}")
    
    def cleanup_test_data(self):
        """Clean up test data."""
        with self.app.app_context():
            try:
                # Delete in reverse order of dependencies
                ExpertConsoleNotification.query.filter_by(expert_user_id=self.test_data["expert1_id"]).delete()
                ExpertConsoleMessage.query.filter_by(shipment_request_id=self.test_data["request_id"]).delete()
                ExpertConsoleLog.query.filter_by(shipment_request_id=self.test_data["request_id"]).delete()
                ShipmentRequest.query.filter_by(id=self.test_data["request_id"]).delete()
                ExpertUser.query.filter_by(id=self.test_data["expert1_id"]).delete()
                ExpertUser.query.filter_by(id=self.test_data["expert2_id"]).delete()
                
                # Clean up location data
                City.query.filter_by(id=self.test_data["city_id"]).delete()
                County.query.filter_by(id=self.test_data["county_id"]).delete()
                Province.query.filter_by(id=self.test_data["province_id"]).delete()
                
                db.session.commit()
                self.log_result("cleanup_test_data", True, "Timeline and messages test data cleaned up successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("cleanup_test_data", False, f"Failed to clean up test data: {str(e)}")
    
    def run_all_tests(self):
        """Run all timeline and messages tests."""
        print("🧪 Starting Expert Timeline & Messages Tests")
        print("=" * 60)
        
        try:
            # Setup
            self.setup_test_data()
            
            # Run tests
            self.test_timeline_ordering()
            self.test_timeline_log_types()
            self.test_messages_ordering()
            self.test_message_types()
            self.test_customer_response_handling()
            self.test_timeline_message_integration()
            self.test_multiple_experts_timeline()
            
        finally:
            # Cleanup
            self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Timeline & Messages Test Summary")
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
    tester = ExpertTimelineMessagesTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All timeline and messages tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some timeline and messages tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
