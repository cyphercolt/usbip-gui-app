"""Rate limiting and connection security"""
import time
from typing import Dict, Tuple


class RateLimiter:
    """Simple rate limiting for SSH connections and commands"""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if the identifier is allowed to make a request"""
        current_time = time.time()
        
        # Clean old attempts
        if identifier in self.attempts:
            self.attempts[identifier] = [
                attempt_time for attempt_time in self.attempts[identifier]
                if current_time - attempt_time < self.window_seconds
            ]
        else:
            self.attempts[identifier] = []
        
        # Check if under limit
        return len(self.attempts[identifier]) < self.max_attempts
    
    def record_attempt(self, identifier: str):
        """Record an attempt for the identifier"""
        current_time = time.time()
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        self.attempts[identifier].append(current_time)
    
    def get_remaining_time(self, identifier: str) -> int:
        """Get remaining time before next attempt is allowed"""
        if identifier not in self.attempts or len(self.attempts[identifier]) < self.max_attempts:
            return 0
        
        oldest_attempt = min(self.attempts[identifier])
        return max(0, int(self.window_seconds - (time.time() - oldest_attempt)))


class ConnectionSecurity:
    """Enhanced connection security features"""
    
    def __init__(self):
        self.ssh_rate_limiter = RateLimiter(max_attempts=3, window_seconds=300)  # 3 attempts per 5 minutes
        self.command_rate_limiter = RateLimiter(max_attempts=10, window_seconds=60)  # 10 commands per minute
    
    def check_ssh_connection_allowed(self, ip: str) -> Tuple[bool, int]:
        """Check if SSH connection to IP is allowed"""
        allowed = self.ssh_rate_limiter.is_allowed(ip)
        remaining_time = self.ssh_rate_limiter.get_remaining_time(ip)
        return allowed, remaining_time
    
    def record_ssh_attempt(self, ip: str):
        """Record SSH connection attempt"""
        self.ssh_rate_limiter.record_attempt(ip)
    
    def check_command_allowed(self, ip: str) -> Tuple[bool, int]:
        """Check if command execution to IP is allowed"""
        allowed = self.command_rate_limiter.is_allowed(ip)
        remaining_time = self.command_rate_limiter.get_remaining_time(ip)
        return allowed, remaining_time
    
    def record_command_attempt(self, ip: str):
        """Record command execution attempt"""
        self.command_rate_limiter.record_attempt(ip)
