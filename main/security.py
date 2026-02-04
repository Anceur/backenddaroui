"""
Security utilities for preventing bot attacks on order submission
"""
import time
import hashlib
import secrets
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class OrderSecurityValidator:
    """Validates order submissions to prevent bot attacks"""
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    @staticmethod
    def get_client_fingerprint(request):
        """Generate a simple fingerprint from request headers"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        
        fingerprint_string = f"{user_agent}|{accept_language}|{accept_encoding}"
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    @staticmethod
    def check_rate_limit(ip_address, max_requests=5, window_seconds=60):
        """
        Check if IP has exceeded rate limit
        Returns: (is_allowed, remaining_requests, reset_time)
        """
        cache_key = f'order_rate_limit_{ip_address}'
        current_count = cache.get(cache_key, 0)
        
        if current_count >= max_requests:
            reset_time = cache.get(f'{cache_key}_reset', time.time() + window_seconds)
            return False, 0, reset_time
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window_seconds)
        cache.set(f'{cache_key}_reset', time.time() + window_seconds, window_seconds)
        
        remaining = max_requests - (current_count + 1)
        return True, remaining, time.time() + window_seconds
    
    @staticmethod
    def check_honeypot(data):
        """
        Check if honeypot field was filled (indicates bot)
        Honeypot field should be empty for legitimate users
        """
        honeypot_fields = ['website', 'url', 'email_confirm', 'confirm_email']
        for field in honeypot_fields:
            if field in data and data[field]:
                logger.warning(f"Honeypot field '{field}' was filled - possible bot")
                return False
        return True
    
    @staticmethod
    def validate_timestamp(token_data, min_seconds=3, max_seconds=3600):
        """
        Validate that form was filled in reasonable time
        token_data should contain 'timestamp' field
        """
        if not token_data or 'timestamp' not in token_data:
            return False, "Missing timestamp"
        
        try:
            timestamp = float(token_data['timestamp'])
            current_time = time.time()
            elapsed = current_time - timestamp
            
            if elapsed < min_seconds:
                logger.warning(f"Order submitted too quickly ({elapsed:.2f}s) - possible bot")
                return False, f"Please wait at least {min_seconds} seconds before submitting"
            
            if elapsed > max_seconds:
                logger.warning(f"Order submitted too late ({elapsed:.2f}s) - possible expired session")
                return False, "Session expired. Please refresh and try again"
            
            return True, None
        except (ValueError, TypeError):
            return False, "Invalid timestamp format"
    
    @staticmethod
    def validate_security_token(token_data, secret_key=None):
        """
        Validate security token to prevent replay attacks
        Token should contain: timestamp, nonce, and signature
        """
        if not token_data:
            return False, "Missing security token"
        
        required_fields = ['timestamp', 'nonce', 'signature']
        for field in required_fields:
            if field not in token_data:
                return False, f"Missing required field: {field}"
        
        # Validate nonce hasn't been used before (prevent replay)
        nonce = token_data['nonce']
        nonce_key = f'order_nonce_{nonce}'
        if cache.get(nonce_key):
            logger.warning(f"Reused nonce detected - possible replay attack")
            return False, "Invalid security token"
        
        # Store nonce for 1 hour
        cache.set(nonce_key, True, 3600)
        
        # Validate signature (optional - can be enhanced)
        # For now, just check that signature exists and is reasonable length
        signature = token_data.get('signature', '')
        if len(signature) < 10:
            return False, "Invalid security token format"
        
        return True, None
    
    @staticmethod
    def generate_security_token():
        """
        Generate a security token for the frontend
        Returns: dict with timestamp, nonce, and signature
        """
        timestamp = time.time()
        nonce = secrets.token_urlsafe(16)
        signature = hashlib.sha256(f"{timestamp}{nonce}".encode()).hexdigest()[:32]
        
        return {
            'timestamp': timestamp,
            'nonce': nonce,
            'signature': signature
        }
    
    @staticmethod
    def validate_request_headers(request):
        """
        Validate that request has legitimate browser headers
        """
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check for common bot user agents
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'python-requests', 'postman', 'insomnia', 'httpie'
        ]
        
        user_agent_lower = user_agent.lower()
        for pattern in bot_patterns:
            if pattern in user_agent_lower:
                logger.warning(f"Bot user agent detected: {user_agent}")
                return False, "Invalid request"
        
        # Check for required headers
        if not user_agent:
            return False, "Missing user agent"
        
        return True, None
    
    @staticmethod
    def validate_order_data_integrity(order_data, security_token):
        """
        Validate that order data hasn't been tampered with
        """
        # Check for suspicious patterns
        if 'items' in order_data:
            items = order_data['items']
            if isinstance(items, list):
                # Check for excessive quantities (possible bot)
                total_quantity = sum(item.get('quantity', 0) for item in items if isinstance(item, dict))
                if total_quantity > 100:
                    logger.warning(f"Suspicious order quantity: {total_quantity}")
                    return False, "Order quantity exceeds maximum limit"
                
                # Check for too many items
                if len(items) > 50:
                    logger.warning(f"Suspicious number of items: {len(items)}")
                    return False, "Order contains too many items"
        
        # Validate total matches items (basic check)
        if 'total' in order_data and 'items' in order_data:
            total = float(order_data.get('total', 0))
            if total <= 0:
                return False, "Invalid order total"
            
            # Check for suspiciously high totals
            if total > 10000:
                logger.warning(f"Suspicious order total: {total}")
                return False, "Order total exceeds maximum limit"
        
        return True, None
    
    @classmethod
    def validate_order_submission(cls, request, order_data, security_token_data):
        """
        Comprehensive validation of order submission
        Returns: (is_valid, error_message, error_details)
        """
        errors = []
        
        # 1. Rate limiting
        ip_address = cls.get_client_ip(request)
        is_allowed, remaining, reset_time = cls.check_rate_limit(ip_address, max_requests=5, window_seconds=60)
        if not is_allowed:
            errors.append({
                'type': 'rate_limit',
                'message': 'Too many order attempts. Please wait before trying again.',
                'reset_time': reset_time
            })
            return False, "Rate limit exceeded", errors
        
        # 2. Honeypot check
        if not cls.check_honeypot(order_data):
            errors.append({
                'type': 'honeypot',
                'message': 'Invalid form submission detected.'
            })
            return False, "Security validation failed", errors
        
        # 3. Request headers validation
        is_valid_header, header_error = cls.validate_request_headers(request)
        if not is_valid_header:
            errors.append({
                'type': 'headers',
                'message': header_error or 'Invalid request headers'
            })
            return False, "Security validation failed", errors
        
        # 4. Timestamp validation
        is_valid_time, time_error = cls.validate_timestamp(security_token_data, min_seconds=3, max_seconds=3600)
        if not is_valid_time:
            errors.append({
                'type': 'timestamp',
                'message': time_error or 'Invalid submission timing'
            })
            return False, "Security validation failed", errors
        
        # 5. Security token validation
        is_valid_token, token_error = cls.validate_security_token(security_token_data)
        if not is_valid_token:
            errors.append({
                'type': 'token',
                'message': token_error or 'Invalid security token'
            })
            return False, "Security validation failed", errors
        
        # 6. Order data integrity
        is_valid_data, data_error = cls.validate_order_data_integrity(order_data, security_token_data)
        if not is_valid_data:
            errors.append({
                'type': 'data_integrity',
                'message': data_error or 'Invalid order data'
            })
            return False, "Security validation failed", errors
        
        # All validations passed
        return True, None, None




