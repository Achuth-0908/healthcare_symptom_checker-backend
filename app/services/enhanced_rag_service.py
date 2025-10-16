"""
Enhanced RAG (Retrieval-Augmented Generation) Service
Uses ChromaDB for vector storage and Jina API for medical embeddings
Integrates medical research papers and guidelines for better accuracy
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
import json
import logging
from typing import List, Dict, Any, Optional
import os
import numpy as np
import asyncio

from app.config import settings
from app.services.jina_embedding_service import JinaEmbeddingService, MedicalKnowledgeEmbedder

logger = logging.getLogger(__name__)


class EnhancedRAGService:
    """
    Enhanced RAG service with Jina API and medical research integration
    """
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.jina_service = JinaEmbeddingService()
        self.medical_embedder = MedicalKnowledgeEmbedder()
        self.knowledge_base = None
        self.research_papers = None
        self.guidelines = None
        self.clinical_conditions = None
    
    def initialize(self):
        """Initialize ChromaDB and load medical knowledge base"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name="medical_knowledge",
                    embedding_function=None  # We'll use Jina embeddings
                )
                logger.info("Loaded existing medical knowledge collection")
                
                # Check if collection is empty and needs indexing
                if self.collection.count() == 0:
                    logger.info("Collection is empty, loading knowledge base...")
                    self._load_knowledge_base()
                else:
                    logger.info(f"Collection has {self.collection.count()} documents")
                    
            except Exception as e:
                logger.info(f"Collection not found, creating new one: {e}")
                try:
                    self.collection = self.client.create_collection(
                        name="medical_knowledge",
                        embedding_function=None,  # We'll use Jina embeddings
                        metadata={"description": "Medical knowledge base with research papers and guidelines"}
                    )
                    logger.info("Created new medical knowledge collection")
                    
                    # Load and index knowledge base
                    self._load_knowledge_base()
                except Exception as create_error:
                    logger.error(f"Failed to create collection: {create_error}")
                    # Try to get existing collection
                    self.collection = self.client.get_collection("medical_knowledge")
                    logger.info("Using existing collection")
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced RAG service: {e}")
            raise
    
    def _load_knowledge_base(self):
        """Load medical knowledge base from files"""
        try:
            # Load original medical knowledge base
            kb_path = settings.KNOWLEDGE_BASE_PATH
            logger.info(f"Looking for knowledge base at: {kb_path}")
            logger.info(f"KB path exists: {os.path.exists(kb_path)}")
            
            if os.path.exists(kb_path):
                with open(kb_path, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
                logger.info(f"Loaded medical knowledge base from {kb_path}")
            else:
                logger.warning(f"Knowledge base file not found at {kb_path}")
                self.knowledge_base = {"conditions": []}
            
            # Load research papers and guidelines
            research_path = settings.MEDICAL_RESEARCH_KB_PATH
            logger.info(f"Looking for research KB at: {research_path}")
            logger.info(f"Research KB path exists: {os.path.exists(research_path)}")
            
            if os.path.exists(research_path):
                with open(research_path, 'r', encoding='utf-8') as f:
                    research_data = json.load(f)
                    self.research_papers = research_data.get('research_papers', [])
                    self.guidelines = research_data.get('medical_guidelines', [])
                    self.clinical_conditions = research_data.get('clinical_conditions', [])
                logger.info(f"Loaded {len(self.research_papers)} research papers, {len(self.guidelines)} guidelines, {len(self.clinical_conditions)} conditions")
            else:
                logger.warning(f"Research knowledge base file not found at {research_path}")
                self.research_papers = []
                self.guidelines = []
                self.clinical_conditions = []
            
            # Index all knowledge into ChromaDB
            self._index_knowledge_base()
            
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            # Don't raise, just continue with empty knowledge base
            self.knowledge_base = {"conditions": []}
            self.research_papers = []
            self.guidelines = []
            self.clinical_conditions = []
            
            # Create some basic medical knowledge as fallback
            self._create_fallback_knowledge()
    
    def _create_fallback_knowledge(self):
        """Create basic medical knowledge as fallback when files are not available"""
        logger.info("Creating fallback medical knowledge base")
        
        self.knowledge_base = {
            "conditions": [
                {
                    "name": "Common Cold",
                    "description": "Viral infection of the upper respiratory tract",
                    "symptoms": ["runny nose", "sneezing", "cough", "sore throat"],
                    "treatment": "Rest, fluids, over-the-counter medications",
                    "urgency_level": "low"
                },
                {
                    "name": "Influenza",
                    "description": "Viral infection causing fever and body aches",
                    "symptoms": ["fever", "body aches", "fatigue", "cough"],
                    "treatment": "Rest, fluids, antiviral medications if severe",
                    "urgency_level": "moderate"
                }
            ]
        }
        
        self.research_papers = [
            {
                "title": "General Medical Guidelines",
                "content": "Basic medical assessment guidelines for common conditions",
                "id": "fallback_paper_001"
            }
        ]
        
        self.guidelines = [
            {
                "title": "Emergency Response Guidelines",
                "content": "Guidelines for identifying medical emergencies",
                "id": "fallback_guideline_001"
            }
        ]
        
        self.clinical_conditions = [
            {
                "name": "Emergency Condition",
                "description": "Life-threatening medical condition requiring immediate attention",
                "symptoms": ["severe pain", "difficulty breathing", "loss of consciousness"],
                "urgency_level": "emergency"
            }
        ]
        
        logger.info("Fallback knowledge base created successfully")
    
    def _index_knowledge_base(self):
        """Index all medical knowledge into ChromaDB with Jina embeddings"""
        try:
            all_documents = []
            all_metadatas = []
            all_ids = []
            
            logger.info(f"Starting to index knowledge base. KB conditions: {len(self.knowledge_base.get('conditions', []))}")
            logger.info(f"Research papers: {len(self.research_papers)}, Guidelines: {len(self.guidelines)}, Conditions: {len(self.clinical_conditions)}")
            
            # Index original medical conditions
            if self.knowledge_base and 'conditions' in self.knowledge_base:
                for condition in self.knowledge_base['conditions']:
                    doc_text = f"""
                    Medical Condition: {condition.get('name', '')}
                    Description: {condition.get('description', '')}
                    Symptoms: {', '.join(condition.get('symptoms', []))}
                    Treatment: {condition.get('treatment', '')}
                    Urgency: {condition.get('urgency_level', '')}
                    """
                    
                    all_documents.append(doc_text.strip())
                    all_metadatas.append({
                        'type': 'condition',
                        'name': condition.get('name', ''),
                        'urgency': condition.get('urgency_level', ''),
                        'source': 'medical_kb'
                    })
                    all_ids.append(f"condition_{condition.get('id', len(all_ids))}")
            
            # Index research papers
            if self.research_papers:
                for paper in self.research_papers:
                    doc_text = f"""
                    Research Paper: {paper.get('title', '')}
                    Abstract: {paper.get('abstract', '')}
                    Keywords: {', '.join(paper.get('keywords', []))}
                    Findings: {paper.get('findings', '')}
                    Domain: {paper.get('domain', '')}
                    """
                    
                    all_documents.append(doc_text.strip())
                    all_metadatas.append({
                        'type': 'research',
                        'title': paper.get('title', ''),
                        'domain': paper.get('domain', ''),
                        'source': paper.get('source', ''),
                        'relevance_score': paper.get('relevance_score', 0.8)
                    })
                    all_ids.append(f"research_{paper.get('id', len(all_ids))}")
            
            # Index guidelines
            if self.guidelines:
                for guideline in self.guidelines:
                    doc_text = f"""
                    Medical Guideline: {guideline.get('title', '')}
                    Description: {guideline.get('description', '')}
                    Recommendations: {guideline.get('recommendations', '')}
                    Conditions: {', '.join(guideline.get('conditions', []))}
                    Urgency: {guideline.get('urgency_level', '')}
                    """
                    
                    all_documents.append(doc_text.strip())
                    all_metadatas.append({
                        'type': 'guideline',
                        'title': guideline.get('title', ''),
                        'urgency': guideline.get('urgency_level', ''),
                        'source': guideline.get('source', ''),
                        'relevance_score': guideline.get('relevance_score', 0.9)
                    })
                    all_ids.append(f"guideline_{guideline.get('id', len(all_ids))}")
            
            # Index clinical conditions
            if self.clinical_conditions:
                for condition in self.clinical_conditions:
                    doc_text = f"""
                    Clinical Condition: {condition.get('name', '')}
                    Description: {condition.get('description', '')}
                    Symptoms: {', '.join(condition.get('symptoms', []))}
                    Treatment: {condition.get('treatment', '')}
                    Urgency: {condition.get('urgency_level', '')}
                    Body Systems: {', '.join(condition.get('body_systems', []))}
                    """
                    
                    all_documents.append(doc_text.strip())
                    all_metadatas.append({
                        'type': 'clinical_condition',
                        'name': condition.get('name', ''),
                        'urgency': condition.get('urgency_level', ''),
                        'body_systems': ', '.join(condition.get('body_systems', [])),  # Convert list to string
                        'relevance_score': condition.get('relevance_score', 0.95)
                    })
                    all_ids.append(f"clinical_{condition.get('id', len(all_ids))}")
            
            # Get embeddings from Jina API
            logger.info(f"Getting embeddings for {len(all_documents)} documents...")
            embeddings = self.jina_service.get_embeddings_sync(all_documents)
            
            if embeddings:
                # Add to ChromaDB
                self.collection.add(
                    documents=all_documents,
                    metadatas=all_metadatas,
                    ids=all_ids,
                    embeddings=embeddings
                )
                logger.info(f"Successfully indexed {len(all_documents)} medical documents")
            else:
                logger.error("Failed to get embeddings from Jina API")
                
        except Exception as e:
            logger.error(f"Error indexing knowledge base: {e}")
            raise
    
    async def retrieve_relevant_conditions(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant medical conditions using Jina embeddings
        
        Args:
            query: User's symptom description
            top_k: Number of results to return
            
        Returns:
            List of relevant medical conditions with metadata
        """
        try:
            if not self.collection:
                logger.error("RAG service not initialized")
                return []
            
            # Get query embedding from Jina with fallback
            query_embedding = self.jina_service.embed_medical_text_sync(query)
            if not query_embedding:
                logger.warning("Failed to get query embedding from Jina, falling back to text-based search")
                # Fallback to text-based search without embeddings
                return self._fallback_text_search(query, top_k)
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            relevant_conditions = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 1.0
                    
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 - distance
                    
                    relevant_conditions.append({
                        'content': doc,
                        'metadata': metadata,
                        'similarity_score': similarity_score,
                        'type': metadata.get('type', 'unknown')
                    })
            
            return relevant_conditions
            
        except Exception as e:
            logger.error(f"Error retrieving relevant conditions: {e}")
            return []
    
    async def get_medical_context(self, query: str) -> Dict[str, Any]:
        """
        Get comprehensive medical context for a query
        
        Args:
            query: User's symptom description
            
        Returns:
            Dictionary containing relevant medical information
        """
        try:
            # Retrieve relevant conditions
            relevant_conditions = await self.retrieve_relevant_conditions(query, top_k=10)
            
            # Categorize results
            conditions = []
            research = []
            guidelines = []
            clinical = []
            
            for item in relevant_conditions:
                if item['type'] == 'condition':
                    conditions.append(item)
                elif item['type'] == 'research':
                    research.append(item)
                elif item['type'] == 'guideline':
                    guidelines.append(item)
                elif item['type'] == 'clinical_condition':
                    clinical.append(item)
            
            # Determine urgency level
            urgency_level = 'routine'
            emergency_indicators = []
            
            for item in relevant_conditions:
                metadata = item.get('metadata', {})
                if metadata.get('urgency') == 'emergency':
                    urgency_level = 'emergency'
                    emergency_indicators.append(item['content'])
                elif metadata.get('urgency') == 'urgent' and urgency_level != 'emergency':
                    urgency_level = 'urgent'
            
            return {
                'relevant_conditions': conditions,
                'research_evidence': research,
                'clinical_guidelines': guidelines,
                'clinical_conditions': clinical,
                'urgency_level': urgency_level,
                'emergency_indicators': emergency_indicators,
                'total_results': len(relevant_conditions)
            }
            
        except Exception as e:
            logger.error(f"Error getting medical context: {e}")
            return {
                'relevant_conditions': [],
                'research_evidence': [],
                'clinical_guidelines': [],
                'clinical_conditions': [],
                'urgency_level': 'routine',
                'emergency_indicators': [],
                'total_results': 0
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get RAG service status"""
        return {
            'initialized': self.collection is not None,
            'jina_service_available': self.jina_service is not None,
            'knowledge_base_loaded': self.knowledge_base is not None,
            'research_papers_count': len(self.research_papers) if self.research_papers else 0,
            'guidelines_count': len(self.guidelines) if self.guidelines else 0,
            'clinical_conditions_count': len(self.clinical_conditions) if self.clinical_conditions else 0
        }
    
    def _fallback_text_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Fallback text-based search when embeddings fail
        Uses simple keyword matching on the knowledge base
        """
        try:
            if not self.knowledge_base:
                logger.error("No knowledge base available for fallback search")
                return []
            
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            results = []
            
            # Search through all knowledge base entries
            for condition in self.knowledge_base:
                condition_text = f"{condition.get('name', '')} {condition.get('description', '')} {condition.get('symptoms', '')}"
                condition_text_lower = condition_text.lower()
                condition_words = set(condition_text_lower.split())
                
                # Calculate simple word overlap score
                overlap = len(query_words.intersection(condition_words))
                if overlap > 0:
                    score = overlap / len(query_words)  # Normalize by query length
                    results.append({
                        'document': condition_text,
                        'metadata': condition,
                        'distance': 1.0 - score,  # Convert to distance (lower is better)
                        'score': score
                    })
            
            # Sort by score (highest first) and return top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in fallback text search: {e}")
            return []
