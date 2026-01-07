"""
Claude AI Service - Core AI Integration
"""
import sys
import logging
from typing import Dict, List, Any, Optional
from anthropic import Anthropic

from app.config import settings, SYSTEM_PROMPT_TEMPLATE, EMERGENCY_KEYWORDS

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for interacting with Anthropic Claude API"""
    
    def __init__(self):
        """Initialize Claude client"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        logger.info("Claude service initialized")
    
    def detect_emergency(self, message: str) -> Dict[str, Any]:
        """
        Detect if message contains emergency keywords
        
        Args:
            message: User's message
            
        Returns:
            Dict with is_emergency flag and detected keywords
        """
        message_lower = message.lower()
        detected_keywords = []
        
        for keyword in EMERGENCY_KEYWORDS:
            if keyword in message_lower:
                detected_keywords.append(keyword)
        
        return {
            "is_emergency": len(detected_keywords) > 0,
            "keywords": detected_keywords
        }
    
    def get_emergency_response(self, keywords: List[str]) -> str:
        """
        Get emergency response message
        
        Args:
            keywords: List of detected emergency keywords
            
        Returns:
            Emergency response text
        """
        return f"""🚨 EMERGENCY ALERT 🚨

This sounds like a medical emergency. The following concerning symptoms were detected: {', '.join(keywords)}

IMMEDIATE ACTION REQUIRED:
• Call 911 (or your local emergency number) immediately
• Do NOT wait or try to treat this yourself
• Go to the nearest emergency room
• If alone, call someone to be with you

This app is for educational purposes only and cannot help with emergencies.

Please seek immediate medical attention."""
    
    async def generate_response(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        max_tokens: int = 2000,
        member_id: Optional[int] = None,
        member_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response using Claude
        
        Args:
            user_message: User's message
            user_profile: User's health profile data
            conversation_history: Previous messages in conversation
            max_tokens: Maximum tokens in response
            member_id: Optional family member ID
            member_name: Optional family member name
            
        Returns:
            Dict with content, tokens_used, emergency flag, sources
        """
        try:
            # Check for emergency first
            emergency_check = self.detect_emergency(user_message)
            if emergency_check["is_emergency"]:
                return {
                    "content": self.get_emergency_response(emergency_check["keywords"]),
                    "emergency": True,
                    "tokens_used": 0,
                    "sources": []
                }
            
            # Build member context
            member_context = ""
            if member_id and member_name:
                member_context = f"\n\n**IMPORTANT CONTEXT**: You are currently chatting with {member_name}, a family member. Address them directly and personalize all advice for {member_name}, not the account owner."
                sys.stderr.write("=" * 60 + "\n")
                sys.stderr.write("👤 MEMBER CONTEXT ACTIVE!\n")
                sys.stderr.write(f"👤 member_id: {member_id}\n")
                sys.stderr.write(f"👤 member_name: {member_name}\n")
                sys.stderr.write(f"👤 member_context: {member_context}\n")
                sys.stderr.write("=" * 60 + "\n")
                sys.stderr.flush()
            else:
                sys.stderr.write("⚠️ NO MEMBER CONTEXT\n")
                sys.stderr.write(f"⚠️ member_id: {member_id}\n")
                sys.stderr.write(f"⚠️ member_name: {member_name}\n")
                sys.stderr.flush()
            
            # Build system prompt
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                user_profile=self._format_user_profile(user_profile),
                conversation_history=self._format_conversation(conversation_history),
                rag_context=""  # TODO: Integrate RAG when available
            ) + member_context
            
            # Build messages for Claude
            messages = conversation_history + [
                {"role": "user", "content": user_message}
            ]
            
            # Call Claude API with debug logging
            sys.stderr.write(f"🤖 System prompt length: {len(system_prompt)} chars\n")
            sys.stderr.write(f"🤖 Last 300 chars: ...{system_prompt[-300:]}\n")
            sys.stderr.flush()
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                temperature=0.7
            )
            
            # Extract response
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            logger.info(f"Generated response ({tokens_used} tokens)")
            
            return {
                "content": content,
                "tokens_used": tokens_used,
                "emergency": False,
                "sources": []  # TODO: Add knowledge base sources
            }
        
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            raise
    
    def _format_user_profile(self, profile: Dict[str, Any]) -> str:
        """Format user profile for system prompt"""
        if not profile:
            return "No health profile provided yet."
        
        parts = []
        if profile.get("ayurvedic_dosha"):
            parts.append(f"Ayurvedic Constitution: {profile['ayurvedic_dosha']}")
        if profile.get("current_conditions"):
            parts.append(f"Current Conditions: {', '.join(profile['current_conditions'])}")
        if profile.get("preferred_traditions"):
            parts.append(f"Preferred Traditions: {', '.join(profile['preferred_traditions'])}")
        
        return "\n".join(parts) if parts else "Minimal profile information."
    
    def _format_conversation(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history for system prompt"""
        if not history:
            return "This is the start of a new conversation."
        
        formatted = []
        for msg in history[-5:]:  # Last 5 messages for context
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content[:200]}")
        
        return "\n".join(formatted)


# Singleton instance
claude_service = ClaudeService()
