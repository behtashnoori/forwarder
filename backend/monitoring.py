"""Monitoring and analytics system for the application."""
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from functools import wraps
from collections import defaultdict, deque

from flask import request, g, current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest, Customer, Opportunity, Activity
from backend.services.utc_timestamp import current_utc_timestamp
from backend.quarantine import decision_epoch_token


class SystemMonitor:
    """System monitoring and metrics collection."""
    
    def __init__(self):
        self.metrics = {
            'requests': deque(maxlen=1000),
            'errors': deque(maxlen=500),
            'performance': deque(maxlen=1000),
            'users': defaultdict(int),
            'endpoints': defaultdict(int)
        }
        self.start_time = datetime.utcnow()
    
    def record_request(self, method: str, endpoint: str, status_code: int, 
                      response_time: float, user_id: Optional[int] = None):
        """Record API request metrics."""
        request_data = {
            'timestamp': current_utc_timestamp(),
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'response_time': response_time,
            'user_id': user_id,
            'ip_address': request.remote_addr
        }
        
        self.metrics['requests'].append(request_data)
        self.metrics['endpoints'][f"{method} {endpoint}"] += 1
        
        if user_id:
            self.metrics['users'][user_id] += 1
    
    def record_error(self, error: Exception, context: Dict[str, Any]):
        """Record error metrics."""
        error_data = {
            'timestamp': current_utc_timestamp(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'endpoint': getattr(request, 'endpoint', 'unknown'),
            'method': getattr(request, 'method', 'unknown')
        }
        
        self.metrics['errors'].append(error_data)
    
    def record_performance(self, operation: str, duration: float, 
                          additional_metrics: Optional[Dict] = None):
        """Record performance metrics."""
        perf_data = {
            'timestamp': current_utc_timestamp(),
            'operation': operation,
            'duration': duration,
            'additional_metrics': additional_metrics or {}
        }
        
        self.metrics['performance'].append(perf_data)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Request metrics
        total_requests = len(self.metrics['requests'])
        recent_requests = list(self.metrics['requests'])[-100:]  # Last 100 requests
        
        # Error metrics
        total_errors = len(self.metrics['errors'])
        recent_errors = list(self.metrics['errors'])[-50:]  # Last 50 errors
        
        # Performance metrics
        recent_performance = list(self.metrics['performance'])[-100:]
        avg_response_time = 0
        if recent_performance:
            avg_response_time = sum(p['duration'] for p in recent_performance) / len(recent_performance)
        
        return {
            'system': {
                'uptime_seconds': uptime,
                'cpu_percent': cpu_percent,
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            },
            'application': {
                'total_requests': total_requests,
                'total_errors': total_errors,
                'avg_response_time': avg_response_time,
                'active_users': len(self.metrics['users']),
                'top_endpoints': dict(sorted(self.metrics['endpoints'].items(), 
                                           key=lambda x: x[1], reverse=True)[:10])
            },
            'recent_activity': {
                'requests': recent_requests,
                'errors': recent_errors,
                'performance': recent_performance
            }
        }
    
    def get_database_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        try:
            with db.session.begin():
                # Table sizes
                table_sizes = {}
                certified_models = {
                    'shipment_request': ShipmentRequest,
                    'customer': Customer,
                    'opportunity': Opportunity,
                    'activity': Activity,
                }
                for table, model in certified_models.items():
                    table_sizes[table] = db.session.query(model).count()
                # ExpertUser is platform identity rather than tenant business data.
                table_sizes['expert_user'] = db.session.query(ExpertUser).count()
                
                # Recent activity counts
                today = datetime.utcnow().date()
                week_ago = today - timedelta(days=7)
                
                recent_requests = db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.created_at >= week_ago
                ).count()
                
                recent_customers = db.session.query(Customer).filter(
                    Customer.created_at >= week_ago
                ).count()
                
                recent_activities = db.session.query(Activity).filter(
                    Activity.created_at >= week_ago
                ).count()
                
                return {
                    'table_sizes': table_sizes,
                    'recent_activity': {
                        'requests_this_week': recent_requests,
                        'customers_this_week': recent_customers,
                        'activities_this_week': recent_activities
                    }
                }
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database metrics error: {e}")
            return {'error': 'Failed to get database metrics'}
    
    def get_business_metrics(self) -> Dict[str, Any]:
        """Get business-specific metrics."""
        try:
            with db.session.begin():
                # Customer metrics
                total_customers = db.session.query(Customer).count()
                active_customers = db.session.query(Customer).filter(
                    Customer.status == 'active'
                ).count()
                
                # Opportunity metrics
                total_opportunities = db.session.query(Opportunity).count()
                open_opportunities = db.session.query(Opportunity).filter(
                    Opportunity.status == 'open'
                ).count()
                won_opportunities = db.session.query(Opportunity).filter(
                    Opportunity.status == 'won'
                ).count()
                
                # Pipeline value
                pipeline_value = db.session.query(func.sum(Opportunity.value)).filter(
                    Opportunity.status == 'open'
                ).scalar() or 0
                
                # Request metrics
                total_requests = db.session.query(ShipmentRequest).count()
                new_requests = db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.status == 'new'
                ).count()
                completed_requests = db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.status.in_(['won', 'closed'])
                ).count()
                
                # Expert metrics
                total_experts = db.session.query(ExpertUser).filter(
                    ExpertUser.is_active
                ).count()
                
                return {
                    'customers': {
                        'total': total_customers,
                        'active': active_customers,
                        'inactive': total_customers - active_customers
                    },
                    'opportunities': {
                        'total': total_opportunities,
                        'open': open_opportunities,
                        'won': won_opportunities,
                        'pipeline_value': float(pipeline_value)
                    },
                    'requests': {
                        'total': total_requests,
                        'new': new_requests,
                        'completed': completed_requests
                    },
                    'experts': {
                        'total': total_experts
                    }
                }
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Business metrics error: {e}")
            return {'error': 'Failed to get business metrics'}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        metrics = self.get_system_metrics()
        
        # Health indicators
        health_indicators = {
            'database': 'healthy',
            'memory': 'healthy',
            'cpu': 'healthy',
            'errors': 'healthy'
        }
        
        # Check memory usage
        if metrics['system']['memory']['percent'] > 90:
            health_indicators['memory'] = 'critical'
        elif metrics['system']['memory']['percent'] > 80:
            health_indicators['memory'] = 'warning'
        
        # Check CPU usage
        if metrics['system']['cpu_percent'] > 90:
            health_indicators['cpu'] = 'critical'
        elif metrics['system']['cpu_percent'] > 80:
            health_indicators['cpu'] = 'warning'
        
        # Check error rate
        total_requests = metrics['application']['total_requests']
        total_errors = metrics['application']['total_errors']
        
        if total_requests > 0:
            error_rate = (total_errors / total_requests) * 100
            if error_rate > 10:
                health_indicators['errors'] = 'critical'
            elif error_rate > 5:
                health_indicators['errors'] = 'warning'
        
        # Overall health
        overall_health = 'healthy'
        if any(status in ['critical', 'warning'] for status in health_indicators.values()):
            if 'critical' in health_indicators.values():
                overall_health = 'critical'
            else:
                overall_health = 'warning'
        
        return {
            'overall': overall_health,
            'indicators': health_indicators,
            'timestamp': current_utc_timestamp()
        }


