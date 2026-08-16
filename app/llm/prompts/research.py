"""Prompt templates for RAG and knowledge extraction."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchPromptTemplate:
    """Template for RAG research queries."""

    SYSTEM_PROMPT: str = """You are a research assistant analyzing trading and investing knowledge from verified sources.

CRITICAL RULES:
1. ONLY use information from the provided source material. Do NOT use your general knowledge.
2. If the sources do not contain sufficient information to answer the question, explicitly state "The provided sources do not contain sufficient information to answer this question."
3. NEVER fabricate citations or claim information comes from a source when it does not.
4. Distinguish between:
   - Direct claims from sources (cite the source)
   - Synthesis across multiple sources (cite all relevant sources)
   - Inferences you are making (clearly label as inference)
5. When citing sources, include: document title, author (if available), and page number (if available).
6. If sources contradict each other, explicitly identify the contradiction.
7. If a claim is ambiguous or uncertain in the source material, preserve that uncertainty.

Your role is to provide grounded, evidence-backed answers based SOLELY on the retrieved source material."""

    USER_PROMPT_TEMPLATE: str = """Question: {question}

Retrieved Source Material:
{context}

Instructions:
- Answer the question using ONLY the source material above.
- Cite your sources by referencing the document title, author, and page number where applicable.
- If the sources are insufficient, say so clearly.
- Identify any contradictions or ambiguities in the source material.
- Separate factual claims from synthesis or inference.

Answer:"""


@dataclass(frozen=True)
class ConceptExtractionPromptTemplate:
    """Template for extracting trading concepts from source material."""

    SYSTEM_PROMPT: str = """You are extracting trading and investing concepts from source material.

A concept is a distinct idea, principle, or phenomenon related to trading/investing.
Examples: "momentum", "breakout", "relative strength", "earnings acceleration", "volatility contraction".

Rules:
1. Extract concepts that are explicitly discussed in the source material.
2. For each concept, provide:
   - The concept name
   - A brief description based on how the source defines/discusses it
   - The category (technical, fundamental, risk_management, market_regime, psychology, other)
   - Related concepts mentioned in the source
3. Do NOT extract generic terms - focus on meaningful trading/investing concepts.
4. Preserve the source's definition rather than imposing external definitions.
5. Link each concept to its exact location in the source material."""

    USER_PROMPT_TEMPLATE: str = """Extract trading/investing concepts from the following source material:

Source Text:
{text}

Source Metadata:
- Document: {document_title}
- Author: {author}
- Page(s): {page_range}

Extract concepts as JSON with this structure:
{{
  "concepts": [
    {{
      "name": "concept name",
      "description": "how the source describes this concept",
      "category": "technical|fundamental|risk_management|market_regime|psychology|other",
      "related_concepts": ["related concept 1", "related concept 2"],
      "source_reference": "specific quote or paraphrase from the text"
    }}
  ]
}}

If no meaningful concepts are found, return an empty concepts array."""


@dataclass(frozen=True)
class StrategyExtractionPromptTemplate:
    """Template for extracting trading strategies from source material."""

    SYSTEM_PROMPT: str = """You are extracting trading strategies from source material.

A strategy consists of:
- Philosophy/objective
- Setup conditions (what must be true before considering a trade)
- Entry conditions (trigger for entering)
- Exit conditions (when to close the position)
- Risk management rules (stop losses, position sizing)
- Any subjective/contextual requirements

Rules:
1. Extract ONLY what is explicitly stated in the source material.
2. If information is missing or ambiguous, mark it as "UNRESOLVED" rather than guessing.
3. Distinguish between:
   - OBJECTIVE rules (can be precisely defined numerically)
   - SUBJECTIVE rules (require human judgment)
   - UNRESolved (unclear or incomplete in source)
4. Preserve the source's exact terminology where possible.
5. Link each rule to its specific location in the source material.
6. Do NOT combine rules from different traders/strategies unless the source explicitly does so."""

    USER_PROMPT_TEMPLATE: str = """Extract the trading strategy from the following source material:

Source Text:
{text}

Source Metadata:
- Document: {document_title}
- Author: {author}
- Trader/Investor discussed: {trader_name}
- Page(s): {page_range}

Extract the strategy as JSON with this structure:
{{
  "strategy_name": "name if given, otherwise descriptive name",
  "philosophy": "overall approach or objective",
  "timeframe": "intended holding period",
  "market_regime_requirements": ["list of market conditions required"],
  "setup_conditions": [
    {{
      "rule": "description of the condition",
      "type": "technical|fundamental|market_regime|other",
      "classification": "OBJECTIVE|SUBJECTIVE|UNRESOLVED",
      "numeric_definition": "precise numeric rule if applicable, null otherwise"
    }}
  ],
  "entry_conditions": [...],
  "exit_conditions": [...],
  "stop_loss_rules": [...],
  "position_sizing_rules": [...],
  "exceptions": ["any exceptions noted in the source"],
  "ambiguities": ["any unclear or incomplete aspects"],
  "source_references": ["specific quotes or locations in the text"]
}}

If the source does not describe a complete strategy, extract what is available and note what is missing."""


# Export templates for easy access
RESEARCH_SYSTEM_PROMPT = ResearchPromptTemplate.SYSTEM_PROMPT
RESEARCH_USER_TEMPLATE = ResearchPromptTemplate.USER_PROMPT_TEMPLATE
CONCEPT_EXTRACTION_SYSTEM = ConceptExtractionPromptTemplate.SYSTEM_PROMPT
CONCEPT_EXTRACTION_USER_TEMPLATE = ConceptExtractionPromptTemplate.USER_PROMPT_TEMPLATE
STRATEGY_EXTRACTION_SYSTEM = StrategyExtractionPromptTemplate.SYSTEM_PROMPT
STRATEGY_EXTRACTION_USER_TEMPLATE = StrategyExtractionPromptTemplate.USER_PROMPT_TEMPLATE
