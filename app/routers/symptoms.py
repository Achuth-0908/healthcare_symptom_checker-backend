"""
Symptoms Router - Main endpoints for symptom checking
Fixed imports for PostgreSQL
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session as DBSession
import logging
import json
from datetime import datetime

from app.models import (
    SymptomStartRequest,
    SymptomMessage,
    SymptomResponse,
    SessionResponse,
    Assessment,
    Condition,
    UrgencyLevel,
    SessionModel,
    ConversationModel,
    AuditLogModel
)
from app.database import get_db
from app.services.llm_service import get_llm_service
from app.services.enhanced_rag_service import EnhancedRAGService
from app.services.triage_service import get_triage_service
from app.services.conversation_manager import get_conversation_manager
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/start", response_model=SessionResponse)
async def start_symptom_check(
    request: SymptomStartRequest,
    db: DBSession = Depends(get_db)
):
    """
    Start a new symptom checking session
    """
    try:
        # Create conversation session
        conversation_manager = get_conversation_manager()
        session_id = conversation_manager.create_session(
            age=request.age,
            sex=request.sex,
            medical_history=request.medical_history,
            medications=request.medications,
            allergies=request.allergies
        )
        
        # Store in PostgreSQL database
        db_session = SessionModel(
            id=session_id,
            age=request.age,
            sex=request.sex,
            medical_history=json.dumps(request.medical_history or []),
            medications=json.dumps(request.medications or []),
            allergies=json.dumps(request.allergies or []),
            status="active",
            turn_count=0
        )
        db.add(db_session)
        
        # Create audit log
        audit = AuditLogModel(
            session_id=session_id,
            event_type="start",
            audit_metadata=json.dumps({
                "age": request.age,
                "has_medical_history": bool(request.medical_history)
            })
        )
        db.add(audit)
        
        db.commit()
        
        logger.info(f"Started new session: {session_id}")
        
        return SessionResponse(
            session_id=str(session_id),
            message="Session created successfully. Please describe your symptoms.",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to start session: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=SymptomResponse)
async def process_symptom_message(
    message: SymptomMessage,
    request: Request,
    db: DBSession = Depends(get_db)
):
    """
    Process a symptom message and return assessment
    """
    try:
        # Get services
        conversation_manager = get_conversation_manager()
        rag_service = request.app.state.rag_service
        llm_service = get_llm_service()
        triage_service = get_triage_service()
        
        # Get conversation session
        session = conversation_manager.get_session(message.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.should_end_conversation():
            raise HTTPException(
                status_code=400,
                detail="Session has ended. Please start a new session."
            )
        
        # Quick triage for emergency detection
        keyword_urgency, detected_keywords = triage_service.quick_triage(
            message.message,
            message.severity
        )
        
        # If emergency detected, return immediately
        if keyword_urgency == UrgencyLevel.EMERGENCY:
            emergency_warning = triage_service.generate_emergency_warning(detected_keywords)
            
            assessment = Assessment(
                urgency=UrgencyLevel.EMERGENCY,
                emergency_warning=emergency_warning,
                probable_conditions=[],
                clarifying_questions=[],
                reasoning="Emergency keywords detected in symptoms. Immediate medical attention required.",
                recommendations=[
                    "Call 911 immediately",
                    "Do not drive yourself",
                    "Stay calm and wait for emergency services"
                ],
                body_systems_affected=triage_service.categorize_body_systems(message.message),
                disclaimer="This is a medical emergency. Call 911 now."
            )
            
            # Log the turn
            conversation_manager.add_turn(
                message.session_id,
                message.message,
                assessment,
                message.severity
            )
            
            # Save to PostgreSQL database
            conversation = ConversationModel(
                session_id=message.session_id,
                turn_number=session.turn_count,
                user_message=message.message,
                assistant_response=json.dumps(assessment.model_dump()),
                severity_reported=message.severity,
                urgency_level=UrgencyLevel.EMERGENCY.value
            )
            db.add(conversation)
            
            # Update session turn count
            db_session = db.query(SessionModel).filter(
                SessionModel.id == message.session_id
            ).first()
            if db_session:
                db_session.turn_count = session.turn_count
                db_session.updated_at = datetime.utcnow()
            
            # Audit log
            audit = AuditLogModel(
                session_id=message.session_id,
                event_type="emergency_detected",
                urgency_level=UrgencyLevel.EMERGENCY.value,
                emergency_keywords_detected=json.dumps(detected_keywords),
                audit_metadata=json.dumps({"immediate_warning": True})
            )
            db.add(audit)
            db.commit()
            
            return SymptomResponse(
                session_id=message.session_id,
                assessment=assessment,
                conversation_turn=session.turn_count,
                timestamp=datetime.utcnow()
            )
        
        # Retrieve relevant conditions using Enhanced RAG
        if rag_service:
            retrieved_conditions = await rag_service.retrieve_relevant_conditions(
                message.message, 
                top_k=settings.TOP_K_RETRIEVAL
            )
            # Format retrieved conditions for LLM
            formatted_conditions = []
            for condition in retrieved_conditions:
                formatted_conditions.append({
                    'content': condition.get('content', ''),
                    'metadata': condition.get('metadata', {}),
                    'similarity_score': condition.get('similarity_score', 0.0)
                })
        else:
            logger.warning("RAG service not available, using empty conditions")
            formatted_conditions = []
        
        # Get conversation context
        conversation_context = session.get_conversation_context()
        
        # Use LLM to analyze symptoms
        llm_response = llm_service.analyze_symptoms(
            symptoms=message.message,
            duration=message.duration,
            severity=message.severity,
            medical_history=session.medical_history,
            retrieved_conditions=formatted_conditions,
            conversation_context=conversation_context
        )
        
        # Parse LLM response into Assessment
        conditions = []
        for cond_data in llm_response.get('probable_conditions', []):
            # Ensure urgency_level is lowercase and valid
            if 'urgency_level' in cond_data:
                cond_data['urgency_level'] = cond_data['urgency_level'].lower()
            # Convert to dictionary for Assessment model
            condition_dict = {
                'name': cond_data.get('name', ''),
                'probability': cond_data.get('probability', 0.0),
                'description': cond_data.get('description', ''),
                'urgency_level': cond_data.get('urgency_level', 'routine'),
                'recommendations': cond_data.get('recommendations', [])
            }
            conditions.append(condition_dict)
        
        # Combine triage results
        llm_urgency = llm_response.get('urgency', 'routine').lower()
        confidence_scores = llm_response.get('confidence_scores', {})
        average_confidence = sum(confidence_scores.values()) / max(len(confidence_scores), 1)
        
        final_urgency = triage_service.combine_triage_results(
            keyword_urgency,
            llm_urgency,
            average_confidence
        )
        
        # Ensure final_urgency is a valid UrgencyLevel
        if isinstance(final_urgency, str):
            final_urgency = final_urgency.lower()
            if final_urgency not in ['emergency', 'urgent', 'moderate', 'low', 'routine', 'self_care']:
                final_urgency = 'routine'
            final_urgency = UrgencyLevel(final_urgency)
        
        # Generate warnings if needed
        emergency_warning = None
        if final_urgency == UrgencyLevel.EMERGENCY:
            emergency_warning = triage_service.generate_emergency_warning(detected_keywords)
        elif final_urgency == UrgencyLevel.URGENT:
            emergency_warning = triage_service.generate_urgent_warning(detected_keywords)
        
        # Build assessment
        assessment = Assessment(
            urgency=final_urgency,
            emergency_warning=emergency_warning or llm_response.get('emergency_warning'),
            probable_conditions=conditions,
            clarifying_questions=llm_response.get('clarifying_questions', []),
            reasoning=llm_response.get('reasoning', ''),
            recommendations=llm_response.get('recommendations', []),
            body_systems_affected=llm_response.get('body_systems_affected', []) or 
                                 triage_service.categorize_body_systems(message.message),
            disclaimer=llm_response.get('disclaimer', 
                                       'This is not a medical diagnosis. Please consult a healthcare professional.')
        )
        
        # Add turn to conversation
        conversation_manager.add_turn(
            message.session_id,
            message.message,
            assessment,
            message.severity
        )
        
        # Save to PostgreSQL database
        conversation = ConversationModel(
            session_id=message.session_id,
            turn_number=session.turn_count,
            user_message=message.message,
            assistant_response=json.dumps(assessment.model_dump()),
            severity_reported=message.severity,
            urgency_level=final_urgency.value
        )
        db.add(conversation)
        
        # Update session turn count
        db_session = db.query(SessionModel).filter(
            SessionModel.id == message.session_id
        ).first()
        if db_session:
            db_session.turn_count = session.turn_count
            db_session.updated_at = datetime.utcnow()
        
        # Audit log
        audit = AuditLogModel(
            session_id=message.session_id,
            event_type="message",
            urgency_level=final_urgency.value,
            emergency_keywords_detected=json.dumps(detected_keywords) if detected_keywords else None,
            confidence_scores=json.dumps(confidence_scores),
            audit_metadata=json.dumps({
                "turn_number": session.turn_count,
                "conditions_count": len(conditions)
            })
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"Processed message for session {message.session_id}, urgency: {final_urgency.value}")
        
        return SymptomResponse(
            session_id=message.session_id,
            assessment=assessment,
            conversation_turn=session.turn_count,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process message: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.post("/end/{session_id}")
async def end_session(
    session_id: str,
    db: DBSession = Depends(get_db)
):
    """
    End a symptom checking session
    """
    try:
        conversation_manager = get_conversation_manager()
        session = conversation_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        conversation_manager.end_session(session_id)
        
        # Update PostgreSQL database
        db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if db_session:
            db_session.status = "completed"
            db_session.updated_at = datetime.utcnow()
            db.commit()
        
        return {
            "message": "Session ended successfully",
            "session_id": session_id,
            "summary": session.get_summary()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))