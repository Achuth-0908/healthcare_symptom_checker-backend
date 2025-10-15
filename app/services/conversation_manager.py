"""
Multi-turn conversation management
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models import Assessment, UrgencyLevel

logger = logging.getLogger(__name__)


class ConversationSession:
    """Manages individual conversation sessions"""
    
    def __init__(
        self,
        session_id: str,
        age: Optional[int] = None,
        sex: Optional[str] = None,
        medical_history: List[str] = None,
        medications: List[str] = None,
        allergies: List[str] = None
    ):
        self.session_id = session_id
        self.age = age
        self.sex = sex
        self.medical_history = medical_history or []
        self.medications = medications or []
        self.allergies = allergies or []
        self.turns: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.status = "active"
        self.turn_count = 0
        self.max_turns = settings.MAX_CONVERSATION_TURNS
    
    def add_turn(
        self,
        user_message: str,
        assessment: Assessment,
        severity: Optional[int] = None
    ):
        """Add a new conversation turn"""
        turn = {
            "turn_number": self.turn_count + 1,
            "user_message": user_message,
            "assessment": assessment.model_dump() if assessment else None,
            "severity": severity,
            "timestamp": datetime.now(),
            "urgency_level": assessment.urgency.value if assessment else "UNKNOWN"
        }
        
        self.turns.append(turn)
        self.turn_count += 1
        self.last_updated = datetime.now()
        
        logger.info(f"Added turn {self.turn_count} to session {self.session_id}")
    
    def get_conversation_context(self) -> str:
        """Build conversation context for LLM"""
        if not self.turns:
            return "No previous conversation."
        
        context_parts = []
        context_parts.append(f"Patient: {self.age} year old {self.sex or 'person'}")
        
        if self.medical_history:
            context_parts.append(f"Medical History: {', '.join(self.medical_history)}")
        
        if self.medications:
            context_parts.append(f"Current Medications: {', '.join(self.medications)}")
        
        if self.allergies:
            context_parts.append(f"Allergies: {', '.join(self.allergies)}")
        
        context_parts.append("\nConversation History:")
        
        for turn in self.turns[-3:]:
            context_parts.append(f"Turn {turn['turn_number']}:")
            context_parts.append(f"User: {turn['user_message']}")
            if turn['assessment']:
                urgency = turn['assessment'].get('urgency', 'UNKNOWN')
                context_parts.append(f"Assessment: {urgency} urgency")
                if turn['assessment'].get('probable_conditions'):
                    conditions = [c['name'] for c in turn['assessment']['probable_conditions']]
                    context_parts.append(f"Conditions: {', '.join(conditions)}")
        
        return "\n".join(context_parts)
    
    def should_end_conversation(self) -> bool:
        """Check if conversation should end"""
        if self.turn_count >= self.max_turns:
            return True
        
        if self.status == "completed":
            return True
        
        if datetime.now() - self.created_at > timedelta(seconds=settings.SESSION_TIMEOUT):
            return True
        
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate conversation summary"""
        if not self.turns:
            return {"message": "No conversation turns recorded"}
        
        final_turn = self.turns[-1]
        final_assessment = final_turn.get('assessment', {})
        
        urgency_counts = {}
        for turn in self.turns:
            urgency = turn.get('urgency_level', 'UNKNOWN')
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
        
        return {
            "session_id": self.session_id,
            "total_turns": self.turn_count,
            "duration_minutes": (self.last_updated - self.created_at).total_seconds() / 60,
            "final_urgency": final_assessment.get('urgency', 'UNKNOWN'),
            "urgency_distribution": urgency_counts,
            "probable_conditions": final_assessment.get('probable_conditions', []),
            "recommendations": final_assessment.get('recommendations', []),
            "status": self.status
        }
    
    def end_session(self):
        """End the conversation session"""
        self.status = "completed"
        self.last_updated = datetime.now()
        logger.info(f"Ended session {self.session_id}")


class ConversationManager:
    """Manages multiple conversation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.cleanup_interval = 3600
        self.last_cleanup = datetime.now()
    
    def create_session(
        self,
        age: Optional[int] = None,
        sex: Optional[str] = None,
        medical_history: List[str] = None,
        medications: List[str] = None,
        allergies: List[str] = None
    ) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        
        session = ConversationSession(
            session_id=session_id,
            age=age,
            sex=sex,
            medical_history=medical_history,
            medications=medications,
            allergies=allergies
        )
        
        self.sessions[session_id] = session
        self._cleanup_old_sessions()
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get conversation session by ID"""
        return self.sessions.get(session_id)
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assessment: Assessment,
        severity: Optional[int] = None
    ) -> bool:
        """Add turn to session"""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return False
        
        if session.should_end_conversation():
            logger.warning(f"Session {session_id} should have ended")
            return False
        
        session.add_turn(user_message, assessment, severity)
        return True
    
    def end_session(self, session_id: str) -> bool:
        """End conversation session"""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return False
        
        session.end_session()
        return True
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session summary"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.get_summary()
    
    def _cleanup_old_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now()
        if (now - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return
        
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if now - session.last_updated > timedelta(seconds=settings.SESSION_TIMEOUT):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
        
        self.last_cleanup = now
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len([s for s in self.sessions.values() if s.status == "active"])
    
    def get_all_sessions_summary(self) -> Dict[str, Any]:
        """Get summary of all sessions"""
        active_count = self.get_active_sessions_count()
        total_count = len(self.sessions)
        
        urgency_distribution = {}
        for session in self.sessions.values():
            if session.turns:
                final_urgency = session.turns[-1].get('urgency_level', 'UNKNOWN')
                urgency_distribution[final_urgency] = urgency_distribution.get(final_urgency, 0) + 1
        
        return {
            "total_sessions": total_count,
            "active_sessions": active_count,
            "completed_sessions": total_count - active_count,
            "urgency_distribution": urgency_distribution,
            "last_cleanup": self.last_cleanup.isoformat()
        }


_conversation_manager = None

def get_conversation_manager() -> ConversationManager:
    """Get or create conversation manager instance"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager