"""
Triage Service for emergency detection and urgency assessment
"""

import logging
from typing import List, Tuple, Optional
from app.config import settings, EMERGENCY_KEYWORDS, URGENT_KEYWORDS, BODY_SYSTEMS
from app.models import UrgencyLevel

logger = logging.getLogger(__name__)


class TriageService:
    """
    Medical triage service for emergency detection and urgency assessment
    """
    
    def __init__(self):
        self.emergency_keywords = EMERGENCY_KEYWORDS
        self.urgent_keywords = URGENT_KEYWORDS
        self.body_systems = BODY_SYSTEMS
    
    def quick_triage(self, symptoms: str, severity: int = None) -> Tuple[UrgencyLevel, List[str]]:
        """
        Perform quick triage based on keyword detection
        Returns (urgency_level, detected_keywords)
        """
        symptoms_lower = symptoms.lower()
        detected_keywords = []
        
        # Check for emergency keywords
        for keyword in self.emergency_keywords:
            if keyword.lower() in symptoms_lower:
                detected_keywords.append(keyword)
        
        if detected_keywords:
            return UrgencyLevel.EMERGENCY, detected_keywords
        
        # Check for urgent keywords
        for keyword in self.urgent_keywords:
            if keyword.lower() in symptoms_lower:
                detected_keywords.append(keyword)
        
        if detected_keywords:
            return UrgencyLevel.URGENT, detected_keywords
        
        # Check severity level
        if severity and severity >= 8:
            return UrgencyLevel.URGENT, ["high_severity"]
        elif severity and severity >= 6:
            return UrgencyLevel.MODERATE, ["moderate_severity"]
        
        return UrgencyLevel.LOW, []
    
    def generate_emergency_warning(self, detected_keywords: List[str]) -> str:
        """Generate emergency warning message"""
        if not detected_keywords:
            return None
        
        warning = "🚨 MEDICAL EMERGENCY DETECTED 🚨\n\n"
        warning += "Based on your symptoms, this appears to be a medical emergency.\n\n"
        warning += "IMMEDIATE ACTION REQUIRED:\n"
        warning += "• Call 911 or go to the nearest emergency room immediately\n"
        warning += "• Do not drive yourself if possible\n"
        warning += "• Stay calm and follow emergency operator instructions\n\n"
        warning += f"Emergency indicators detected: {', '.join(detected_keywords)}\n\n"
        warning += "This system cannot replace emergency medical care. Please seek immediate professional help."
        
        return warning
    
    def generate_urgent_warning(self, detected_keywords: List[str]) -> str:
        """Generate urgent warning message"""
        if not detected_keywords:
            return None
        
        warning = "⚠️ URGENT MEDICAL ATTENTION NEEDED ⚠️\n\n"
        warning += "Your symptoms require prompt medical evaluation.\n\n"
        warning += "RECOMMENDED ACTION:\n"
        warning += "• Contact your doctor immediately or visit urgent care\n"
        warning += "• If symptoms worsen, go to the emergency room\n"
        warning += "• Monitor your condition closely\n\n"
        warning += f"Urgent indicators detected: {', '.join(detected_keywords)}\n\n"
        warning += "Please consult with a healthcare professional as soon as possible."
        
        return warning
    
    def categorize_body_systems(self, symptoms: str) -> List[str]:
        """Categorize symptoms by affected body systems"""
        symptoms_lower = symptoms.lower()
        affected_systems = []
        
        for system, keywords in self.body_systems.items():
            for keyword in keywords:
                if keyword.lower() in symptoms_lower:
                    if system not in affected_systems:
                        affected_systems.append(system)
                    break
        
        return affected_systems if affected_systems else ["general"]
    
    def combine_triage_results(
        self,
        keyword_urgency: UrgencyLevel,
        llm_urgency: str,
        confidence: float
    ) -> UrgencyLevel:
        """
        Combine keyword-based and LLM-based triage results
        """
        # Convert LLM urgency string to enum
        llm_urgency_enum = self._parse_urgency_string(llm_urgency)
        
        # If keyword detection found emergency, prioritize that
        if keyword_urgency == UrgencyLevel.EMERGENCY:
            return UrgencyLevel.EMERGENCY
        
        # If LLM found emergency and confidence is high, use that
        if llm_urgency_enum == UrgencyLevel.EMERGENCY and confidence > 0.7:
            return UrgencyLevel.EMERGENCY
        
        # If keyword detection found urgent, prioritize that
        if keyword_urgency == UrgencyLevel.URGENT:
            return UrgencyLevel.URGENT
        
        # Use the higher urgency level between keyword and LLM
        if llm_urgency_enum == UrgencyLevel.EMERGENCY:
            return UrgencyLevel.URGENT  # Downgrade to urgent for safety
        elif llm_urgency_enum == UrgencyLevel.URGENT:
            return UrgencyLevel.URGENT
        elif llm_urgency_enum == UrgencyLevel.MODERATE:
            return UrgencyLevel.MODERATE
        else:
            return UrgencyLevel.LOW
    
    def _parse_urgency_string(self, urgency_str: str) -> UrgencyLevel:
        """Parse urgency string to enum"""
        if not urgency_str:
            return UrgencyLevel.LOW
        
        urgency_lower = urgency_str.lower()
        
        if "emergency" in urgency_lower:
            return UrgencyLevel.EMERGENCY
        elif "urgent" in urgency_lower:
            return UrgencyLevel.URGENT
        elif "moderate" in urgency_lower or "routine" in urgency_lower:
            return UrgencyLevel.MODERATE
        else:
            return UrgencyLevel.LOW
    
    def assess_confidence(self, symptoms: str, conditions: List[dict]) -> float:
        """
        Assess confidence in the assessment based on symptom clarity and condition matches
        """
        if not symptoms or len(symptoms.strip()) < 10:
            return 0.3  # Low confidence for vague symptoms
        
        if not conditions:
            return 0.4  # Low confidence if no conditions identified
        
        # Higher confidence if symptoms are detailed
        confidence = 0.5
        
        # Increase confidence based on symptom detail
        if len(symptoms.split()) > 10:
            confidence += 0.1
        
        # Increase confidence if conditions have high probability
        max_condition_prob = max([c.get('probability', 0) for c in conditions], default=0)
        confidence += max_condition_prob * 0.3
        
        # Increase confidence if multiple conditions agree
        if len(conditions) > 1:
            avg_prob = sum([c.get('probability', 0) for c in conditions]) / len(conditions)
            if avg_prob > 0.5:
                confidence += 0.1
        
        return min(confidence, 1.0)  # Cap at 1.0


# Singleton instance
_triage_service = None


def get_triage_service() -> TriageService:
    """Get or create triage service instance"""
    global _triage_service
    if _triage_service is None:
        _triage_service = TriageService()
    return _triage_service