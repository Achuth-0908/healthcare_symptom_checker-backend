"""
RAG (Retrieval-Augmented Generation) Service
Uses ChromaDB for vector storage and retrieval
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
import json
import logging
from typing import List, Dict, Any, Optional
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation service for medical knowledge
    """
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_function = None
        self.knowledge_base = None
    
    def initialize(self):
        """Initialize ChromaDB and load medical knowledge base"""
        try:
            # Use ChromaDB's default embedding function (more memory efficient)
            # This avoids loading heavy sentence-transformers models
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name="medical_conditions",
                    embedding_function=self.embedding_function
                )
                logger.info("Loaded existing medical conditions collection")
            except:
                self.collection = self.client.create_collection(
                    name="medical_conditions",
                    embedding_function=self.embedding_function,
                    metadata={"description": "Medical conditions and symptoms"}
                )
                logger.info("Created new medical conditions collection")
                
                # Load and index knowledge base
                self._load_knowledge_base()
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise
    
    def _load_knowledge_base(self):
        """Load medical knowledge base from JSON file"""
        try:
            kb_path = settings.KNOWLEDGE_BASE_PATH
            
            # Check if knowledge base exists
            if not os.path.exists(kb_path):
                logger.warning(f"Knowledge base not found at {kb_path}, creating sample data")
                self._create_sample_knowledge_base(kb_path)
            
            # Load knowledge base
            with open(kb_path, 'r') as f:
                self.knowledge_base = json.load(f)
            
            # Index conditions into ChromaDB
            self._index_conditions()
            logger.info(f"Loaded and indexed {len(self.knowledge_base['conditions'])} conditions")
            
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            raise
    
    def _index_conditions(self):
        """Index medical conditions into vector database"""
        conditions = self.knowledge_base.get('conditions', [])
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, condition in enumerate(conditions):
            # Create searchable text from condition
            text = f"{condition['name']}. {condition['description']}. "
            text += f"Symptoms: {', '.join(condition['symptoms'])}. "
            text += f"Severity indicators: {', '.join(condition.get('severity_indicators', []))}."
            
            documents.append(text)
            metadatas.append({
                "name": condition['name'],
                "category": condition.get('category', 'general'),
                "urgency_base": condition.get('urgency_base', 'ROUTINE')
            })
            ids.append(f"condition_{idx}")
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            self.collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
    
    def _create_sample_knowledge_base(self, path: str):
        """Create sample medical knowledge base"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        sample_kb = {
            "conditions": [
                {
                    "name": "Common Cold",
                    "category": "respiratory",
                    "description": "Viral infection of the upper respiratory tract",
                    "symptoms": ["runny nose", "congestion", "sneezing", "sore throat", "cough", "mild fever"],
                    "severity_indicators": ["fever over 101F", "symptoms lasting over 10 days"],
                    "red_flags": ["difficulty breathing", "severe headache", "chest pain"],
                    "urgency_base": "SELF_CARE",
                    "duration": "7-10 days",
                    "self_care": ["rest", "fluids", "over-the-counter medications"],
                    "see_doctor_if": ["symptoms worsen", "fever over 101F for 3+ days", "difficulty breathing"]
                },
                {
                    "name": "Influenza (Flu)",
                    "category": "respiratory",
                    "description": "Viral infection causing respiratory and systemic symptoms",
                    "symptoms": ["high fever", "body aches", "fatigue", "cough", "sore throat", "headache"],
                    "severity_indicators": ["fever over 103F", "severe muscle pain", "extreme fatigue"],
                    "red_flags": ["difficulty breathing", "chest pain", "confusion", "severe vomiting"],
                    "urgency_base": "ROUTINE",
                    "duration": "1-2 weeks",
                    "self_care": ["rest", "fluids", "fever reducers"],
                    "see_doctor_if": ["high-risk patient", "symptoms severe", "difficulty breathing"]
                },
                {
                    "name": "Heart Attack",
                    "category": "cardiovascular",
                    "description": "Blockage of blood flow to the heart muscle",
                    "symptoms": ["chest pain", "pain radiating to arm", "shortness of breath", "nausea", "cold sweat"],
                    "severity_indicators": ["crushing chest pain", "pain in jaw or arm", "difficulty breathing"],
                    "red_flags": ["all symptoms are red flags"],
                    "urgency_base": "EMERGENCY",
                    "duration": "immediate",
                    "self_care": [],
                    "see_doctor_if": ["call 911 immediately"]
                }
            ]
        }
        
        with open(path, 'w') as f:
            json.dump(sample_kb, f, indent=2)
    
    def retrieve_relevant_conditions(
        self,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve most relevant medical conditions based on symptoms
        """
        if top_k is None:
            top_k = settings.TOP_K_RETRIEVAL
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            conditions = []
            for idx, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                # Convert distance to similarity score (lower distance = higher similarity)
                similarity = 1 / (1 + distance)
                
                if similarity >= settings.SIMILARITY_THRESHOLD:
                    # Find full condition data
                    condition_name = metadata['name']
                    full_condition = self._get_full_condition(condition_name)
                    
                    if full_condition:
                        conditions.append({
                            "name": condition_name,
                            "similarity": similarity,
                            "category": metadata['category'],
                            "details": full_condition
                        })
            
            return conditions
            
        except Exception as e:
            logger.error(f"Failed to retrieve conditions: {e}")
            return []
    
    def _get_full_condition(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full condition details from knowledge base"""
        for condition in self.knowledge_base.get('conditions', []):
            if condition['name'] == name:
                return condition
        return None
    
    def format_retrieved_conditions(self, conditions: List[Dict[str, Any]]) -> str:
        """Format retrieved conditions for LLM prompt"""
        if not conditions:
            return "No specific conditions retrieved from knowledge base."
        
        formatted = []
        for cond in conditions:
            details = cond['details']
            text = f"\n**{cond['name']}** (Similarity: {cond['similarity']:.2f})\n"
            text += f"Category: {cond['category']}\n"
            text += f"Description: {details['description']}\n"
            text += f"Common symptoms: {', '.join(details['symptoms'])}\n"
            text += f"Base urgency: {details['urgency_base']}\n"
            
            if details.get('red_flags'):
                text += f"RED FLAGS: {', '.join(details['red_flags'])}\n"
            
            formatted.append(text)
        
        return "\n".join(formatted)
    
    def search_emergency_conditions(self, query: str) -> List[Dict[str, Any]]:
        """Search specifically for emergency conditions"""
        all_conditions = self.retrieve_relevant_conditions(query, top_k=10)
        
        # Filter for emergency conditions
        emergency_conditions = [
            c for c in all_conditions 
            if c['details'].get('urgency_base') == 'EMERGENCY'
        ]
        
        return emergency_conditions


# Singleton instance
_rag_service = None


def get_rag_service() -> RAGService:
    """Get or create RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service