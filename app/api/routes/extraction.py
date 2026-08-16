"""API routes for knowledge extraction (concepts, strategies, hypotheses)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.knowledge.schemas import (
    ConceptResponse,
    StrategyResponse,
    HypothesisResponse,
    ConceptCreate,
    StrategyCreate,
    HypothesisCreate,
)
from app.db.models import Concept, Strategy, Hypothesis
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.post("/concepts/from-chunks", response_model=dict)
async def extract_concepts_from_chunks(
    chunk_ids: list[int] = Body(..., description="List of chunk IDs to analyze"),
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Extract trading concepts from specified document chunks.
    
    This endpoint uses an LLM to analyze the text in the specified chunks
    and extract trading/investing concepts with full provenance tracking.
    
    Each extracted concept is linked to its source chunk(s) for evidence.
    """
    if not chunk_ids:
        raise HTTPException(status_code=400, detail="chunk_ids cannot be empty")
    
    try:
        from app.core.config import settings
        from app.llm.openai_provider import OpenAILLMProvider
        from app.knowledge.extraction.concepts import ConceptExtractionService
        
        # Create LLM provider
        llm_provider = OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_llm_model,
        )
        
        # Create extraction service
        extraction_service = ConceptExtractionService(llm_provider=llm_provider)
        
        # Extract and save concepts
        stats = await extraction_service.extract_and_save_from_chunks(
            session=db,
            chunk_ids=chunk_ids,
        )
        
        return {
            "status": "success",
            "statistics": stats,
            "message": f"Processed {stats['chunks_processed']} chunks, extracted {stats['concepts_extracted']} concepts",
        }
        
    except Exception as e:
        logger.error(f"Concept extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/strategies/from-chunks", response_model=dict)
async def extract_strategy_from_chunks(
    chunk_ids: list[int] = Body(..., description="List of chunk IDs containing strategy information"),
    trader_name: str | None = Body(None, description="Optional name of trader/investor"),
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Extract a trading strategy from specified document chunks.
    
    This endpoint uses an LLM to analyze the text in the specified chunks
    and extract a complete trading strategy including:
    - Setup conditions
    - Entry rules
    - Exit rules
    - Risk management rules
    - Position sizing rules
    
    Each extracted rule is linked to its source chunk(s) for evidence.
    Strategies are created with PROPOSED status and require review.
    """
    if not chunk_ids:
        raise HTTPException(status_code=400, detail="chunk_ids cannot be empty")
    
    try:
        from app.core.config import settings
        from app.llm.openai_provider import OpenAILLMProvider
        from app.knowledge.extraction.strategies import StrategyExtractionService
        
        # Create LLM provider
        llm_provider = OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_llm_model,
        )
        
        # Create extraction service
        extraction_service = StrategyExtractionService(llm_provider=llm_provider)
        
        # Extract strategy
        result = await extraction_service.extract_from_chunks(
            session=db,
            chunk_ids=chunk_ids,
            trader_name=trader_name,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error_message or "Strategy extraction failed",
            )
        
        if not result.strategy:
            raise HTTPException(
                status_code=400,
                detail="No strategy could be extracted from the provided chunks",
            )
        
        # Save strategy to database
        strategy_obj = await extraction_service.save_strategy(
            session=db,
            strategy=result.strategy,
            review_status="PROPOSED",
        )
        
        # Optionally generate hypotheses
        # hypotheses = await extraction_service.generate_hypotheses_from_strategy(
        #     session=db,
        #     strategy=strategy_obj,
        # )
        
        return {
            "status": "success",
            "strategy_id": strategy_obj.id,
            "strategy_name": strategy_obj.name,
            "rules_count": len(strategy_obj.rules),
            "message": f"Strategy '{strategy_obj.name}' extracted with {len(strategy_obj.rules)} rules",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Strategy extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.get("/concepts", response_model=list[ConceptResponse])
async def list_concepts(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = 0,
    limit: int = 20,
) -> list[ConceptResponse]:
    """List all extracted concepts."""
    result = await db.execute(
        select(Concept)
        .order_by(Concept.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    concepts = result.scalars().all()
    
    return [
        ConceptResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            category=c.category,
            review_status=c.review_status,
            metadata_json=c.metadata_json,
            created_at=c.created_at,
            updated_at=c.created_at,  # Would need updated_at field for accuracy
            evidence=[],
            related_concepts=[],
        )
        for c in concepts
    ]


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = 0,
    limit: int = 20,
) -> list[StrategyResponse]:
    """List all extracted strategies."""
    result = await db.execute(
        select(Strategy)
        .order_by(Strategy.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    strategies = result.scalars().all()
    
    return [
        StrategyResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            trader_id=s.trader_id,
            timeframe=s.timeframe,
            strategy_type=s.strategy_type,
            philosophy=s.philosophy,
            confidence=s.confidence,
            review_status=s.review_status,
            metadata_json=s.metadata_json,
            created_at=s.created_at,
            updated_at=s.created_at,
            rules=[],
            evidence=[],
            trader=None,
        )
        for s in strategies
    ]


@router.get("/hypotheses", response_model=list[HypothesisResponse])
async def list_hypotheses(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = 0,
    limit: int = 20,
) -> list[HypothesisResponse]:
    """List all generated hypotheses."""
    result = await db.execute(
        select(Hypothesis)
        .order_by(Hypothesis.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    hypotheses = result.scalars().all()
    
    return [
        HypothesisResponse(
            id=h.id,
            hypothesis_text=h.hypothesis_text,
            description=h.description,
            variables_required=h.variables_required,
            source_strategy_id=h.source_strategy_id,
            status=h.status,
            test_results=h.test_results,
            created_at=h.created_at,
            evidence=[],
        )
        for h in hypotheses
    ]
