"""
Security Utilities for AI Insights
Provides input validation, output sanitization, and rate limiting
"""

import re
import html
import logging
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class SecurityUtils:
    """Security utilities for AI Insights"""
    
    # Dangerous patterns to filter
    DANGEROUS_PATTERNS = [
        # SQL Injection
        r'DROP\s+TABLE',
        r'DELETE\s+FROM',
        r'INSERT\s+INTO',
        r'UPDATE\s+SET',
        r'UNION\s+SELECT',
        r';\s*--',
        r"'\s*OR\s*'1'\s*=\s*'1",
        
        # XSS
        r'<script[^>]*>',
        r'javascript:',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onload\s*=',
        r'<iframe[^>]*>',
        
        # Code Injection
        r'__import__\s*\(',
        r'eval\s*\(',
        r'exec\s*\(',
        r'compile\s*\(',
        
        # Template Injection
        r'\{\{.*\}\}',
        r'\$\{.*\}',
        
        # Path Traversal
        r'\.\./\.\.',
        r'\.\.\\\\',
        
        # Command Injection
        r';\s*ls\s*;',
        r';\s*cat\s*;',
        r'\|\s*bash',
        r'`.*`',
    ]
    
    @staticmethod
    def validate_input(question: str, max_length: int = 10000) -> str:
        """
        Validate and sanitize user input
        
        Args:
            question: User input
            max_length: Maximum allowed length
        
        Returns:
            Sanitized input string
        """
        try:
            # Handle None
            if question is None:
                return ""
            
            # Convert to string
            question = str(question)
            
            # Limit length
            if len(question) > max_length:
                logger.warning(f"Input truncated from {len(question)} to {max_length} chars")
                question = question[:max_length]
            
            # Remove null bytes
            question = question.replace('\x00', '')
            
            # Normalize whitespace
            question = ' '.join(question.split())
            
            # Remove excessive punctuation
            question = re.sub(r'([!?.]){4,}', r'\1\1\1', question)
            
            return question
            
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            return ""
    
    @staticmethod
    def sanitize_output(response: str, escape_html: bool = True) -> str:
        """
        Sanitize output for safe display
        
        Args:
            response: AI response
            escape_html: Whether to HTML escape
        
        Returns:
            Sanitized response
        """
        try:
            if not response:
                return ""
            
            response = str(response)
            
            # HTML escape if requested
            if escape_html:
                response = html.escape(response)
            
            # Filter dangerous patterns (case-insensitive)
            for pattern in SecurityUtils.DANGEROUS_PATTERNS:
                response = re.sub(pattern, '[FILTERED]', response, flags=re.IGNORECASE)
            
            # Remove any remaining script tags
            response = re.sub(r'<script[^>]*>.*?</script>', '[FILTERED]', response, flags=re.IGNORECASE | re.DOTALL)
            
            # Remove event handlers
            response = re.sub(r'on\w+\s*=\s*["\'].*?["\']', '[FILTERED]', response, flags=re.IGNORECASE)
            
            return response
            
        except Exception as e:
            logger.error(f"Output sanitization failed: {e}")
            return str(response)
    
    @staticmethod
    def detect_malicious_intent(question: str) -> Tuple[bool, Optional[str]]:
        """
        Detect potentially malicious input
        
        Args:
            question: User input
        
        Returns:
            Tuple of (is_malicious, attack_type)
        """
        try:
            if not question:
                return False, None
            
            question_str = str(question).lower()
            
            # Check for SQL injection
            sql_patterns = ['drop table', 'delete from', 'union select', "' or '1'='1"]
            if any(pattern in question_str for pattern in sql_patterns):
                return True, "SQL Injection"
            
            # Check for XSS
            xss_patterns = ['<script', 'javascript:', 'onerror=', 'onclick=']
            if any(pattern in question_str for pattern in xss_patterns):
                return True, "XSS Attack"
            
            # Check for code injection
            code_patterns = ['__import__', 'eval(', 'exec(', 'compile(']
            if any(pattern in question_str for pattern in code_patterns):
                return True, "Code Injection"
            
            # Check for path traversal
            if '../' in question_str or '..\\' in question_str:
                return True, "Path Traversal"
            
            return False, None
            
        except Exception as e:
            logger.error(f"Malicious intent detection failed: {e}")
            return False, None


