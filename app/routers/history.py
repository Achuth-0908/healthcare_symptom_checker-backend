"""
History Router - Endpoints for conversation history and export
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime

from app.models import (
    ConversationHistory, ExportRequest, ExportResponse,
    ConversationTurn, Assessment, ConversationModel, SessionModel
)
from app.database import get_db
from app.services.conversation_manager import get_conversation_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get complete conversation history for a session
    """
    try:
        # Get from database
        db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        conversations = db.query(ConversationModel).filter(
            ConversationModel.session_id == session_id
        ).order_by(ConversationModel.turn_number).all()
        
        # Build conversation turns
        turns = []
        for conv in conversations:
            assessment_data = json.loads(conv.assistant_response) if conv.assistant_response else {}
            assessment = Assessment(**assessment_data)
            
            turn = ConversationTurn(
                timestamp=conv.timestamp,
                user_message=conv.user_message,
                assistant_response=assessment,
                severity_reported=conv.severity_reported
            )
            turns.append(turn)
        
        # Get final assessment
        final_assessment = turns[-1].assistant_response if turns else None
        
        # Build patient info
        patient_info = {
            "age": db_session.age,
            "sex": db_session.sex,
            "medical_history": json.loads(db_session.medical_history) if db_session.medical_history else [],
            "medications": json.loads(db_session.medications) if db_session.medications else [],
            "allergies": json.loads(db_session.allergies) if db_session.allergies else []
        }
        
        return ConversationHistory(
            session_id=session_id,
            created_at=db_session.created_at,
            turns=turns,
            total_turns=len(turns),
            last_updated=db_session.updated_at or db_session.created_at,
            summary=f"Session with {len(turns)} conversation turns"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export", response_model=ExportResponse)
async def export_conversation(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """
    Export conversation in specified format
    """
    try:
        # Get conversation history
        db_session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        conversations = db.query(ConversationModel).filter(
            ConversationModel.session_id == request.session_id
        ).order_by(ConversationModel.turn_number).all()
        
        if request.format == "json":
            content = _export_json(db_session, conversations)
        elif request.format == "text":
            content = _export_text(db_session, conversations)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
        
        return ExportResponse(
            session_id=request.session_id,
            format=request.format,
            content=content,
            generated_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _export_json(db_session: SessionModel, conversations: list) -> str:
    """Export as JSON"""
    data = {
        "session_id": db_session.id,
        "created_at": db_session.created_at.isoformat(),
        "patient_info": {
            "age": db_session.age,
            "sex": db_session.sex,
            "medical_history": json.loads(db_session.medical_history) if db_session.medical_history else [],
            "medications": json.loads(db_session.medications) if db_session.medications else [],
            "allergies": json.loads(db_session.allergies) if db_session.allergies else []
        },
        "conversations": []
    }
    
    for conv in conversations:
        data["conversations"].append({
            "turn_number": conv.turn_number,
            "timestamp": conv.timestamp.isoformat(),
            "user_message": conv.user_message,
            "severity_reported": conv.severity_reported,
            "urgency_level": conv.urgency_level,
            "assessment": json.loads(conv.assistant_response) if conv.assistant_response else {}
        })
    
    return json.dumps(data, indent=2)


def _export_text(db_session: SessionModel, conversations: list) -> str:
    """Export as human-readable text"""
    lines = []
    lines.append("=" * 80)
    lines.append("SYMPTOM CHECKER CONVERSATION SUMMARY")
    lines.append("=" * 80)
    lines.append(f"\nSession ID: {db_session.id}")
    lines.append(f"Date: {db_session.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Status: {db_session.status}")
    
    # Patient information
    lines.append("\n" + "-" * 80)
    lines.append("PATIENT INFORMATION")
    lines.append("-" * 80)
    if db_session.age:
        lines.append(f"Age: {db_session.age}")
    if db_session.sex:
        lines.append(f"Sex: {db_session.sex}")
    if db_session.medical_history:
        medical_history = json.loads(db_session.medical_history) if db_session.medical_history else []
        lines.append(f"Medical History: {', '.join(medical_history)}")
    if db_session.medications:
        medications = json.loads(db_session.medications) if db_session.medications else []
        lines.append(f"Medications: {', '.join(medications)}")
    if db_session.allergies:
        allergies = json.loads(db_session.allergies) if db_session.allergies else []
        lines.append(f"Allergies: {', '.join(allergies)}")
    
    # Conversations
    lines.append("\n" + "-" * 80)
    lines.append("CONVERSATION")
    lines.append("-" * 80)
    
    for conv in conversations:
        lines.append(f"\n[Turn {conv.turn_number}] {conv.timestamp.strftime('%H:%M:%S')}")
        lines.append(f"Urgency Level: {conv.urgency_level}")
        if conv.severity_reported:
            lines.append(f"Severity Reported: {conv.severity_reported}/10")
        lines.append(f"\nPatient: {conv.user_message}")
        
        assessment = json.loads(conv.assistant_response) if conv.assistant_response else {}
        lines.append("\nAssessment:")
        
        if assessment.get('emergency_warning'):
            lines.append(f"\n⚠️  {assessment['emergency_warning']}")
        
        if assessment.get('probable_conditions'):
            lines.append("\nPossible Conditions:")
            for cond in assessment['probable_conditions']:
                confidence = cond.get('confidence', 0) * 100
                lines.append(f"  - {cond['name']} ({confidence:.0f}% confidence)")
        
        if assessment.get('reasoning'):
            lines.append(f"\nReasoning: {assessment['reasoning']}")
        
        if assessment.get('recommendations'):
            lines.append("\nRecommendations:")
            for rec in assessment['recommendations']:
                lines.append(f"  • {rec}")
        
        if assessment.get('clarifying_questions'):
            lines.append("\nFollow-up Questions:")
            for q in assessment['clarifying_questions']:
                lines.append(f"  ? {q}")
        
        lines.append("\n" + "-" * 40)
    
    # Final summary
    if conversations:
        final_conv = conversations[-1]
        lines.append("\n" + "=" * 80)
        lines.append("FINAL ASSESSMENT")
        lines.append("=" * 80)
        lines.append(f"Final Urgency Level: {final_conv.urgency_level}")
        
        assessment = json.loads(final_conv.assistant_response) if final_conv.assistant_response else {}
        if assessment.get('probable_conditions'):
            lines.append("\nMost Likely Conditions:")
            for cond in assessment['probable_conditions'][:3]:
                confidence = cond.get('confidence', 0) * 100
                lines.append(f"  {confidence:.0f}% - {cond['name']}")
        
        lines.append(f"\n{assessment.get('disclaimer', '')}")
    
    lines.append("\n" + "=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    lines.append("\nThis report is for informational purposes only.")
    lines.append("Please consult with a healthcare professional for proper medical advice.")
    
    return "\n".join(lines)