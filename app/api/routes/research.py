"""API routes for research queries and knowledge access."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas_knowledge import (
    ConceptSchema,
    EvidenceSchema,
    HypothesisSchema,
    ResearchAnswerSchema,
    ResearchQuery,
    SourceReference,
    StrategySchema,
    TraderSchema,
)
from app.knowledge.service import ResearchService
from app.llm.openai_provider import OpenAILLMProvider
from app.retrieval.semantic_search import SemanticSearchProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/query", response_model=ResearchAnswerSchema)
async def research_query(
    query: ResearchQuery,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResearchAnswerSchema:
    """Answer a research question using retrieved source material.
    
    This endpoint uses RAG (Retrieval-Augmented Generation) to:
    1. Retrieve relevant document chunks based on the query
    2. Generate an answer grounded in the retrieved sources
    3. Provide citations back to the original source material
    
    The LLM is instructed to:
    - Only use information from the provided sources
    - Never fabricate citations
    - Identify contradictions or ambiguities
    - State when evidence is insufficient
    """
    # Create retrieval provider
    from app.db.session import async_session_factory
    
    retrieval_provider = SemanticSearchProvider(async_session_factory)
    
    # Create LLM provider
    from app.core.config import settings
    
    llm_provider = OpenAILLMProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_llm_model,
    )
    
    # Create research service
    research_service = ResearchService(
        retrieval_provider=retrieval_provider,
        llm_provider=llm_provider,
        top_k=query.top_k,
    )
    
    try:
        answer = await research_service.query(query.question)
        
        return ResearchAnswerSchema(
            answer=answer.answer,
            sources=[
                SourceReference(
                    index=s["index"],
                    chunk_id=s["chunk_id"],
                    document_id=s["document_id"],
                    document_title=s["document_title"],
                    document_author=s["document_author"],
                    page_start=s["page_start"],
                    page_end=s["page_end"],
                    section_heading=s["section_heading"],
                    score=s["score"],
                )
                for s in answer.sources
            ],
            confidence=answer.confidence,
            has_sufficient_evidence=answer.has_sufficient_evidence,
            contradictions_identified=answer.contradictions_identified,
            ambiguities_identified=answer.ambiguities_identified,
        )
        
    except Exception as e:
        logger.error(f"Research query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Research query failed: {str(e)}") from e


# Placeholder endpoints for future knowledge access
# These will be fully implemented in later phases

@router.get("/concepts", response_model=list[ConceptSchema])
async def list_concepts() -> list[ConceptSchema]:
    """List all extracted trading concepts.
    
    TODO: Implement in Phase 6 - Concept Extraction
    """
    return []


@router.get("/concepts/{concept_id}", response_model=ConceptSchema)
async def get_concept(concept_id: int) -> ConceptSchema:
    """Get a specific concept with its relationships.
    
    TODO: Implement in Phase 6 - Concept Extraction
    """
    raise HTTPException(status_code=404, detail="Concept extraction not yet implemented")


@router.get("/strategies", response_model=list[StrategySchema])
async def list_strategies() -> list[StrategySchema]:
    """List all extracted trading strategies.
    
    TODO: Implement in Phase 7 - Strategy Extraction
    """
    return []


@router.get("/strategies/{strategy_id}", response_model=StrategySchema)
async def get_strategy(strategy_id: int) -> StrategySchema:
    """Get a specific strategy with its rules and evidence.
    
    TODO: Implement in Phase 7 - Strategy Extraction
    """
    raise HTTPException(status_code=404, detail="Strategy extraction not yet implemented")


@router.get("/strategies/{strategy_id}/rules", response_model=list[dict])
async def get_strategy_rules(strategy_id: int) -> list[dict]:
    """Get rules for a specific strategy.
    
    TODO: Implement in Phase 7 - Strategy Extraction
    """
    raise HTTPException(status_code=404, detail="Strategy extraction not yet implemented")


@router.get("/strategies/{strategy_id}/evidence", response_model=list[EvidenceSchema])
async def get_strategy_evidence(strategy_id: int) -> list[EvidenceSchema]:
    """Get evidence/provenance for a specific strategy.
    
    TODO: Implement in Phase 7 - Strategy Extraction
    """
    raise HTTPException(status_code=404, detail="Strategy extraction not yet implemented")


@router.post("/strategies/compare", response_model=dict)
async def compare_strategies(strategy_ids: list[int]) -> dict:
    """Compare multiple trading strategies.
    
    TODO: Implement in Phase 8 - Strategy Comparison
    """
    raise HTTPException(status_code=404, detail="Strategy comparison not yet implemented")


@router.get("/hypotheses", response_model=list[HypothesisSchema])
async def list_hypotheses() -> list[HypothesisSchema]:
    """List all generated hypotheses.
    
    TODO: Implement in Phase 9 - Research Hypotheses
    """
    return []


@router.post("/hypotheses", response_model=HypothesisSchema)
async def generate_hypothesis(hypothesis_request: dict) -> HypothesisSchema:
    """Generate a testable hypothesis from source material.
    
    TODO: Implement in Phase 9 - Research Hypotheses
    """
    raise HTTPException(status_code=404, detail="Hypothesis generation not yet implemented")


@router.get("/traders", response_model=list[TraderSchema])
async def list_traders() -> list[TraderSchema]:
    """List all traders/investors in the knowledge base.
    
    TODO: Implement when trader extraction is added
    """
    return []


@router.get("/traders/{trader_id}", response_model=TraderSchema)
async def get_trader(trader_id: int) -> TraderSchema:
    """Get a specific trader/investor.
    
    TODO: Implement when trader extraction is added
    """
    raise HTTPException(status_code=404, detail="Trader extraction not yet implemented")
