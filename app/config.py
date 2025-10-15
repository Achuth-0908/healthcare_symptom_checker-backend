"""
Application configuration settings
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration"""
    
    # Core settings
    APP_NAME: str = "Healthcare Symptom Checker"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API keys
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    JINA_API_KEY: str 
    
    # LLM models
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    PRIMARY_LLM: str = "gemini"
    FALLBACK_LLM: str = "groq"
    
    # Generation settings
    TEMPERATURE_ANALYSIS: float = 0.3
    TEMPERATURE_QUESTIONS: float = 0.5
    MAX_TOKENS: int = 2048
    
    # Database
    DATABASE_URL: str = "postgresql://health_symptom_checker_user:4IgnXn7S7lnErOpG0GKDpmUw89voW5C3@dpg-d3neevodl3ps73ep6m5g-a/health_symptom_checker"
    POSTGRES_HOST: str = "dpg-d3neevodl3ps73ep6m5g-a"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "health_symptom_checker"
    POSTGRES_USER: str = "health_symptom_checker_user"
    POSTGRES_PASSWORD: str = "4IgnXn7S7lnErOpG0GKDpmUw89voW5C3"
    
    @property
    def database_url(self) -> str:
        return self.DATABASE_URL
    
    # Connection pool
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    
    # Vector database
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL: str = "jina-embeddings-v2-base-en"  # Lighter model name
    KNOWLEDGE_BASE_PATH: str = "./app/data/medical_kb.json"
    MEDICAL_RESEARCH_KB_PATH: str = "./app/data/medical_research_kb.json"
    
    # RAG settings
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    # API timeout settings
    JINA_API_TIMEOUT: int = 60
    JINA_API_MAX_RETRIES: int = 3
    LLM_API_TIMEOUT: int = 120
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 50
    RATE_LIMIT_WINDOW: int = 3600
    
    # Session management
    SESSION_TIMEOUT: int = 3600
    MAX_CONVERSATION_TURNS: int = 20
    
    # Safety thresholds
    EMERGENCY_DETECTION_THRESHOLD: float = 0.85
    CONFIDENCE_THRESHOLD_LOW: float = 0.3
    CONFIDENCE_THRESHOLD_HIGH: float = 0.7
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "symptom_checker.log"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True


# Initialize settings
settings = Settings()


# Emergency keywords for quick detection
EMERGENCY_KEYWORDS = [
    "chest pain", "crushing pain", "radiating pain", "squeezing chest",
    "difficulty breathing", "can't breathe", "gasping", "choking",
    "sudden severe headache", "worst headache", "thunderclap headache",
    "slurred speech", "face drooping", "arm weakness", "facial paralysis",
    "severe bleeding", "heavy bleeding", "hemorrhage", "uncontrolled bleeding",
    "unconscious", "loss of consciousness", "passed out", "unresponsive",
    "severe allergic reaction", "anaphylaxis", "throat swelling", "airway closing",
    "suicidal", "want to die", "kill myself", "end my life",
    "seizure", "convulsions", "fitting",
    "severe abdominal pain", "rigid abdomen", "board-like abdomen",
    "severe burn", "large burn", "third degree burn",
    "poisoning", "overdose", "swallowed poison",
    "severe head injury", "head trauma", "skull fracture",
    "stroke symptoms", "stroke", "brain attack",
    "heart attack", "myocardial infarction"
]

# Urgent keywords
URGENT_KEYWORDS = [
    "high fever", "fever over 103", "persistent fever", "fever 104",
    "severe pain", "pain 8", "pain 9", "pain 10", "unbearable pain",
    "persistent vomiting", "can't keep anything down", "vomiting blood",
    "blood in stool", "blood in urine", "coughing blood", "bloody discharge",
    "severe injury", "broken bone", "deep cut", "deep wound",
    "severe dehydration", "very dehydrated", "no urination",
    "severe rash", "spreading rash", "painful rash",
    "eye injury", "vision loss", "sudden vision change", "eye trauma",
    "severe swelling", "rapid swelling", "swelling spreading"
]

# Body systems for categorization
BODY_SYSTEMS = {
    "respiratory": [
        "breathing", "cough", "lungs", "chest", "wheezing",
        "shortness of breath", "respiratory", "airway"
    ],
    "cardiovascular": [
        "heart", "chest pain", "palpitations", "pulse",
        "blood pressure", "circulation", "cardiac"
    ],
    "gastrointestinal": [
        "stomach", "nausea", "vomiting", "diarrhea", "abdominal",
        "bowel", "intestinal", "digestive", "gastric"
    ],
    "neurological": [
        "headache", "dizziness", "confusion", "numbness", "tingling",
        "weakness", "seizure", "neurological", "brain"
    ],
    "musculoskeletal": [
        "pain", "joint", "muscle", "back", "sprain",
        "fracture", "bone", "tendon", "ligament"
    ],
    "dermatological": [
        "skin", "rash", "itching", "lesion", "wound",
        "burn", "cut", "bruise", "swelling"
    ],
    "mental_health": [
        "anxiety", "depression", "stress", "panic", "mood",
        "mental", "psychological", "psychiatric"
    ],
    "general": [
        "fever", "fatigue", "weakness", "weight loss",
        "malaise", "tired", "exhausted"
    ]
}