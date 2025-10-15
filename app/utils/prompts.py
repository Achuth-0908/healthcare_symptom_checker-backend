"""
Medical prompts for LLM services
"""

def create_symptom_analysis_prompt(
    symptoms: str,
    duration: str = None,
    severity: int = None,
    medical_history: list = None,
    retrieved_conditions: str = None,
    conversation_context: str = None
) -> str:
    """Create comprehensive symptom analysis prompt for Gemini"""
    
    prompt = f"""
You are a medical triage assistant. Analyze the following symptoms and provide a structured assessment.

PATIENT INFORMATION:
- Symptoms: {symptoms}
- Duration: {duration or "Not specified"}
- Severity (1-10): {severity or "Not specified"}
- Medical History: {', '.join(medical_history) if medical_history else "None provided"}
- Conversation Context: {conversation_context or "None"}

RELEVANT MEDICAL CONDITIONS:
{retrieved_conditions or "No specific conditions retrieved"}

ANALYSIS REQUIREMENTS:
1. Assess urgency level: EMERGENCY, URGENT, ROUTINE, or SELF_CARE
2. Identify probable conditions with confidence scores
3. Generate clarifying questions to gather more information
4. Provide evidence-based reasoning
5. Suggest appropriate recommendations
6. Identify affected body systems
7. Include appropriate disclaimers

RESPONSE FORMAT (JSON):
{{
    "urgency": "EMERGENCY|URGENT|ROUTINE|SELF_CARE",
    "emergency_warning": "string or null",
    "probable_conditions": [
        {{
            "name": "condition name",
            "probability": 0.0-1.0,
            "description": "brief description",
            "urgency_level": "EMERGENCY|URGENT|ROUTINE|SELF_CARE",
            "recommendations": ["recommendation1", "recommendation2"]
        }}
    ],
    "confidence_scores": {{
        "overall_confidence": 0.0-1.0,
        "condition_confidence": 0.0-1.0
    }},
    "clarifying_questions": [
        "question1",
        "question2",
        "question3"
    ],
    "reasoning": "detailed reasoning for the assessment",
    "recommendations": [
        "immediate action 1",
        "immediate action 2"
    ],
    "body_systems_affected": [
        "system1",
        "system2"
    ],
    "disclaimer": "appropriate medical disclaimer"
}}

SAFETY GUIDELINES:
- If ANY emergency symptoms are present, set urgency to EMERGENCY
- Always include appropriate disclaimers
- Recommend immediate medical attention for emergencies
- Be conservative in assessments
- Focus on patient safety above all else

Analyze the symptoms now and provide your assessment:
"""
    return prompt


def create_questions_prompt(
    symptoms: str,
    conditions: list,
    previous_questions: list
) -> str:
    """Create prompt for generating clarifying questions using Groq"""
    
    prompt = f"""
You are a medical assistant generating clarifying questions to better understand a patient's symptoms.

CURRENT SYMPTOMS: {symptoms}

POSSIBLE CONDITIONS: {', '.join(conditions) if conditions else "None identified"}

PREVIOUS QUESTIONS ASKED: {', '.join(previous_questions) if previous_questions else "None"}

Generate 2-3 specific, helpful clarifying questions that will help differentiate between possible conditions and assess urgency. Questions should be:

1. Clear and easy to understand
2. Specific to the symptoms mentioned
3. Helpful for medical assessment
4. Not repetitive of previous questions

Format as a simple list, one question per line:
"""
    return prompt


def create_emergency_detection_prompt(symptoms: str) -> str:
    """Create prompt for emergency detection"""
    
    prompt = f"""
Analyze these symptoms for emergency indicators:

SYMPTOMS: {symptoms}

EMERGENCY INDICATORS TO CHECK:
- Chest pain or pressure
- Difficulty breathing
- Severe bleeding
- Loss of consciousness
- Severe allergic reactions
- Signs of stroke
- Signs of heart attack
- Severe head injury
- Poisoning or overdose
- Severe burns
- Suicidal thoughts

Respond with:
1. EMERGENCY_LEVEL: EMERGENCY, URGENT, or SAFE
2. DETECTED_KEYWORDS: list of emergency keywords found
3. IMMEDIATE_ACTION: what the patient should do right now

Format as JSON:
{{
    "emergency_level": "EMERGENCY|URGENT|SAFE",
    "detected_keywords": ["keyword1", "keyword2"],
    "immediate_action": "specific action to take"
}}
"""
    return prompt


def create_triage_prompt(symptoms: str, severity: int = None) -> str:
    """Create prompt for medical triage assessment"""
    
    prompt = f"""
Perform medical triage assessment for the following symptoms:

SYMPTOMS: {symptoms}
SEVERITY (1-10): {severity or "Not specified"}

TRIAGE LEVELS:
- EMERGENCY: Life-threatening, requires immediate medical attention
- URGENT: Serious but not immediately life-threatening, see doctor within hours
- ROUTINE: Non-urgent, can wait for appointment
- SELF_CARE: Minor symptoms, can be managed at home

Assess and provide:
1. Triage level
2. Reasoning
3. Recommended timeframe for care
4. Red flags to watch for

Format as JSON:
{{
    "triage_level": "EMERGENCY|URGENT|ROUTINE|SELF_CARE",
    "reasoning": "explanation of triage decision",
    "timeframe": "when to seek care",
    "red_flags": ["warning sign 1", "warning sign 2"]
}}
"""
    return prompt