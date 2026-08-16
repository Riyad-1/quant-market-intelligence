"""Prompt templates for RAG and knowledge extraction."""

from app.llm.prompts.research import (
    CONCEPT_EXTRACTION_SYSTEM,
    CONCEPT_EXTRACTION_USER_TEMPLATE,
    RESEARCH_SYSTEM_PROMPT,
    RESEARCH_USER_TEMPLATE,
    STRATEGY_EXTRACTION_SYSTEM,
    STRATEGY_EXTRACTION_USER_TEMPLATE,
    ConceptExtractionPromptTemplate,
    ResearchPromptTemplate,
    StrategyExtractionPromptTemplate,
)

__all__ = [
    "RESEARCH_SYSTEM_PROMPT",
    "RESEARCH_USER_TEMPLATE",
    "CONCEPT_EXTRACTION_SYSTEM",
    "CONCEPT_EXTRACTION_USER_TEMPLATE",
    "STRATEGY_EXTRACTION_SYSTEM",
    "STRATEGY_EXTRACTION_USER_TEMPLATE",
    "ResearchPromptTemplate",
    "ConceptExtractionPromptTemplate",
    "StrategyExtractionPromptTemplate",
]