"""LLM-powered answer synthesis for /recall."""

import httpx

from .config import settings

SYNTHESIS_PROMPT = """You are a personal memory assistant. The user asked a question and relevant memory entries have been retrieved.

Synthesize a clear, direct answer based ONLY on the provided entries. Do not invent information.

For each claim, cite the entry by its index number in brackets, e.g., [1], [2].

If the entries don't contain enough information to fully answer the question, say so explicitly.

Keep your answer concise and actionable. The user values direct communication."""


async def synthesize_answer(query: str, entries: list) -> str | None:
    """Generate a grounded answer from retrieved memory entries."""
    if not settings.llm_api_key or not entries:
        return None

    context_parts = []
    for index, entry in enumerate(entries, start=1):
        entities = ", ".join(entity.get("name", "") for entity in entry.entities) if entry.entities else "none"
        context_parts.append(
            f"[{index}] ({entry.entry_type}, {entry.occurred_at.strftime('%Y-%m-%d')}, "
            f"entities: {entities})\n{entry.body}"
        )

    user_message = (
        f"Question: {query}\n\nRetrieved memory entries:\n"
        f"{'\n\n'.join(context_parts)}\n\n"
        "Synthesize an answer based only on these entries. Cite entries by number."
    )

    if settings.llm_provider == "anthropic":
        return await _synthesize_anthropic(user_message)
    if settings.llm_provider == "openai":
        return await _synthesize_openai(user_message)
    return None


async def _synthesize_anthropic(user_message: str) -> str:
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
                "max_tokens": 1000,
                "system": SYNTHESIS_PROMPT,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _synthesize_openai(user_message: str) -> str:
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
                    {"role": "system", "content": SYNTHESIS_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 1000,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
