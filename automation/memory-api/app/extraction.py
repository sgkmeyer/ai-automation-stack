"""LLM-powered entity extraction and entry classification."""

import json

import httpx

from .config import settings
from .memory_types import normalize_extraction

EXTRACTION_PROMPT = """You are an entity extraction system for a personal memory journal.

Given a log entry from the user, extract:

1. entry_type: Classify as exactly one of: meeting, decision, commitment, reflection, observation, research, conversation, journal, transcript_summary, action_item, insight
2. entities: Extract mentioned people, companies, projects, and topics. For each entity, provide:
   - name: The proper name
   - type: One of: person, company, project, topic
   - role: One of: mentioned, subject, participant, owner

Rules:
- Use proper capitalization for names
- Don't extract generic nouns as entities
- If the user mentions making a decision, classify as "decision"
- If the user mentions promising or committing to do something, classify as "commitment"
- If the user describes a meeting or call, classify as "meeting" or "conversation"
- Default to "observation" if unclear

Respond with ONLY valid JSON, no markdown formatting:
{
    "entry_type": "...",
    "entities": [
        {"name": "...", "type": "...", "role": "..."}
    ]
}"""


async def extract_from_log(text: str) -> dict:
    """Use LLM to extract entry type and entities from natural language."""
    if not settings.llm_api_key:
        return {"entry_type": "observation", "entities": []}

    if settings.llm_provider == "anthropic":
        return normalize_extraction(await _extract_anthropic(text))
    if settings.llm_provider == "openai":
        return normalize_extraction(await _extract_openai(text))
    return {"entry_type": "observation", "entities": []}


async def _extract_anthropic(text: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": 500,
                "system": EXTRACTION_PROMPT,
                "messages": [{"role": "user", "content": text}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]
        return json.loads(content)


async def _extract_openai(text: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": text},
                ],
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