class RateLimiter:
    """Rate limiter for API protection"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = defaultdict(list)
        self.blocked_users = {}
    
    def is_allowed(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is allowed
        
        Args:
            user_id: User identifier
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        try:
            # Check if user is blocked
            if user_id in self.blocked_users:
                block_until = self.blocked_users[user_id]
                if datetime.now() < block_until:
                    remaining = (block_until - datetime.now()).seconds
                    return False, f"Rate limit exceeded. Try again in {remaining}s"
                else:
                    # Unblock user
                    del self.blocked_users[user_id]
            
            now = datetime.now()
            cutoff = now - self.window
            
            # Remove old requests
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if req_time > cutoff
            ]
            
            # Check limit
            if len(self.requests[user_id]) >= self.max_requests:
                # Block user for 1 minute
                self.blocked_users[user_id] = now + timedelta(minutes=1)
                return False, f"Rate limit exceeded ({self.max_requests} requests per {self.window.seconds}s)"
            
            # Add new request
            self.requests[user_id].append(now)
            return True, None
            
        except Exception as e:
            logger.error(f"Rate limiting failed: {e}")
            # Fail open (allow request)
            return True, None
    
    def get_remaining_requests(self, user_id: str) -> int:
        """Get remaining requests for user"""
        try:
            now = datetime.now()
            cutoff = now - self.window
            
            # Count recent requests
            recent = [
                req_time for req_time in self.requests.get(user_id, [])
                if req_time > cutoff
            ]
            
            return max(0, self.max_requests - len(recent))
            
        except Exception as e:
            logger.error(f"Failed to get remaining requests: {e}")
            return self.max_requests
    
    def reset_user(self, user_id: str):
        """Reset rate limit for user"""
        if user_id in self.requests:
            del self.requests[user_id]
        if user_id in self.blocked_users:
            del self.blocked_users[user_id]


class InputValidator:
    """Advanced input validation"""
    
    @staticmethod
    def validate_question(question: str) -> Tuple[bool, Optional[str]]:
        """
        Validate question input
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if None
            if question is None:
                return True, None  # Allow None, will be converted to empty string
            
            # Convert to string
            question = str(question)
            
            # Check length
            if len(question) > 50000:
                return False, "Question too long (max 50,000 characters)"
            
            # Check for null bytes
            if '\x00' in question:
                return False, "Invalid characters detected"
            
            # Check for excessive repetition (potential DoS)
            if len(set(question)) < 5 and len(question) > 100:
                return False, "Suspicious input pattern detected"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Question validation failed: {e}")
            return False, str(e)
    
    @staticmethod
    def validate_context(context: str) -> Tuple[bool, Optional[str]]:
        """
        Validate context input
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if context is None:
                return True, None
            
            context = str(context)
            
            if len(context) > 100000:
                return False, "Context too large (max 100,000 characters)"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Context validation failed: {e}")
            return False, str(e)
    
    @staticmethod
    def validate_history(history: list) -> Tuple[bool, Optional[str]]:
        """
        Validate conversation history
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if history is None:
                return True, None
            
            if not isinstance(history, list):
                return False, "History must be a list"
            
            if len(history) > 100:
                return False, "History too long (max 100 exchanges)"
            
            # Validate each entry
            for entry in history:
                if not isinstance(entry, dict):
                    continue  # Skip invalid entries
                
                # Check for excessive content
                query = str(entry.get('query', ''))
                response = str(entry.get('response', ''))
                
                if len(query) > 10000 or len(response) > 10000:
                    return False, "History entry too large"
            
            return True, None
            
        except Exception as e:
            logger.error(f"History validation failed: {e}")
            return False, str(e)


class ResponseValidator:
    """Validate AI responses for quality and safety"""
    
    @staticmethod
    def validate_response(response: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate AI response
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check required fields
            if 'insight' not in response and 'answer' not in response:
                return False, "Response missing content field"
            
            # Get response text
            text = response.get('insight', response.get('answer', ''))
            
            # Check minimum length
            if len(text) < 10:
                return False, "Response too short"
            
            # Check maximum length
            if len(text) > 50000:
                return False, "Response too long"
            
            # Check for dangerous content
            dangerous = ['<script>', 'javascript:', 'onerror=', 'DROP TABLE']
            if any(pattern in text for pattern in dangerous):
                return False, "Response contains dangerous content"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            return False, str(e)
    
    @staticmethod
    def ensure_music_context(response: str, question: str) -> str:
        """
        Ensure response is music-related
        
        Args:
            response: AI response
            question: Original question
        
        Returns:
            Music-contextualized response
        """
        try:
            # Check if response is music-related
            music_keywords = ['music', 'song', 'artist', 'album', 'genre', 'playlist', 
                            'track', 'band', 'singer', 'listen', 'sound']
            
            response_lower = response.lower()
            
            if not any(keyword in response_lower for keyword in music_keywords):
                # Add music context
                prefix = "For music recommendations: "
                response = prefix + response
            
            return response
            
        except Exception as e:
            logger.error(f"Music context enforcement failed: {e}")
            return response


# Global rate limiter instance
_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    return _rate_limiter
