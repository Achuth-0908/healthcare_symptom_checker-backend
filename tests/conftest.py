"""
Pytest configuration and fixtures
"""

import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from main import app
from app.database import get_db
from app.models import Base


@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Create test database URL
    database_url = f"sqlite:///{db_path}"
    
    # Create engine
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def db_session(test_db):
    """Create database session for testing"""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    with patch('app.services.llm_service.get_llm_service') as mock:
        mock_service = mock.return_value
        mock_service.analyze_symptoms.return_value = {
            "urgency": "ROUTINE",
            "probable_conditions": [],
            "confidence_scores": {"overall_confidence": 0.5},
            "clarifying_questions": ["How long have you had these symptoms?"],
            "reasoning": "Based on the symptoms described...",
            "recommendations": ["Monitor symptoms", "See doctor if they worsen"],
            "body_systems_affected": ["general"],
            "disclaimer": "This is not a medical diagnosis."
        }
        yield mock_service


@pytest.fixture
def mock_rag_service():
    """Mock Enhanced RAG service"""
    with patch('app.services.enhanced_rag_service.EnhancedRAGService') as mock:
        mock_service = mock.return_value
        mock_service.retrieve_relevant_conditions.return_value = []
        mock_service.get_service_status.return_value = {
            'initialized': True,
            'jina_service_available': True,
            'knowledge_base_loaded': True,
            'research_papers_count': 10,
            'guidelines_count': 8,
            'clinical_conditions_count': 15
        }
        yield mock_service


@pytest.fixture
def mock_triage_service():
    """Mock triage service"""
    with patch('app.services.triage_service.get_triage_service') as mock:
        mock_service = mock.return_value
        mock_service.quick_triage.return_value = ("LOW", [])
        mock_service.combine_triage_results.return_value = "LOW"
        mock_service.categorize_body_systems.return_value = ["general"]
        mock_service.generate_emergency_warning.return_value = None
        yield mock_service


@pytest.fixture
def mock_conversation_manager():
    """Mock conversation manager"""
    with patch('app.services.conversation_manager.get_conversation_manager') as mock:
        mock_manager = mock.return_value
        
        # Mock session
        mock_session = mock_manager.get_session.return_value
        mock_session.should_end_conversation.return_value = False
        mock_session.turn_count = 0
        mock_session.get_conversation_context.return_value = "No previous conversation."
        mock_session.medical_history = []
        mock_session.get_summary.return_value = {"message": "Session ended"}
        
        yield mock_manager


@pytest.fixture
def sample_symptom_request():
    """Sample symptom start request"""
    return {
        "age": 30,
        "sex": "male",
        "medical_history": ["diabetes"],
        "medications": ["metformin"],
        "allergies": ["penicillin"]
    }


@pytest.fixture
def sample_symptom_message():
    """Sample symptom message"""
    return {
        "session_id": "test-session-id",
        "message": "I have a headache and feel tired",
        "duration": "2 days",
        "severity": 5
    }


@pytest.fixture
def emergency_symptom_message():
    """Emergency symptom message"""
    return {
        "session_id": "test-session-id",
        "message": "I have severe chest pain and can't breathe",
        "severity": 10
    }


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY": "test-gemini-key",
        "GROQ_API_KEY": "test-groq-key",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "DEBUG": "true"
    }):
        yield
