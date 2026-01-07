"""
Agent Name Sanitizer Utility

This module provides utilities for sanitizing agent names to comply with Azure AI requirements.
Azure agent names must:
- Start and end with alphanumeric characters
- Can contain hyphens in the middle
- Must not exceed 63 characters
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentNameSanitizer:
    """Utility class for sanitizing agent names to comply with Azure AI requirements."""
    
    MAX_LENGTH = 63
    DEFAULT_FALLBACK = "DefaultAgent"
    
    @staticmethod
    def sanitize(agent_name: Optional[str], fallback: str = DEFAULT_FALLBACK) -> str:
        """
        Sanitize an agent name to comply with Azure AI requirements.
        
        Args:
            agent_name: The original agent name to sanitize
            fallback: Fallback name to use if sanitization results in empty string
            
        Returns:
            A sanitized agent name that complies with Azure AI requirements
            
        Requirements:
            - Must start and end with alphanumeric characters
            - Can contain hyphens in the middle  
            - Must not exceed 63 characters
        """
        if not agent_name:
            return fallback
            
        original_name = agent_name
        
        # Remove any characters that aren't alphanumeric or hyphen
        sanitized = re.sub(r'[^a-zA-Z0-9-]', '', agent_name)
        
        # Ensure it starts with alphanumeric (remove leading hyphens)
        sanitized = re.sub(r'^-+', '', sanitized)
        
        # Ensure it ends with alphanumeric (remove trailing hyphens)
        sanitized = re.sub(r'-+$', '', sanitized)
        
        # Limit to maximum length
        if len(sanitized) > AgentNameSanitizer.MAX_LENGTH:
            sanitized = sanitized[:AgentNameSanitizer.MAX_LENGTH]
            # Re-check for trailing hyphens after truncation
            sanitized = re.sub(r'-+$', '', sanitized)
        
        # Fallback if sanitization resulted in empty string
        if not sanitized:
            logger.warning(
                f"Agent name '{original_name}' could not be sanitized, using fallback '{fallback}'"
            )
            return fallback
        
        # Log if name was changed
        if sanitized != original_name:
            logger.info(f"Sanitized agent name: '{original_name}' -> '{sanitized}'")
        
        return sanitized
    
    @staticmethod
    def is_valid(agent_name: str) -> bool:
        """
        Check if an agent name is already valid according to Azure AI requirements.
        
        Args:
            agent_name: The agent name to validate
            
        Returns:
            True if the name is valid, False otherwise
        """
        if not agent_name:
            return False
            
        # Check length
        if len(agent_name) > AgentNameSanitizer.MAX_LENGTH:
            return False
            
        # Check for invalid characters (only alphanumeric and hyphens allowed)
        if not re.match(r'^[a-zA-Z0-9-]+$', agent_name):
            return False
            
        # Check that it starts and ends with alphanumeric
        if not re.match(r'^[a-zA-Z0-9].*[a-zA-Z0-9]$', agent_name):
            return False
            
        return True