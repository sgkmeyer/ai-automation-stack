"""Registry storage, extraction, and query helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

from .config import settings
from .db import get_conn
from .mutation_journal import record_mutation

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "ref_src",
    "si",
}
TRACKING_QUERY_PREFIXES = ("utm_",)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    )
}
REGISTRY_FETCH_VERIFY = False


@dataclass
class CanonicalUrl:
    original_url: str
    canonical_url: str
    canonical_host: str
    source_kind: str
    redirected: bool
    final_url: str


@dataclass
class ExtractedContent:
    title: str | None
    description: str | None
    text: str | None
    raw_text: str | None
    extraction_mode: str
    metadata: dict[str, Any]


def detect_source_kind(host: str) -> str:
    normalized = host.lower().removeprefix("www.")
    if normalized.endswith("youtu.be") or normalized.endswith("youtube.com"):
        return "youtube"
    if normalized.endswith("x.com") or normalized.endswith("twitter.com"):
        return "x"
    if normalized.endswith("tiktok.com"):
        return "tiktok"
    if normalized:
        return "web"
    return "unknown"


def _scheme_equivalent_urls(canonical_url: str, source_kind: str) -> list[str]:
    if source_kind != "web":
        return [canonical_url]

    parsed = urlparse(canonical_url)
    if parsed.scheme not in {"http", "https"}:
        return [canonical_url]

    alternate = urlunparse(
        (
            "https" if parsed.scheme == "http" else "http",
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return [canonical_url, alternate]


def _strip_tracking_params(query: list[tuple[str, str]]) -> list[tuple[str, str]]:
    cleaned: list[tuple[str, str]] = []
    for key, value in query:
        lower_key = key.lower()
        if lower_key in TRACKING_QUERY_PARAMS:
            continue
        if any(lower_key.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        cleaned.append((key, value))
    return cleaned


def _canonicalize_parsed(parsed) -> CanonicalUrl:
    scheme = parsed.scheme or "https"
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    query = parse_qsl(parsed.query, keep_blank_values=False)

    if host in {"youtu.be", "www.youtu.be"}:
        video_id = path.strip("/")
        host = "www.youtube.com"
        path = "/watch"
        query = [("v", video_id)] if video_id else []
    elif host.endswith("youtube.com"):
        host = "www.youtube.com"
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) >= 2 and segments[0] == "shorts":
            path = "/watch"
            query = [("v", segments[1])]
    elif host.endswith("twitter.com"):
        host = "x.com"
    elif host.startswith("m.") and host.endswith("tiktok.com"):
        host = host.removeprefix("m.")

    if host == "www.youtube.com":
        allowed = {"v", "list", "t"}
        query = [(key, value) for key, value in query if key in allowed]
    elif detect_source_kind(host) in {"x", "tiktok"}:
        query = []
    else:
        query = _strip_tracking_params(query)

    if path != "/":
        path = re.sub(r"/{2,}", "/", path).rstrip("/") or "/"

    canonical_url = urlunparse((scheme, host, path, "", urlencode(query, doseq=True), ""))
    return CanonicalUrl(
        original_url=urlunparse(parsed),
        canonical_url=canonical_url,
        canonical_host=host,
        source_kind=detect_source_kind(host),
        redirected=False,
        final_url=canonical_url,
    )


def _fallback_title_for_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.") or "saved link"
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        return host

    last_segment = re.sub(r"[-_]+", " ", segments[-1]).strip()
    last_segment = re.sub(r"\.[a-z0-9]{1,6}$", "", last_segment, flags=re.IGNORECASE)
    if not last_segment:
        return host
    return f"{host} - {last_segment.title()}"


def _fallback_extracted_content(canonical: CanonicalUrl, *, reason: str, status_code: int | None = None) -> ExtractedContent:
    metadata: dict[str, Any] = {
        "resolved_url": canonical.final_url or canonical.canonical_url,
        "fallback_reason": reason,
    }
    if status_code is not None:
        metadata["fetch_status_code"] = status_code

    return ExtractedContent(
        title=_fallback_title_for_url(canonical.canonical_url),
        description=None,
        text=None,
        raw_text=None,
        extraction_mode="blocked_metadata_only" if status_code in {401, 403, 429} else "url_metadata_only",
        metadata=metadata,
    )


def _registry_item_preference(row: dict[str, Any]) -> tuple[int, int, int, int, datetime, datetime]:
    parsed = urlparse(str(row.get("canonical_url") or ""))
    return (
        1 if parsed.scheme == "https" else 0,
        1 if row.get("processing_status") == "ready" else 0,
        1 if bool(row.get("summary")) else 0,
        1 if bool(row.get("title")) else 0,
        row.get("processed_at") or datetime.min.replace(tzinfo=timezone.utc),
        row.get("last_captured_at") or datetime.min.replace(tzinfo=timezone.utc),
    )


def _pick_preferred_registry_item(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(rows, key=_registry_item_preference)


async def canonicalize_url(url: str, *, deep: bool = False) -> CanonicalUrl:
    normalized_input = url.strip()
    parsed = urlparse(normalized_input)
    if not parsed.scheme:
        parsed = urlparse(f"https://{normalized_input}")

    candidate = _canonicalize_parsed(parsed)
    timeout = httpx.Timeout(settings.registry_fetch_timeout_seconds)
    method = "GET" if deep or candidate.source_kind in {"x", "tiktok"} else "HEAD"

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
            verify=REGISTRY_FETCH_VERIFY,
        ) as client:
            response = await client.request(method, candidate.canonical_url)
            if response.status_code in {403, 405, 501} and method == "HEAD":
                response = await client.get(candidate.canonical_url)
            final_parsed = urlparse(str(response.url))
            final_candidate = _canonicalize_parsed(final_parsed)
            final_candidate.redirected = final_candidate.canonical_url != candidate.canonical_url
            final_candidate.final_url = str(response.url)
            return final_candidate
    except Exception:
        return candidate


def _youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/") or None
    if parsed.netloc.endswith("youtube.com"):
        query = dict(parse_qsl(parsed.query))
        if query.get("v"):
            return query["v"]
        segments = [segment for segment in parsed.path.split("/") if segment]
        if len(segments) >= 2 and segments[0] == "shorts":
            return segments[1]
    return None


async def _fetch_html_metadata(url: str) -> ExtractedContent:
    timeout = httpx.Timeout(settings.registry_fetch_timeout_seconds)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
        verify=REGISTRY_FETCH_VERIFY,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "html.parser")

    def pick_meta(*names: str) -> str | None:
        for name in names:
            tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
            if tag and tag.get("content"):
                return str(tag["content"]).strip()
        return None

    title = pick_meta("og:title", "twitter:title") or (soup.title.string.strip() if soup.title and soup.title.string else None)
    description = pick_meta("og:description", "twitter:description", "description")
    canonical_link = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
    canonical_href = str(canonical_link.get("href")).strip() if canonical_link and canonical_link.get("href") else None
    body_text = soup.get_text(separator="\n", strip=True)
    clipped = body_text[: settings.registry_max_extract_chars] if body_text else None

    return ExtractedContent(
        title=title,
        description=description,
        text=clipped,
        raw_text=body_text,
        extraction_mode="metadata_only" if clipped == description else "html_parse",
        metadata={
            "resolved_url": str(response.url),
            "html_canonical_url": urljoin(str(response.url), canonical_href) if canonical_href else None,
        },
    )


async def _fetch_youtube_content(url: str) -> ExtractedContent:
    video_id = _youtube_video_id(url)
    if not video_id:
        return ExtractedContent(
            title=None,
            description=None,
            text=None,
            raw_text=None,
            extraction_mode="youtube_unresolved",
            metadata={},
        )

    title = None
    description = None
    timeout = httpx.Timeout(settings.registry_fetch_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=DEFAULT_HEADERS, verify=REGISTRY_FETCH_VERIFY) as client:
            oembed = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            )
            oembed.raise_for_status()
            data = oembed.json()
            title = data.get("title")
    except Exception:
        pass

    transcript_text = None
    transcript_language = None
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)
        pieces = []
        for snippet in transcript:
            transcript_language = getattr(transcript, "language_code", transcript_language)
            pieces.append(snippet.text)
        transcript_text = "\n".join(pieces)
    except Exception:
        transcript_text = None

    if not transcript_text:
        try:
            html_meta = await _fetch_html_metadata(url)
            if not title:
                title = html_meta.title
            description = html_meta.description
        except Exception:
            pass

    raw_text = transcript_text or description
    return ExtractedContent(
        title=title,
        description=description,
        text=(transcript_text or description or "")[: settings.registry_max_extract_chars] or None,
        raw_text=raw_text,
        extraction_mode="youtube_transcript" if transcript_text else "youtube_metadata_only",
        metadata={"video_id": video_id, "transcript_language": transcript_language},
    )


async def extract_registry_content(canonical: CanonicalUrl) -> ExtractedContent:
    if canonical.source_kind == "youtube":
        return await _fetch_youtube_content(canonical.canonical_url)

    try:
        content = await _fetch_html_metadata(canonical.canonical_url)
    except httpx.HTTPStatusError as exc:
        return _fallback_extracted_content(
            canonical,
            reason=str(exc),
            status_code=exc.response.status_code if exc.response else None,
        )
    if canonical.source_kind in {"x", "tiktok"}:
        return ExtractedContent(
            title=content.title,
            description=content.description,
            text=content.description,
            raw_text=content.raw_text,
            extraction_mode="metadata_only",
            metadata=content.metadata,
        )
    return content


async def summarize_registry_item(
    *,
    canonical_url: str,
    source_kind: str,
    extracted: ExtractedContent,
    user_tags: list[str],
    user_notes: list[str],
) -> dict[str, Any]:
    title = extracted.title
    description = extracted.description
    base_text = (extracted.text or description or "").strip()

    if not settings.llm_api_key:
        summary = description or base_text[:500] or canonical_url
        why = user_notes[-1] if user_notes else summary
        takeaways = [user_notes[-1]] if user_notes else ([summary] if summary else [])
        topics = sorted({source_kind, *user_tags}) or [source_kind]
        return {
            "title": title,
            "summary": summary,
            "why_it_matters": why,
            "key_takeaways": takeaways[:5],
            "topics": topics[:8],
        }

    prompt = {
        "canonical_url": canonical_url,
        "source_kind": source_kind,
        "extracted_title": title,
        "extracted_description": description,
        "user_tags": user_tags,
        "user_notes": user_notes,
        "content": base_text[: settings.registry_max_extract_chars],
    }
    system_prompt = (
        "You are building a private content registry for the user's second brain.\n"
        "Given a saved URL plus optional user notes and tags, produce a useful stored summary.\n"
        "Return valid JSON with keys: title, summary, why_it_matters, key_takeaways, topics.\n"
        "Rules:\n"
        "- summary: 2-4 sentences, source-faithful.\n"
        "- why_it_matters: concise interpretation of why this may matter to the user.\n"
        "- key_takeaways: array of 2-5 short bullet-style strings.\n"
        "- topics: array of 2-6 lower-case topic tags aligned with the user's tags when appropriate.\n"
        "- preserve the original meaning; do not invent details.\n"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        if settings.llm_provider == "anthropic":
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.llm_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "max_tokens": 1000,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": json.dumps(prompt)}],
                },
            )
            response.raise_for_status()
            payload = json.loads(response.json()["content"][0]["text"])
        else:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(prompt)},
                    ],
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            payload = json.loads(response.json()["choices"][0]["message"]["content"])

    return {
        "title": payload.get("title") or title,
        "summary": str(payload.get("summary") or description or canonical_url).strip(),
        "why_it_matters": str(payload.get("why_it_matters") or (user_notes[-1] if user_notes else description or canonical_url)).strip(),
        "key_takeaways": [str(item).strip() for item in payload.get("key_takeaways", []) if str(item).strip()][:5],
        "topics": [str(item).strip().lower() for item in payload.get("topics", []) if str(item).strip()][:8],
    }


def _archive_path_for(item_id: UUID, source_kind: str, canonical_host: str) -> Path:
    host = re.sub(r"[^a-z0-9.-]+", "-", canonical_host.lower()).strip("-") or "unknown"
    root = Path(settings.registry_archive_root)
    return root / source_kind / host / f"{item_id}.md"


def archive_registry_content(item_id: UUID, source_kind: str, canonical_host: str, canonical_url: str, extracted: ExtractedContent) -> str | None:
    if not extracted.raw_text:
        return None

    path = _archive_path_for(item_id, source_kind, canonical_host)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"URL: {canonical_url}",
                f"Title: {extracted.title or ''}",
                f"Description: {extracted.description or ''}",
                "",
                extracted.raw_text,
            ]
        ),
        encoding="utf-8",
    )
    return str(path)


async def _fetch_item(conn, item_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow("SELECT * FROM registry.items WHERE id = $1", item_id)
    return dict(row) if row else None


def _metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _merge_metadata(metadata: dict[str, Any], user_note: str | None, user_tags: list[str]) -> dict[str, Any]:
    merged = dict(metadata or {})
    existing_tags = {str(tag).strip() for tag in merged.get("user_tags", []) if str(tag).strip()}
    existing_tags.update(tag.strip() for tag in user_tags if tag.strip())
    merged["user_tags"] = sorted(existing_tags)

    note_search = merged.get("note_search", "")
    pieces = [piece.strip() for piece in [note_search, user_note or ""] if piece and piece.strip()]
    if pieces:
        merged["note_search"] = "\n".join(dict.fromkeys(pieces))
    return merged


async def create_registry_capture(*, url: str, note: str | None, tags: list[str], capture_channel: str) -> dict[str, Any]:
    canonical = await canonicalize_url(url, deep=False)
    lookup_urls = _scheme_equivalent_urls(canonical.canonical_url, canonical.source_kind)
    async with get_conn() as conn:
        async with conn.transaction():
            existing_rows = await conn.fetch(
                """
                SELECT *
                FROM registry.items
                WHERE canonical_url = ANY($1::text[])
                """,
                lookup_urls,
            )
            existing = [dict(row) for row in existing_rows]
            if existing:
                preferred = _pick_preferred_registry_item(existing)
                item_id = preferred["id"]
                for row in existing:
                    if row["id"] != item_id:
                        item_id = await _merge_registry_items(conn, row["id"], item_id)

                merged_row = await _fetch_item(conn, item_id)
                metadata = _merge_metadata(_metadata_dict((merged_row or {}).get("metadata")) if merged_row else {}, note, tags)
                await conn.execute(
                    """
                    UPDATE registry.items
                    SET last_captured_at = NOW(),
                        source_kind = $2,
                        canonical_host = $3,
                        processing_status = 'captured',
                        review_state = 'inbox',
                        last_error = NULL,
                        metadata = $4::jsonb
                    WHERE id = $1
                    """,
                    item_id,
                    canonical.source_kind,
                    canonical.canonical_host,
                    json.dumps(metadata),
                )
            else:
                metadata = _merge_metadata({}, note, tags)
                item_id = await conn.fetchval(
                    """
                    INSERT INTO registry.items (
                        original_url, canonical_url, canonical_host, source_kind,
                        capture_channel, processing_status, review_state, metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, 'captured', 'inbox', $6::jsonb)
                    RETURNING id
                    """,
                    url,
                    canonical.canonical_url,
                    canonical.canonical_host,
                    canonical.source_kind,
                    capture_channel,
                    json.dumps(metadata),
                )

            await conn.execute(
                """
                INSERT INTO registry.captures (item_id, submitted_url, capture_channel, user_note, user_tags)
                VALUES ($1, $2, $3, $4, $5)
                """,
                item_id,
                url,
                capture_channel,
                note,
                tags,
            )

            await conn.execute(
                """
                INSERT INTO registry.jobs (item_id, job_type, status, attempt_count, started_at, completed_at)
                VALUES ($1, 'capture', 'completed', 1, NOW(), NOW())
                """,
                item_id,
            )
            await conn.execute(
                """
                INSERT INTO registry.jobs (item_id, job_type, status)
                VALUES ($1, 'process', 'pending')
                """,
                item_id,
            )

    return {
        "item_id": item_id,
        "canonical_url": canonical.canonical_url,
        "processing_status": "captured",
        "review_state": "inbox",
    }


async def _latest_capture_context(conn, item_id: UUID) -> tuple[list[str], list[str]]:
    rows = await conn.fetch(
        """
        SELECT id, user_note, user_tags
        FROM registry.captures
        WHERE item_id = $1
        ORDER BY captured_at ASC
        """,
        item_id,
    )
    notes = [str(row["user_note"]).strip() for row in rows if row["user_note"]]
    tags: list[str] = []
    for row in rows:
        tags.extend(tag.strip() for tag in row["user_tags"] if isinstance(tag, str) and tag.strip())
    return notes, sorted(set(tags))


async def _merge_registry_items(conn, from_item_id: UUID, to_item_id: UUID) -> UUID:
    if from_item_id == to_item_id:
        return to_item_id

    from_row = await conn.fetchrow("SELECT * FROM registry.items WHERE id = $1", from_item_id)
    to_row = await conn.fetchrow("SELECT * FROM registry.items WHERE id = $1", to_item_id)
    if not from_row or not to_row:
        return to_item_id

    from_metadata = _metadata_dict(from_row["metadata"])
    to_metadata = _metadata_dict(to_row["metadata"])
    merged_metadata = dict(from_metadata)
    merged_metadata.update(to_metadata)
    merged_metadata["user_tags"] = sorted(
        {
            str(tag).strip()
            for tag in [*from_metadata.get("user_tags", []), *to_metadata.get("user_tags", [])]
            if isinstance(tag, str) and str(tag).strip()
        }
    )
    note_search_lines = [
        line.strip()
        for line in [from_metadata.get("note_search", ""), to_metadata.get("note_search", "")]
        if isinstance(line, str) and line.strip()
    ]
    if note_search_lines:
        merged_metadata["note_search"] = "\n".join(dict.fromkeys(note_search_lines))

    await conn.execute("UPDATE registry.captures SET item_id = $2 WHERE item_id = $1", from_item_id, to_item_id)
    await conn.execute("UPDATE registry.jobs SET item_id = $2 WHERE item_id = $1", from_item_id, to_item_id)
    await conn.execute(
        """
        UPDATE registry.items
        SET original_url = CASE
                WHEN title IS NULL AND summary IS NULL AND why_it_matters IS NULL
                    THEN COALESCE($2, original_url)
                ELSE original_url
            END,
            canonical_host = COALESCE(NULLIF(canonical_host, ''), $3),
            source_kind = CASE
                WHEN source_kind = 'unknown' THEN $4
                ELSE source_kind
            END,
            capture_channel = COALESCE(NULLIF(capture_channel, ''), $5),
            review_state = CASE
                WHEN review_state = 'inbox' OR $6 = 'inbox' THEN 'inbox'
                WHEN review_state = 'reviewed' OR $6 = 'reviewed' THEN 'reviewed'
                ELSE 'archived'
            END,
            metadata = $7::jsonb,
            raw_archive_path = COALESCE(raw_archive_path, $8),
            first_captured_at = LEAST(first_captured_at, $9),
            last_captured_at = GREATEST(last_captured_at, $10),
            processed_at = COALESCE(processed_at, $11),
            last_error = COALESCE(last_error, $12)
        WHERE id = $1
        """,
        to_item_id,
        from_row["original_url"],
        from_row["canonical_host"],
        from_row["source_kind"],
        from_row["capture_channel"],
        from_row["review_state"],
        json.dumps(merged_metadata),
        from_row["raw_archive_path"],
        from_row["first_captured_at"],
        from_row["last_captured_at"],
        from_row["processed_at"],
        from_row["last_error"],
    )
    await conn.execute("DELETE FROM registry.items WHERE id = $1", from_item_id)
    return to_item_id


async def process_registry_item(item_id: UUID, *, reprocess: bool = False) -> dict[str, Any]:
    async with get_conn() as conn:
        async with conn.transaction():
            pending_job_id = await conn.fetchval(
                """
                UPDATE registry.jobs
                SET status = 'processing',
                    attempt_count = attempt_count + 1,
                    started_at = NOW()
                WHERE id = (
                    SELECT id
                    FROM registry.jobs
                    WHERE item_id = $1
                      AND job_type = $2
                      AND status IN ('pending', 'failed')
                    ORDER BY created_at DESC
                    LIMIT 1
                )
                RETURNING id
                """,
                item_id,
                "reprocess" if reprocess else "process",
            )
            if pending_job_id is None:
                pending_job_id = await conn.fetchval(
                    """
                    INSERT INTO registry.jobs (item_id, job_type, status, attempt_count, started_at)
                    VALUES ($1, $2, 'processing', 1, NOW())
                    RETURNING id
                    """,
                    item_id,
                    "reprocess" if reprocess else "process",
                )

            item = await _fetch_item(conn, item_id)
            if not item:
                raise ValueError(f"registry item {item_id} not found")

            await conn.execute(
                "UPDATE registry.items SET processing_status = 'processing', last_error = NULL WHERE id = $1",
                item_id,
            )

    async with get_conn() as conn:
        notes, user_tags = await _latest_capture_context(conn, item_id)
        capture_count = await conn.fetchval("SELECT COUNT(*) FROM registry.captures WHERE item_id = $1", item_id)

    try:
        deep = await canonicalize_url(item["canonical_url"], deep=True)
        extracted = await extract_registry_content(deep)
        html_canonical = extracted.metadata.get("html_canonical_url")
        if html_canonical:
            html_candidate = await canonicalize_url(html_canonical, deep=False)
            if html_candidate.canonical_url:
                deep = html_candidate

        async with get_conn() as conn:
            async with conn.transaction():
                lookup_urls = _scheme_equivalent_urls(deep.canonical_url, deep.source_kind)
                if deep.canonical_url != item["canonical_url"] or len(lookup_urls) > 1:
                    existing = await conn.fetchrow(
                        """
                        SELECT id
                        FROM registry.items
                        WHERE canonical_url = ANY($1::text[]) AND id <> $2
                        ORDER BY
                            CASE
                                WHEN canonical_url = $3 THEN 0
                                ELSE 1
                            END,
                            last_captured_at DESC
                        LIMIT 1
                        """,
                        lookup_urls,
                        item_id,
                        deep.canonical_url,
                    )
                    if existing:
                        item_id = await _merge_registry_items(conn, item_id, existing["id"])
                    if deep.canonical_url != item["canonical_url"]:
                        await conn.execute(
                            """
                            UPDATE registry.items
                            SET canonical_url = $2,
                                canonical_host = $3,
                                source_kind = $4
                            WHERE id = $1
                            """,
                            item_id,
                            deep.canonical_url,
                            deep.canonical_host,
                            deep.source_kind,
                        )
                    item = await _fetch_item(conn, item_id)

        async with get_conn() as conn:
            notes, user_tags = await _latest_capture_context(conn, item_id)
            capture_count = await conn.fetchval("SELECT COUNT(*) FROM registry.captures WHERE item_id = $1", item_id)

        summary = await summarize_registry_item(
            canonical_url=deep.canonical_url,
            source_kind=deep.source_kind,
            extracted=extracted,
            user_tags=user_tags,
            user_notes=notes,
        )
        archive_path = archive_registry_content(item_id, deep.source_kind, deep.canonical_host, deep.canonical_url, extracted)

        metadata = _metadata_dict(item["metadata"])
        metadata.update(extracted.metadata)
        metadata["user_tags"] = user_tags
        if notes:
            metadata["note_search"] = "\n".join(notes)
        metadata["extraction_mode"] = extracted.extraction_mode
        metadata["capture_count"] = int(capture_count or 0)

        processing_status = "ready" if any([summary["summary"], summary["title"], deep.canonical_url]) else "failed"
        async with get_conn() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE registry.items
                    SET canonical_url = $2,
                        canonical_host = $3,
                        source_kind = $4,
                        title = $5,
                        summary = $6,
                        why_it_matters = $7,
                        key_takeaways = $8,
                        topics = $9,
                        metadata = $10::jsonb,
                        raw_archive_path = $11,
                        processing_status = $12,
                        processed_at = CASE WHEN $12 = 'ready' THEN NOW() ELSE processed_at END,
                        last_error = CASE WHEN $12 = 'failed' THEN COALESCE(last_error, 'processing_failed') ELSE NULL END
                    WHERE id = $1
                    """,
                    item_id,
                    deep.canonical_url,
                    deep.canonical_host,
                    deep.source_kind,
                    summary["title"],
                    summary["summary"],
                    summary["why_it_matters"],
                    summary["key_takeaways"],
                    summary["topics"],
                    json.dumps(metadata),
                    archive_path,
                    processing_status,
                )
                await conn.execute(
                    """
                    UPDATE registry.jobs
                    SET status = 'completed',
                        completed_at = NOW()
                    WHERE id = $1
                    """,
                    pending_job_id,
                )
        return {"item_id": item_id, "processing_status": processing_status}
    except Exception as exc:
        async with get_conn() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE registry.items
                    SET processing_status = 'failed',
                        last_error = $2
                    WHERE id = $1
                    """,
                    item_id,
                    str(exc),
                )
                await conn.execute(
                    """
                    UPDATE registry.jobs
                    SET status = 'failed',
                        error_message = $2,
                        completed_at = NOW()
                    WHERE id = $1
                    """,
                    pending_job_id,
                    str(exc),
                )
        raise


async def query_registry(
    *,
    query: str | None,
    source_kind: str | None,
    review_state: str | None,
    from_ts,
    to_ts,
    topics: list[str],
    user_tags: list[str],
    limit: int,
    page: int,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[str] = []
    params: list[Any] = []
    idx = 0

    if query:
        idx += 1
        conditions.append(f"i.tsv @@ websearch_to_tsquery('english', ${idx})")
        params.append(query)
        rank_expr = f"ts_rank_cd(i.tsv, websearch_to_tsquery('english', ${idx}))"
    else:
        rank_expr = "0"

    if source_kind:
        idx += 1
        conditions.append(f"i.source_kind = ${idx}")
        params.append(source_kind)

    if review_state:
        idx += 1
        conditions.append(f"i.review_state = ${idx}")
        params.append(review_state)

    if from_ts:
        idx += 1
        conditions.append(f"i.last_captured_at >= ${idx}")
        params.append(from_ts)

    if to_ts:
        idx += 1
        conditions.append(f"i.last_captured_at <= ${idx}")
        params.append(to_ts)

    if topics:
        idx += 1
        conditions.append(f"i.topics && ${idx}::text[]")
        params.append(topics)

    if user_tags:
        idx += 1
        conditions.append(
            f"""
            EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(COALESCE(i.metadata->'user_tags', '[]'::jsonb)) AS tag(value)
                WHERE tag.value = ANY(${idx}::text[])
            )
            """
        )
        params.append(user_tags)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    offset = max(page - 1, 0) * limit
    idx += 1
    params.append(limit)
    idx += 1
    params.append(offset)

    async with get_conn() as conn:
        rows = await conn.fetch(
            f"""
            SELECT
                i.*,
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'id', c.id,
                                'captured_at', c.captured_at,
                                'user_note', c.user_note,
                                'user_tags', c.user_tags
                            )
                            ORDER BY c.captured_at DESC
                        )
                        FROM registry.captures c
                        WHERE c.item_id = i.id
                    ),
                    '[]'::json
                ) AS captures,
                {rank_expr} AS rank
            FROM registry.items i
            WHERE {where_clause}
            ORDER BY rank DESC, i.last_captured_at DESC
            LIMIT ${idx - 1}
            OFFSET ${idx}
            """,
            *params,
        )
        total = await conn.fetchval(f"SELECT COUNT(*) FROM registry.items i WHERE {where_clause}", *params[:-2])

    return [dict(row) for row in rows], int(total or 0)


async def list_registry(
    *,
    review_state: str | None,
    source_kind: str | None,
    topics: list[str],
    user_tags: list[str],
    from_ts,
    to_ts,
    limit: int,
    page: int,
    sort: str,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[str] = []
    params: list[Any] = []
    idx = 0

    if source_kind:
        idx += 1
        conditions.append(f"i.source_kind = ${idx}")
        params.append(source_kind)

    if review_state:
        idx += 1
        conditions.append(f"i.review_state = ${idx}")
        params.append(review_state)

    if from_ts:
        idx += 1
        conditions.append(f"i.last_captured_at >= ${idx}")
        params.append(from_ts)

    if to_ts:
        idx += 1
        conditions.append(f"i.last_captured_at <= ${idx}")
        params.append(to_ts)

    if topics:
        idx += 1
        conditions.append(f"i.topics && ${idx}::text[]")
        params.append(topics)

    if user_tags:
        idx += 1
        conditions.append(
            f"""
            EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(COALESCE(i.metadata->'user_tags', '[]'::jsonb)) AS tag(value)
                WHERE tag.value = ANY(${idx}::text[])
            )
            """
        )
        params.append(user_tags)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    offset = max(page - 1, 0) * limit
    idx += 1
    params.append(limit)
    idx += 1
    params.append(offset)
    order_direction = "ASC" if sort == "oldest" else "DESC"

    async with get_conn() as conn:
        rows = await conn.fetch(
            f"""
            SELECT
                i.*,
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'id', c.id,
                                'captured_at', c.captured_at,
                                'user_note', c.user_note,
                                'user_tags', c.user_tags
                            )
                            ORDER BY c.captured_at DESC
                        )
                        FROM registry.captures c
                        WHERE c.item_id = i.id
                    ),
                    '[]'::json
                ) AS captures
            FROM registry.items i
            WHERE {where_clause}
            ORDER BY i.last_captured_at {order_direction}
            LIMIT ${idx - 1}
            OFFSET ${idx}
            """,
            *params,
        )
        total = await conn.fetchval(f"SELECT COUNT(*) FROM registry.items i WHERE {where_clause}", *params[:-2])

    return [dict(row) for row in rows], int(total or 0)


async def review_registry_item(
    item_id: UUID,
    action: str,
    *,
    actor_type: str = "tars",
    actor_id: str | None = "registry_api",
    reason: str | None = None,
) -> dict[str, Any]:
    mapping = {"mark_reviewed": "reviewed", "archive": "archived", "mark_inbox": "inbox"}
    new_state = mapping[action]
    async with get_conn() as conn, conn.transaction():
        current = await conn.fetchrow(
            """
            SELECT id, review_state, title, canonical_url
            FROM registry.items
            WHERE id = $1
            FOR UPDATE
            """,
            item_id,
        )
        if not current:
            raise ValueError(f"registry item {item_id} not found")

        row = await conn.fetchrow(
            """
            UPDATE registry.items
            SET review_state = $2
            WHERE id = $1
            RETURNING id, review_state, title, canonical_url
            """,
            item_id,
            new_state,
        )
        mutation = await record_mutation(
            conn,
            actor_type=actor_type,
            actor_id=actor_id,
            subsystem="registry",
            mutation_type="review_state_change",
            target_id=item_id,
            reason=reason or f"registry review action: {action}",
            before_state={"review_state": current["review_state"]},
            after_state={"review_state": new_state},
            rollback_mode="inverse_mutation",
            rollback_status="available",
            metadata={"action": action},
        )
    response = dict(row)
    response["mutation_id"] = mutation["id"]
    return response
