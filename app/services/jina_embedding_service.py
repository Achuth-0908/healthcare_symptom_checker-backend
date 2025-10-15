"""
Jina Embedding Service for Medical AI
Uses Jina API for high-quality medical embeddings
"""

import requests
import json
import logging
from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from app.config import settings

logger = logging.getLogger(__name__)


class JinaEmbeddingService:
    """
    Jina API service for medical embeddings
    Provides high-quality embeddings for medical text
    """
    
    def __init__(self):
        self.api_url = "https://api.jina.ai/v1/embeddings"
        self.model = "jina-embeddings-v2-base-en"  # Medical-optimized model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.JINA_API_KEY}"
        }
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts using Jina API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            payload = {
                "model": self.model,
                "input": texts
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return [item["embedding"] for item in result["data"]]
                    else:
                        logger.error(f"Jina API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error getting Jina embeddings: {e}")
            return []
    
    def get_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """
        Synchronous version of get_embeddings
        """
        try:
            payload = {
                "model": self.model,
                "input": texts
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return [item["embedding"] for item in result["data"]]
            else:
                logger.error(f"Jina API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting Jina embeddings: {e}")
            return []
    
    async def embed_medical_text(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for a single medical text
        
        Args:
            text: Medical text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        embeddings = await self.get_embeddings([text])
        return embeddings[0] if embeddings else None
    
    def embed_medical_text_sync(self, text: str) -> Optional[List[float]]:
        """
        Synchronous version of embed_medical_text
        """
        embeddings = self.get_embeddings_sync([text])
        return embeddings[0] if embeddings else None


class MedicalKnowledgeEmbedder:
    """
    Specialized embedder for medical knowledge base
    """
    
    def __init__(self):
        self.jina_service = JinaEmbeddingService()
    
    async def embed_medical_conditions(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Embed medical conditions with their descriptions
        
        Args:
            conditions: List of medical condition dictionaries
            
        Returns:
            List of conditions with embeddings
        """
        texts = []
        for condition in conditions:
            # Create comprehensive text for embedding
            text = f"""
            Medical Condition: {condition.get('name', '')}
            Description: {condition.get('description', '')}
            Symptoms: {', '.join(condition.get('symptoms', []))}
            Treatment: {condition.get('treatment', '')}
            Urgency: {condition.get('urgency_level', '')}
            """
            texts.append(text.strip())
        
        embeddings = await self.jina_service.get_embeddings(texts)
        
        # Add embeddings to conditions
        for i, condition in enumerate(conditions):
            if i < len(embeddings):
                condition['embedding'] = embeddings[i]
        
        return conditions
    
    async def embed_research_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Embed medical research papers
        
        Args:
            papers: List of research paper dictionaries
            
        Returns:
            List of papers with embeddings
        """
        texts = []
        for paper in papers:
            # Create comprehensive text for embedding
            text = f"""
            Title: {paper.get('title', '')}
            Abstract: {paper.get('abstract', '')}
            Keywords: {', '.join(paper.get('keywords', []))}
            Findings: {paper.get('findings', '')}
            Medical Domain: {paper.get('domain', '')}
            """
            texts.append(text.strip())
        
        embeddings = await self.jina_service.get_embeddings(texts)
        
        # Add embeddings to papers
        for i, paper in enumerate(papers):
            if i < len(embeddings):
                paper['embedding'] = embeddings[i]
        
        return papers
    
    async def embed_guidelines(self, guidelines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Embed medical guidelines
        
        Args:
            guidelines: List of guideline dictionaries
            
        Returns:
            List of guidelines with embeddings
        """
        texts = []
        for guideline in guidelines:
            # Create comprehensive text for embedding
            text = f"""
            Guideline: {guideline.get('title', '')}
            Description: {guideline.get('description', '')}
            Recommendations: {guideline.get('recommendations', '')}
            Conditions: {', '.join(guideline.get('conditions', []))}
            Source: {guideline.get('source', '')}
            """
            texts.append(text.strip())
        
        embeddings = await self.jina_service.get_embeddings(texts)
        
        # Add embeddings to guidelines
        for i, guideline in enumerate(guidelines):
            if i < len(embeddings):
                guideline['embedding'] = embeddings[i]
        
        return guidelines
