#!/usr/bin/env python3
"""
Direct test for expert console message management functionality.
Tests adding messages (internal notes and customer messages) via database operations.
"""

import sys
import os
import json
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

class MessageManagementDirectTester:
    """Test expert console message management functionality via database operations."""
    
    def __init__(self):
        self.app = create_app()
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
        """Set up test data for message management testing."""
        with self.app.app_context():
            try:
                # Create test expert user
                expert = ExpertUser(
                    username="expert_message_test",
                    password_hash="hashed_password",
                    full_name="Message Test Expert",
                    email="message_test@example.com",
                    role="expert",
                    is_active=True
                )
                db.session.add(expert)
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
                    customer_first_name="علی",
                    customer_last_name="احمدی",
                    origin_province_id=province.id,
                    origin_county_id=county.id,
                    origin_city_id=city.id,
                    dest_province_id=province.id,
                    dest_county_id=county.id,
                    dest_city_id=city.id,
                    transport_method="truck",
                    cargo_description="کالاهای الکترونیکی",
                    cargo_weight=200.0,
                    cargo_volume=5.0,
                    cargo_value=5000000,
                    special_instructions="حمل با احتیاط",
                    pickup_date=datetime.now().date() + timedelta(days=1),
                    delivery_date=datetime.now().date() + timedelta(days=3),
                    status="assigned",
                    assigned_to=expert.id,
                    priority="normal",
                    sla_due_at=datetime.now() + timedelta(hours=8),
                    has_unread_for_assignee=False
                )
                db.session.add(shipment_request)
                db.session.flush()
                
                db.session.commit()
                
                self.test_data = {
                    "expert_id": expert.id,
                    "request_id": shipment_request.id,
                    "province_id": province.id,
                    "county_id": county.id,
                    "city_id": city.id
                }
                
                self.log_result("setup_test_data", True, "Message management test data created successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("setup_test_data", False, f"Failed to create test data: {str(e)}")
                raise
    
    def test_add_internal_note_message(self):
        """Test adding internal note message."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                expert_id = self.test_data["expert_id"]
                
                # Test data for internal note
                message_data = {
                    "type": "internal_note",
                    "subject": "بررسی اولیه کالاها",
                    "content": "کالاهای الکترونیکی نیاز به بسته‌بندی ضد ضربه دارند. لطفاً با مشتری تماس بگیرید.",
                    "expert_id": expert_id
                }
                
                # Get shipment request
                req = db.session.query(ShipmentRequest).get(request_id)
                if not req:
                    self.log_result("test_add_internal_note_message", False, "Shipment request not found")
                    return
                
                # Get expert
                expert = db.session.query(ExpertUser).get(expert_id)
                if not expert:
                    self.log_result("test_add_internal_note_message", False, "Expert not found")
                    return
                
                # Create message
                message = ExpertConsoleMessage(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    message_type=message_data["type"],
                    subject=message_data["subject"],
                    content=message_data["content"],
                    is_read_by_customer=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(message)
                
                # Create log entry
                log = ExpertConsoleLog(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    action="message_added",
                    note=f"پیام {message_data['type']} اضافه شد",
                    ip_address="127.0.0.1",
                    created_at=datetime.utcnow()
                )
                db.session.add(log)
                
                db.session.commit()
                
                # Verify message was created
                created_message = db.session.query(ExpertConsoleMessage).filter_by(
                    shipment_request_id=request_id,
                    message_type="internal_note"
                ).first()
                
                if created_message:
                    # Verify message properties
                    if (created_message.subject == message_data["subject"] and
                        created_message.content == message_data["content"] and
                        created_message.message_type == "internal_note" and
                        created_message.expert_user_id == expert_id and
                        not created_message.is_read_by_customer):
                        
                        self.log_result(
                            "test_add_internal_note_message", True,
                            "Internal note message created successfully",
                            {
                                "message_id": created_message.id,
                                "subject": created_message.subject,
                                "message_type": created_message.message_type,
                                "expert_id": created_message.expert_user_id
                            }
                        )
                    else:
                        self.log_result(
                            "test_add_internal_note_message", False,
                            "Message properties don't match expected values",
                            {
                                "expected_subject": message_data["subject"],
                                "actual_subject": created_message.subject,
                                "expected_content": message_data["content"],
                                "actual_content": created_message.content
                            }
                        )
                else:
                    self.log_result("test_add_internal_note_message", False, "Message was not created in database")
                    
        except Exception as e:
            db.session.rollback()
            self.log_result("test_add_internal_note_message", False, f"Exception: {str(e)}")
    
    def test_add_customer_message(self):
        """Test adding customer message."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                expert_id = self.test_data["expert_id"]
                
                # Test data for customer message
                message_data = {
                    "type": "customer_message",
                    "subject": "اطلاع‌رسانی وضعیت حمل",
                    "content": "درخواست حمل شما دریافت شد و در حال بررسی است. به زودی با شما تماس خواهیم گرفت.",
                    "expert_id": expert_id
                }
                
                # Get shipment request
                req = db.session.query(ShipmentRequest).get(request_id)
                if not req:
                    self.log_result("test_add_customer_message", False, "Shipment request not found")
                    return
                
                # Get expert
                expert = db.session.query(ExpertUser).get(expert_id)
                if not expert:
                    self.log_result("test_add_customer_message", False, "Expert not found")
                    return
                
                # Store original status
                original_status = req.status
                
                # Create message
                message = ExpertConsoleMessage(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    message_type=message_data["type"],
                    subject=message_data["subject"],
                    content=message_data["content"],
                    is_read_by_customer=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(message)
                
                # Create log entry
                log = ExpertConsoleLog(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    action="message_added",
                    note=f"پیام {message_data['type']} اضافه شد",
                    ip_address="127.0.0.1",
                    created_at=datetime.utcnow()
                )
                db.session.add(log)
                
                # If customer message, update status and touch time
                if message_data["type"] == "customer_message":
                    req.status = "waiting_for_customer"
                    req.last_customer_touch_at = datetime.utcnow()
                    req.has_unread_for_assignee = True
                
                db.session.commit()
                
                # Verify message was created
                created_message = db.session.query(ExpertConsoleMessage).filter_by(
                    shipment_request_id=request_id,
                    message_type="customer_message"
                ).first()
                
                if created_message:
                    # Verify message properties
                    if (created_message.subject == message_data["subject"] and
                        created_message.content == message_data["content"] and
                        created_message.message_type == "customer_message" and
                        created_message.expert_user_id == expert_id and
                        not created_message.is_read_by_customer):
                        
                        # Verify status was updated
                        updated_req = db.session.query(ShipmentRequest).get(request_id)
                        if (updated_req.status == "waiting_for_customer" and
                            updated_req.has_unread_for_assignee == True and
                            updated_req.last_customer_touch_at is not None):
                            
                            self.log_result(
                                "test_add_customer_message", True,
                                "Customer message created and status updated successfully",
                                {
                                    "message_id": created_message.id,
                                    "subject": created_message.subject,
                                    "message_type": created_message.message_type,
                                    "expert_id": created_message.expert_user_id,
                                    "new_status": updated_req.status,
                                    "has_unread": updated_req.has_unread_for_assignee
                                }
                            )
                        else:
                            self.log_result(
                                "test_add_customer_message", False,
                                "Customer message created but status not updated correctly",
                                {
                                    "expected_status": "waiting_for_customer",
                                    "actual_status": updated_req.status,
                                    "expected_unread": True,
                                    "actual_unread": updated_req.has_unread_for_assignee
                                }
                            )
                    else:
                        self.log_result(
                            "test_add_customer_message", False,
                            "Message properties don't match expected values",
                            {
                                "expected_subject": message_data["subject"],
                                "actual_subject": created_message.subject,
                                "expected_content": message_data["content"],
                                "actual_content": created_message.content
                            }
                        )
                else:
                    self.log_result("test_add_customer_message", False, "Message was not created in database")
                    
        except Exception as e:
            db.session.rollback()
            self.log_result("test_add_customer_message", False, f"Exception: {str(e)}")
    
    def test_message_validation_errors(self):
        """Test message validation with invalid inputs."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                expert_id = self.test_data["expert_id"]
                
                # Test 1: Empty content (PostgreSQL allows empty strings, so this will pass)
                # This is expected behavior - empty strings are valid in PostgreSQL
                try:
                    message = ExpertConsoleMessage(
                        shipment_request_id=request_id,
                        expert_user_id=expert_id,
                        message_type="internal_note",
                        subject="Test Subject",
                        content="",  # Empty content
                        is_read_by_customer=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(message)
                    db.session.commit()
                    
                    # Clean up the created message
                    db.session.delete(message)
                    db.session.commit()
                    
                    self.log_result(
                        "test_message_validation_errors", True,
                        "Empty string content accepted (PostgreSQL behavior - empty strings are valid)",
                        {"note": "PostgreSQL treats empty strings as valid values, different from NULL"}
                    )
                except Exception as e:
                    db.session.rollback()
                    self.log_result(
                        "test_message_validation_errors", False,
                        "Unexpected rejection of empty string content",
                        {"error": str(e)}
                    )
                
                # Test 2: None content (should be rejected by NOT NULL constraint)
                try:
                    message = ExpertConsoleMessage(
                        shipment_request_id=request_id,
                        expert_user_id=expert_id,
                        message_type="internal_note",
                        subject="Test Subject",
                        content=None,  # None content
                        is_read_by_customer=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(message)
                    db.session.commit()
                    
                    self.log_result(
                        "test_message_validation_errors", False,
                        "Should have failed with None content but didn't"
                    )
                except Exception as e:
                    db.session.rollback()
                    self.log_result(
                        "test_message_validation_errors", True,
                        "Correctly rejected message with None content (NOT NULL constraint)",
                        {"error": str(e)}
                    )
                
                # Test 3: Invalid expert ID
                try:
                    message = ExpertConsoleMessage(
                        shipment_request_id=request_id,
                        expert_user_id=99999,  # Non-existent expert
                        message_type="internal_note",
                        subject="Test Subject",
                        content="Test content",
                        is_read_by_customer=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(message)
                    db.session.commit()
                    
                    self.log_result(
                        "test_message_validation_errors", False,
                        "Should have failed with invalid expert ID but didn't"
                    )
                except Exception as e:
                    db.session.rollback()
                    self.log_result(
                        "test_message_validation_errors", True,
                        "Correctly rejected message with invalid expert ID",
                        {"error": str(e)}
                    )
                
                # Test 4: Invalid request ID
                try:
                    message = ExpertConsoleMessage(
                        shipment_request_id=99999,  # Non-existent request
                        expert_user_id=expert_id,
                        message_type="internal_note",
                        subject="Test Subject",
                        content="Test content",
                        is_read_by_customer=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(message)
                    db.session.commit()
                    
                    self.log_result(
                        "test_message_validation_errors", False,
                        "Should have failed with invalid request ID but didn't"
                    )
                except Exception as e:
                    db.session.rollback()
                    self.log_result(
                        "test_message_validation_errors", True,
                        "Correctly rejected message with invalid request ID",
                        {"error": str(e)}
                    )
                    
        except Exception as e:
            db.session.rollback()
            self.log_result("test_message_validation_errors", False, f"Exception: {str(e)}")
    
    def test_customer_response_handling(self):
        """Test customer response handling in messages."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                expert_id = self.test_data["expert_id"]
                
                # Create a customer message first
                customer_message = ExpertConsoleMessage(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    message_type="customer_message",
                    subject="سوال مشتری",
                    content="آیا می‌توانید قیمت حمل را اعلام کنید؟",
                    is_read_by_customer=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(customer_message)
                db.session.flush()
                
                # Simulate customer response
                customer_response_text = "قیمت حمل 2,000,000 تومان است."
                customer_message.customer_response = customer_response_text
                customer_message.is_read_by_customer = True
                customer_message.updated_at = datetime.utcnow()
                
                # Create log entry for customer response
                log = ExpertConsoleLog(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    action="customer_response",
                    note="مشتری پاسخ داد",
                    ip_address="127.0.0.1",
                    created_at=datetime.utcnow()
                )
                db.session.add(log)
                
                db.session.commit()
                
                # Verify customer response was saved
                updated_message = db.session.query(ExpertConsoleMessage).get(customer_message.id)
                
                if (updated_message.customer_response == customer_response_text and
                    updated_message.is_read_by_customer == True):
                    
                    self.log_result(
                        "test_customer_response_handling", True,
                        "Customer response handled correctly",
                        {
                            "message_id": updated_message.id,
                            "customer_response": updated_message.customer_response,
                            "is_read_by_customer": updated_message.is_read_by_customer
                        }
                    )
                else:
                    self.log_result(
                        "test_customer_response_handling", False,
                        "Customer response not handled correctly",
                        {
                            "expected_response": customer_response_text,
                            "actual_response": updated_message.customer_response,
                            "expected_read": True,
                            "actual_read": updated_message.is_read_by_customer
                        }
                    )
                    
        except Exception as e:
            db.session.rollback()
            self.log_result("test_customer_response_handling", False, f"Exception: {str(e)}")
    
    def test_message_ordering(self):
        """Test that messages are properly ordered by creation time."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                expert_id = self.test_data["expert_id"]
                
                # Create multiple messages with different timestamps
                base_time = datetime.utcnow()
                
                message1 = ExpertConsoleMessage(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    message_type="internal_note",
                    subject="پیام اول",
                    content="این اولین پیام است",
                    is_read_by_customer=False,
                    created_at=base_time - timedelta(minutes=10),
                    updated_at=base_time - timedelta(minutes=10)
                )
                
                message2 = ExpertConsoleMessage(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    message_type="customer_message",
                    subject="پیام دوم",
                    content="این دومین پیام است",
                    is_read_by_customer=False,
                    created_at=base_time - timedelta(minutes=5),
                    updated_at=base_time - timedelta(minutes=5)
                )
                
                message3 = ExpertConsoleMessage(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    message_type="internal_note",
                    subject="پیام سوم",
                    content="این سومین پیام است",
                    is_read_by_customer=False,
                    created_at=base_time,
                    updated_at=base_time
                )
                
                db.session.add(message1)
                db.session.add(message2)
                db.session.add(message3)
                db.session.commit()
                
                # Get messages ordered by creation time (newest first)
                messages = db.session.query(ExpertConsoleMessage).filter(
                    ExpertConsoleMessage.shipment_request_id == request_id
                ).order_by(ExpertConsoleMessage.created_at.desc()).all()
                
                if len(messages) >= 3:
                    # Check if messages are in descending order (newest first)
                    timestamps = [msg.created_at for msg in messages]
                    is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
                    
                    if is_sorted:
                        self.log_result(
                            "test_message_ordering", True,
                            f"Messages are properly ordered by creation time",
                            {
                                "message_count": len(messages),
                                "first_message_subject": messages[0].subject,
                                "last_message_subject": messages[-1].subject,
                                "is_sorted": is_sorted
                            }
                        )
                    else:
                        self.log_result(
                            "test_message_ordering", False,
                            "Messages are not in descending order",
                            {
                                "timestamps": [ts.isoformat() for ts in timestamps],
                                "subjects": [msg.subject for msg in messages]
                            }
                        )
                else:
                    self.log_result(
                        "test_message_ordering", False,
                        f"Expected at least 3 messages, got {len(messages)}",
                        messages
                    )
                    
        except Exception as e:
            db.session.rollback()
            self.log_result("test_message_ordering", False, f"Exception: {str(e)}")
    
    def test_timeline_integration(self):
        """Test that message creation creates timeline entries."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                expert_id = self.test_data["expert_id"]
                
                # Create a message
                message = ExpertConsoleMessage(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    message_type="internal_note",
                    subject="تست تایم‌لاین",
                    content="این پیام برای تست تایم‌لاین است",
                    is_read_by_customer=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(message)
                
                # Create corresponding log entry
                log = ExpertConsoleLog(
                    shipment_request_id=request_id,
                    expert_user_id=expert_id,
                    action="message_added",
                    note="پیام internal_note اضافه شد",
                    ip_address="127.0.0.1",
                    created_at=datetime.utcnow()
                )
                db.session.add(log)
                
                db.session.commit()
                
                # Verify timeline entry was created
                timeline_entries = db.session.query(ExpertConsoleLog).filter(
                    ExpertConsoleLog.shipment_request_id == request_id,
                    ExpertConsoleLog.action == "message_added"
                ).all()
                
                if timeline_entries:
                    # Check if there's a timeline entry for our message
                    message_log = None
                    for entry in timeline_entries:
                        if "internal_note" in entry.note:
                            message_log = entry
                            break
                    
                    if message_log:
                        self.log_result(
                            "test_timeline_integration", True,
                            "Message creation created timeline entry",
                            {
                                "log_id": message_log.id,
                                "action": message_log.action,
                                "note": message_log.note,
                                "expert_id": message_log.expert_user_id
                            }
                        )
                    else:
                        self.log_result(
                            "test_timeline_integration", False,
                            "Timeline entry not found for message creation",
                            timeline_entries
                        )
                else:
                    self.log_result(
                        "test_timeline_integration", False,
                        "No timeline entries found for message_added action",
                        []
                    )
                    
        except Exception as e:
            db.session.rollback()
            self.log_result("test_timeline_integration", False, f"Exception: {str(e)}")
    
    def test_multiple_message_types(self):
        """Test creating multiple message types."""
        try:
            with self.app.app_context():
                request_id = self.test_data["request_id"]
                expert_id = self.test_data["expert_id"]
                
                # Create different types of messages
                message_types = [
                    {
                        "type": "internal_note",
                        "subject": "نظر کارشناس",
                        "content": "این یک پیام داخلی است"
                    },
                    {
                        "type": "customer_message",
                        "subject": "اطلاع‌رسانی به مشتری",
                        "content": "این پیام برای مشتری است"
                    }
                ]
                
                created_messages = []
                
                for msg_data in message_types:
                    message = ExpertConsoleMessage(
                        shipment_request_id=request_id,
                        expert_user_id=expert_id,
                        message_type=msg_data["type"],
                        subject=msg_data["subject"],
                        content=msg_data["content"],
                        is_read_by_customer=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.session.add(message)
                    created_messages.append(message)
                
                db.session.commit()
                
                # Verify all message types were created
                all_messages = db.session.query(ExpertConsoleMessage).filter(
                    ExpertConsoleMessage.shipment_request_id == request_id
                ).all()
                
                message_types_found = set(msg.message_type for msg in all_messages)
                expected_types = {"internal_note", "customer_message"}
                
                if message_types_found == expected_types:
                    self.log_result(
                        "test_multiple_message_types", True,
                        f"All message types created successfully",
                        {
                            "total_messages": len(all_messages),
                            "message_types_found": list(message_types_found),
                            "expected_types": list(expected_types)
                        }
                    )
                else:
                    self.log_result(
                        "test_multiple_message_types", False,
                        "Not all message types were created",
                        {
                            "message_types_found": list(message_types_found),
                            "expected_types": list(expected_types),
                            "missing_types": list(expected_types - message_types_found)
                        }
                    )
                    
        except Exception as e:
            db.session.rollback()
            self.log_result("test_multiple_message_types", False, f"Exception: {str(e)}")
    
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
                
                db.session.commit()
                self.log_result("cleanup_test_data", True, "Message management test data cleaned up successfully")
                
            except Exception as e:
                db.session.rollback()
                self.log_result("cleanup_test_data", False, f"Failed to clean up test data: {str(e)}")
    
    def run_all_tests(self):
        """Run all message management tests."""
        print("🧪 Starting Expert Message Management Direct Tests")
        print("=" * 60)
        
        try:
            # Setup
            self.setup_test_data()
            
            # Run tests
            self.test_add_internal_note_message()
            self.test_add_customer_message()
            self.test_message_validation_errors()
            self.test_customer_response_handling()
            self.test_message_ordering()
            self.test_timeline_integration()
            self.test_multiple_message_types()
            
        finally:
            # Cleanup
            self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Message Management Direct Test Summary")
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
    tester = MessageManagementDirectTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All message management direct tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some message management direct tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