# Global monitor instance
system_monitor = SystemMonitor()


def monitor_performance(operation_name: str):
    """Decorator to monitor performance of functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                system_monitor.record_performance(operation_name, duration)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                system_monitor.record_performance(operation_name, duration, {
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                
                system_monitor.record_error(e, {
                    'operation': operation_name,
                    'function': func.__name__
                })
                
                raise
        
        return wrapper
    return decorator


def monitor_api_call(func):
    """Decorator to monitor API calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            system_monitor.record_request(
                method=request.method,
                endpoint=request.endpoint or request.path,
                status_code=200,
                response_time=duration,
                user_id=getattr(g, 'current_user_id', None)
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            system_monitor.record_request(
                method=request.method,
                endpoint=request.endpoint or request.path,
                status_code=500,
                response_time=duration,
                user_id=getattr(g, 'current_user_id', None)
            )
            
            system_monitor.record_error(e, {
                'endpoint': request.endpoint or request.path,
                'method': request.method
            })
            
            raise
    
    return wrapper


class AnalyticsEngine:
    """Analytics engine for business intelligence."""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_customer_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get customer analytics for the specified period."""
        cache_key = f"customer_analytics_{days}_{decision_epoch_token()}"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.utcnow().timestamp() - timestamp < self.cache_ttl:
                return cached_data
        
        try:
            with db.session.begin():
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Customer growth
                total_customers = db.session.query(Customer).count()
                new_customers = db.session.query(Customer).filter(
                    Customer.created_at >= start_date
                ).count()
                
                # Customer types distribution
                type_distribution = db.session.query(
                    Customer.customer_type,
                    func.count(Customer.id)
                ).group_by(Customer.customer_type).all()
                
                # Industry distribution
                industry_distribution = db.session.query(
                    Customer.industry,
                    func.count(Customer.id)
                ).filter(Customer.industry.isnot(None)).group_by(Customer.industry).all()
                
                # Customer activity
                active_customers = db.session.query(Customer).filter(
                    Customer.status == 'active'
                ).count()
                
                analytics = {
                    'total_customers': total_customers,
                    'new_customers': new_customers,
                    'growth_rate': (new_customers / max(total_customers - new_customers, 1)) * 100,
                    'type_distribution': dict(type_distribution),
                    'industry_distribution': dict(industry_distribution),
                    'active_customers': active_customers,
                    'activity_rate': (active_customers / max(total_customers, 1)) * 100
                }
                
                # Cache the result
                self.cache[cache_key] = (analytics, datetime.utcnow().timestamp())
                
                return analytics
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Customer analytics error: {e}")
            return {'error': 'Failed to get customer analytics'}
    
    def get_sales_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get sales analytics for the specified period."""
        cache_key = f"sales_analytics_{days}_{decision_epoch_token()}"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.utcnow().timestamp() - timestamp < self.cache_ttl:
                return cached_data
        
        try:
            with db.session.begin():
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Opportunity metrics
                total_opportunities = db.session.query(Opportunity).count()
                new_opportunities = db.session.query(Opportunity).filter(
                    Opportunity.created_at >= start_date
                ).count()
                
                won_opportunities = db.session.query(Opportunity).filter(
                    Opportunity.status == 'won'
                ).count()
                
                # Pipeline value
                pipeline_value = db.session.query(func.sum(Opportunity.value)).filter(
                    Opportunity.status == 'open'
                ).scalar() or 0
                
                # Won value
                won_value = db.session.query(func.sum(Opportunity.value)).filter(
                    Opportunity.status == 'won'
                ).scalar() or 0
                
                # Conversion rate
                conversion_rate = (won_opportunities / max(total_opportunities, 1)) * 100
                
                # Stage distribution
                stage_distribution = db.session.query(
                    Opportunity.stage,
                    func.count(Opportunity.id)
                ).group_by(Opportunity.stage).all()
                
                analytics = {
                    'total_opportunities': total_opportunities,
                    'new_opportunities': new_opportunities,
                    'won_opportunities': won_opportunities,
                    'conversion_rate': conversion_rate,
                    'pipeline_value': float(pipeline_value),
                    'won_value': float(won_value),
                    'stage_distribution': dict(stage_distribution)
                }
                
                # Cache the result
                self.cache[cache_key] = (analytics, datetime.utcnow().timestamp())
                
                return analytics
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Sales analytics error: {e}")
            return {'error': 'Failed to get sales analytics'}
    
    def get_performance_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get performance analytics for the specified period."""
        cache_key = f"performance_analytics_{days}_{decision_epoch_token()}"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.utcnow().timestamp() - timestamp < self.cache_ttl:
                return cached_data
        
        try:
            with db.session.begin():
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # Request metrics
                total_requests = db.session.query(ShipmentRequest).count()
                new_requests = db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.created_at >= start_date
                ).count()
                
                completed_requests = db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.status.in_(['won', 'closed'])
                ).count()
                
                # SLA compliance
                overdue_requests = db.session.query(ShipmentRequest).filter(
                    ShipmentRequest.sla_due_at < datetime.utcnow(),
                    ShipmentRequest.status.in_(['assigned', 'in_progress'])
                ).count()
                
                # Expert performance
                expert_performance = db.session.query(
                    ExpertUser.full_name,
                    func.count(ShipmentRequest.id)
                ).join(ShipmentRequest, ShipmentRequest.assigned_to == ExpertUser.id).group_by(
                    ExpertUser.id, ExpertUser.full_name
                ).all()
                
                analytics = {
                    'total_requests': total_requests,
                    'new_requests': new_requests,
                    'completed_requests': completed_requests,
                    'completion_rate': (completed_requests / max(total_requests, 1)) * 100,
                    'overdue_requests': overdue_requests,
                    'sla_compliance': ((total_requests - overdue_requests) / max(total_requests, 1)) * 100,
                    'expert_performance': dict(expert_performance)
                }
                
                # Cache the result
                self.cache[cache_key] = (analytics, datetime.utcnow().timestamp())
                
                return analytics
                
        except SQLAlchemyError as e:
            current_app.logger.error(f"Performance analytics error: {e}")
            return {'error': 'Failed to get performance analytics'}


# Global analytics engine
analytics_engine = AnalyticsEngine()
