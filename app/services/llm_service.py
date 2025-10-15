"""
LLM Service integrating both Gemini and Groq
Gemini for complex medical reasoning, Groq for fast responses
"""

import google.generativeai as genai
from groq import Groq
import json
import logging
from typing import Dict, Any, Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Unified LLM service supporting both Gemini and Groq
    """
    
    def __init__(self):
        self.gemini_client = None
        self.groq_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize both LLM clients"""
        try:
            # Initialize Gemini
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_client = genai.GenerativeModel(settings.GEMINI_MODEL)
                logger.info("Gemini client initialized")
            else:
                logger.warning("Gemini API key not provided")
            
            # Initialize Groq
            if settings.GROQ_API_KEY:
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("Groq client initialized")
            else:
                logger.warning("Groq API key not provided")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_with_gemini(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response using Gemini (best for complex medical reasoning)
        """
        if not self.gemini_client:
            raise ValueError("Gemini client not initialized")
        
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = self.gemini_client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_with_groq(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response using Groq (best for fast responses)
        """
        if not self.groq_client:
            raise ValueError("Groq client not initialized")
        
        try:
            completion = self.groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical triage assistant. Provide accurate, safety-focused responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        use_primary: bool = True,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate response with automatic fallback
        """
        primary_llm = settings.PRIMARY_LLM if use_primary else settings.FALLBACK_LLM
        
        try:
            if primary_llm == "gemini":
                return self.generate_with_gemini(prompt, temperature, max_tokens)
            else:
                return self.generate_with_groq(prompt, temperature, max_tokens)
                
        except Exception as e:
            logger.warning(f"Primary LLM ({primary_llm}) failed, trying fallback: {e}")
            
            # Try fallback
            fallback_llm = settings.FALLBACK_LLM
            try:
                if fallback_llm == "gemini":
                    return self.generate_with_gemini(prompt, temperature, max_tokens)
                else:
                    return self.generate_with_groq(prompt, temperature, max_tokens)
            except Exception as fallback_error:
                logger.error(f"Fallback LLM also failed: {fallback_error}")
                raise
    
    def analyze_symptoms(
        self,
        symptoms: str,
        duration: Optional[str],
        severity: Optional[int],
        medical_history: List[str],
        retrieved_conditions: str,
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze symptoms using Gemini for complex medical reasoning
        """
        from app.utils.prompts import create_symptom_analysis_prompt
        
        prompt = create_symptom_analysis_prompt(
            symptoms=symptoms,
            duration=duration,
            severity=severity,
            medical_history=medical_history,
            retrieved_conditions=retrieved_conditions,
            conversation_context=conversation_context
        )
        
        # Use Gemini for complex medical analysis
        response = self.generate_with_gemini(
            prompt,
            temperature=settings.TEMPERATURE_ANALYSIS,
            max_tokens=2048
        )
        
        # Parse JSON response
        try:
            # Extract JSON from markdown if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Log the response for debugging
            logger.info(f"LLM response: {response[:500]}...")
            
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response}")
            
            # Return a safe default response
            return {
                "urgency": "ROUTINE",
                "emergency_warning": None,
                "probable_conditions": [],
                "confidence_scores": {},
                "clarifying_questions": [
                    "Can you describe your symptoms in more detail?",
                    "How long have you been experiencing these symptoms?"
                ],
                "reasoning": "Unable to process the symptom analysis. Please provide more details.",
                "recommendations": ["Consult with a healthcare provider for proper evaluation."],
                "disclaimer": "This is not a medical diagnosis. Please consult a healthcare professional."
            }
    
    def generate_clarifying_questions(
        self,
        symptoms: str,
        conditions: List[str],
        previous_questions: List[str]
    ) -> List[str]:
        """
        Generate clarifying questions using Groq for fast response
        """
        from app.utils.prompts import create_questions_prompt
        
        prompt = create_questions_prompt(symptoms, conditions, previous_questions)
        
        # Use Groq for quick question generation
        response = self.generate_with_groq(
            prompt,
            temperature=settings.TEMPERATURE_QUESTIONS,
            max_tokens=512
        )
        
        # Parse questions from response
        questions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean the question
                question = line.lstrip('0123456789.-•) ').strip()
                if question:
                    questions.append(question)
        
        return questions[:3]  # Return max 3 questions


# Singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service