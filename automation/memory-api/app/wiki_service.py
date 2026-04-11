"""Filesystem-backed wiki search, proposal, and lint helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID, uuid4

from .config import settings

PAGE_TYPES = {"people", "companies", "projects", "topics", "syntheses", "sources"}
PROPOSAL_STATUSES = {"pending_review", "approved", "rejected"}
PLACEHOLDER_PATTERNS = (
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\[\[\s*placeholder\s*\]\]", re.IGNORECASE),
)


@dataclass
class WikiPage:
    page_ref: str
    page_type: str
    title: str
    body: str
    summary: str
    source_refs: list[str]
    tags: list[str]
    status: str | None
    updated_at: str | None
    confidence: str | None


def _vault_root() -> Path:
    return Path(settings.wiki_vault_root).expanduser()


def _pages_root() -> Path:
    return _vault_root() / "wiki"


def _proposal_root() -> Path:
    return Path(settings.wiki_proposal_root).expanduser()


def _proposal_bucket(status: str) -> Path:
    if status not in PROPOSAL_STATUSES:
        raise ValueError(f"unsupported proposal status: {status}")
    return _proposal_root() / status


def _outbox_root() -> Path:
    return _proposal_root() / "outbox"


def ensure_wiki_proposal_layout() -> None:
    for status in PROPOSAL_STATUSES:
        _proposal_bucket(status).mkdir(parents=True, exist_ok=True)
    (_outbox_root() / "pages").mkdir(parents=True, exist_ok=True)
    (_outbox_root() / "metadata").mkdir(parents=True, exist_ok=True)


def _normalize_page_ref(page_ref: str) -> PurePosixPath:
    candidate = PurePosixPath(page_ref.strip())
    if not str(candidate) or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("page_ref must be a safe relative path")
    if candidate.parts[0] != "wiki":
        raise ValueError("page_ref must live under wiki/")
    if candidate.suffix != ".md":
        raise ValueError("page_ref must point to a markdown file")
    return candidate


def _page_path(page_ref: str) -> Path:
    normalized = _normalize_page_ref(page_ref)
    return _vault_root().joinpath(*normalized.parts)


def _proposal_json_path(status: str, proposal_id: UUID) -> Path:
    return _proposal_bucket(status) / f"{proposal_id}.json"


def _proposal_markdown_path(status: str, proposal_id: UUID) -> Path:
    return _proposal_bucket(status) / f"{proposal_id}.md"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _parse_list_value(value: str) -> list[str]:
    stripped = value.strip()
    if not stripped:
        return []
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip()
        if not inner:
            return []
        return [piece.strip().strip("\"'") for piece in inner.split(",") if piece.strip()]
    return [piece.strip() for piece in stripped.split(",") if piece.strip()]


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    if len(lines) < 3:
        return {}, text

    frontmatter: dict[str, Any] = {}
    current_list_key: str | None = None
    end_index = None

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
        if line.startswith("- ") and current_list_key:
            frontmatter.setdefault(current_list_key, []).append(line[2:].strip().strip("\"'"))
            continue
        if ":" not in line:
            current_list_key = None
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "":
            frontmatter[key] = []
            current_list_key = key
            continue
        current_list_key = None
        if key in {"tags", "source_refs"}:
            frontmatter[key] = _parse_list_value(value)
        else:
            frontmatter[key] = value.strip("\"'")

    if end_index is None:
        return {}, text

    body = "\n".join(lines[end_index + 1 :]).strip()
    return frontmatter, body


def _serialize_frontmatter(frontmatter: dict[str, Any]) -> str:
    lines = ["---"]
    for key in ("title", "type", "status", "tags", "source_refs", "updated_at", "confidence"):
        value = frontmatter.get(key)
        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"{key}:")
            lines.extend(f"- {item}" for item in value)
            continue
        if value in (None, ""):
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"


def _title_from_body(body: str, fallback: str) -> str:
    first_line = body.splitlines()[0].strip() if body else ""
    return first_line.lstrip("# ").strip() or fallback


def _excerpt(body: str, query: str, *, max_length: int = 240) -> str:
    text = re.sub(r"\s+", " ", body).strip()
    if not text:
        return ""
    lowered = text.lower()
    normalized_query = query.strip().lower()
    if normalized_query and normalized_query in lowered:
        index = lowered.index(normalized_query)
        start = max(index - 70, 0)
        end = min(index + len(normalized_query) + 120, len(text))
        excerpt = text[start:end].strip()
    else:
        excerpt = text[:max_length].strip()
    return excerpt if len(excerpt) <= max_length else f"{excerpt[: max_length - 1].rstrip()}…"


def _page_type_for_path(path: Path) -> str:
    parts = path.relative_to(_pages_root()).parts
    if not parts:
        return "unknown"
    return parts[0] if parts[0] in PAGE_TYPES else "unknown"


def _updated_at_value(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_page(path: Path) -> WikiPage:
    raw = _read_text(path)
    frontmatter, body = _parse_frontmatter(raw)
    page_ref = path.relative_to(_vault_root()).as_posix()
    title = str(frontmatter.get("title") or _title_from_body(body, path.stem)).strip()
    page_type = str(frontmatter.get("type") or _page_type_for_path(path)).strip()
    source_refs = [str(item).strip() for item in frontmatter.get("source_refs", []) if str(item).strip()]
    tags = [str(item).strip() for item in frontmatter.get("tags", []) if str(item).strip()]
    return WikiPage(
        page_ref=page_ref,
        page_type=page_type,
        title=title,
        body=body,
        summary=_excerpt(body, ""),
        source_refs=source_refs,
        tags=tags,
        status=str(frontmatter.get("status")).strip() if frontmatter.get("status") else None,
        updated_at=str(frontmatter.get("updated_at")).strip() if frontmatter.get("updated_at") else None,
        confidence=str(frontmatter.get("confidence")).strip() if frontmatter.get("confidence") else None,
    )


def _iter_pages() -> list[WikiPage]:
    pages_root = _pages_root()
    if not pages_root.exists():
        return []
    pages: list[WikiPage] = []
    for path in sorted(pages_root.rglob("*.md")):
        if not path.is_file():
            continue
        pages.append(_load_page(path))
    return pages


def search_wiki_pages(*, query: str, limit: int = 5, page_types: list[str] | None = None) -> tuple[list[dict[str, Any]], int]:
    normalized_query = query.strip().lower()
    terms = [piece for piece in re.split(r"\W+", normalized_query) if piece]
    if not normalized_query:
        return [], 0

    matched: list[tuple[float, WikiPage]] = []
    for page in _iter_pages():
        if page_types and page.page_type not in page_types:
            continue

        title = page.title.lower()
        body = page.body.lower()
        refs = " ".join(page.source_refs).lower()
        tags = " ".join(page.tags).lower()
        page_type = page.page_type.lower()

        score = 0.0
        if normalized_query in title:
            score += 0.55
        if normalized_query in refs:
            score += 0.30
        if normalized_query in body:
            score += 0.25
        if normalized_query in tags:
            score += 0.15

        for term in terms:
            if term in title:
                score += 0.08
            if term in refs:
                score += 0.05
            if term in body:
                score += 0.03
            if term in tags or term in page_type:
                score += 0.02

        updated_at = _updated_at_value(page.updated_at)
        if updated_at:
            score += 0.04

        if score > 0:
            matched.append((round(min(score, 0.99), 2), page))

    matched.sort(
        key=lambda item: (
            item[0],
            _updated_at_value(item[1].updated_at) or datetime.min.replace(tzinfo=UTC),
            item[1].title.lower(),
        ),
        reverse=True,
    )

    results = [
        {
            "id": page.page_ref,
            "title": page.title,
            "summary": _excerpt(page.body, normalized_query),
            "body": page.body,
            "source_type": "wiki_page",
            "source": "wiki",
            "source_ref": page.page_ref,
            "page_ref": page.page_ref,
            "page_type": page.page_type,
            "source_refs": page.source_refs,
            "tags": page.tags,
            "updated_at": page.updated_at,
            "citation": f"wiki:{page.page_ref}",
            "score": score,
        }
        for score, page in matched[:limit]
    ]
    return results, len(matched)


def get_wiki_page(*, page_ref: str) -> dict[str, Any]:
    path = _page_path(page_ref)
    if not path.exists():
        raise FileNotFoundError(f"wiki page not found: {page_ref}")

    page = _load_page(path)
    return {
        "page_ref": page.page_ref,
        "page_type": page.page_type,
        "title": page.title,
        "body": page.body,
        "source_refs": page.source_refs,
        "tags": page.tags,
        "status": page.status,
        "updated_at": page.updated_at,
        "confidence": page.confidence,
    }


def render_wiki_markdown(
    *,
    title: str,
    page_type: str,
    content: str,
    source_refs: list[str],
    tags: list[str],
    status: str = "draft",
    confidence: str | None = None,
    updated_at: str | None = None,
) -> str:
    frontmatter = {
        "title": title,
        "type": page_type,
        "status": status,
        "tags": tags,
        "source_refs": source_refs,
        "updated_at": updated_at or datetime.now(UTC).isoformat(),
        "confidence": confidence,
    }
    body = content.strip()
    if body and not body.startswith("# "):
        body = f"# {title}\n\n{body}"
    return f"{_serialize_frontmatter(frontmatter)}\n\n{body.strip()}\n"


def create_wiki_proposal(
    *,
    page_type: str,
    title: str,
    content: str,
    source_refs: list[str],
    tags: list[str],
    actor: dict[str, Any],
    slug: str | None = None,
    page_ref: str | None = None,
    confidence: str | None = None,
) -> dict[str, Any]:
    ensure_wiki_proposal_layout()

    if page_type not in PAGE_TYPES:
        raise ValueError(f"page_type must be one of: {', '.join(sorted(PAGE_TYPES))}")

    normalized_page_ref = page_ref or f"wiki/{page_type}/{_slugify(slug or title)}.md"
    _normalize_page_ref(normalized_page_ref)

    now = datetime.now(UTC).isoformat()
    target_path = _page_path(normalized_page_ref)
    operation = "update" if target_path.exists() else "create"
    proposal_id = uuid4()

    markdown = render_wiki_markdown(
        title=title,
        page_type=page_type,
        content=content,
        source_refs=source_refs,
        tags=tags,
        status="proposed",
        confidence=confidence,
        updated_at=now,
    )

    proposal = {
        "proposal_id": str(proposal_id),
        "status": "pending_review",
        "created_at": now,
        "updated_at": now,
        "reviewed_at": None,
        "review_actor": None,
        "actor": actor,
        "operation": operation,
        "page_ref": normalized_page_ref,
        "page_type": page_type,
        "title": title,
        "tags": tags,
        "source_refs": source_refs,
        "confidence": confidence,
        "proposed_markdown": markdown,
    }

    _proposal_json_path("pending_review", proposal_id).write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    _proposal_markdown_path("pending_review", proposal_id).write_text(markdown, encoding="utf-8")
    return proposal


def _load_proposal(status: str, proposal_id: UUID) -> dict[str, Any]:
    path = _proposal_json_path(status, proposal_id)
    if not path.exists():
        raise FileNotFoundError(f"wiki proposal not found: {proposal_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_wiki_proposals(*, status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    ensure_wiki_proposal_layout()
    statuses = [status] if status else ["pending_review", "approved", "rejected"]
    proposals: list[dict[str, Any]] = []
    for current_status in statuses:
        if current_status not in PROPOSAL_STATUSES:
            raise ValueError(f"unsupported proposal status: {current_status}")
        for path in sorted(_proposal_bucket(current_status).glob("*.json"), reverse=True):
            proposals.append(json.loads(path.read_text(encoding="utf-8")))
    proposals.sort(key=lambda proposal: proposal.get("updated_at", ""), reverse=True)
    return proposals[:limit]


def review_wiki_proposal(*, proposal_id: UUID, action: str, actor: dict[str, Any]) -> dict[str, Any]:
    ensure_wiki_proposal_layout()
    if action not in {"approve", "reject"}:
        raise ValueError("action must be approve or reject")

    current_status = None
    current_json_path = None
    current_markdown_path = None
    proposal = None
    for status in PROPOSAL_STATUSES:
        json_path = _proposal_json_path(status, proposal_id)
        if json_path.exists():
            current_status = status
            current_json_path = json_path
            current_markdown_path = _proposal_markdown_path(status, proposal_id)
            proposal = json.loads(json_path.read_text(encoding="utf-8"))
            break

    if proposal is None or current_status is None or current_json_path is None or current_markdown_path is None:
        raise FileNotFoundError(f"wiki proposal not found: {proposal_id}")
    if current_status != "pending_review":
        raise ValueError(f"wiki proposal {proposal_id} is already {current_status}")

    new_status = "approved" if action == "approve" else "rejected"
    now = datetime.now(UTC).isoformat()
    proposal["status"] = new_status
    proposal["updated_at"] = now
    proposal["reviewed_at"] = now
    proposal["review_actor"] = actor

    new_json_path = _proposal_json_path(new_status, proposal_id)
    new_markdown_path = _proposal_markdown_path(new_status, proposal_id)
    new_json_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    new_markdown_path.write_text(proposal["proposed_markdown"], encoding="utf-8")
    current_json_path.unlink(missing_ok=True)
    current_markdown_path.unlink(missing_ok=True)

    outbox_page_path = None
    if new_status == "approved":
        outbox_page_path = _outbox_root() / "pages" / Path(proposal["page_ref"])
        outbox_page_path.parent.mkdir(parents=True, exist_ok=True)
        outbox_page_path.write_text(proposal["proposed_markdown"], encoding="utf-8")
        (_outbox_root() / "metadata" / f"{proposal_id}.json").write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    return {
        **proposal,
        "outbox_page_path": str(outbox_page_path) if outbox_page_path else None,
    }


def wiki_health() -> dict[str, Any]:
    ensure_wiki_proposal_layout()
    pages_root = _pages_root()
    page_count = len(list(pages_root.rglob("*.md"))) if pages_root.exists() else 0
    proposal_counts = {
        status: len(list(_proposal_bucket(status).glob("*.json")))
        for status in PROPOSAL_STATUSES
    }
    outbox_pages = len(list((_outbox_root() / "pages").rglob("*.md")))
    return {
        "status": "ready",
        "wiki_vault_root": str(_vault_root()),
        "wiki_pages_root": str(pages_root),
        "wiki_proposal_root": str(_proposal_root()),
        "page_count": page_count,
        "proposal_counts": proposal_counts,
        "outbox_pages": outbox_pages,
    }


def lint_wiki(*, limit: int = 50) -> dict[str, Any]:
    pages = _iter_pages()
    title_index: dict[str, list[str]] = {}

    orphan_pages: list[dict[str, Any]] = []
    missing_cross_links: list[dict[str, Any]] = []
    unresolved_placeholders: list[dict[str, Any]] = []
    stale_pages: list[dict[str, Any]] = []

    stale_cutoff = datetime.now(UTC) - timedelta(days=settings.wiki_stale_days)

    for page in pages:
        title_index.setdefault(page.title.strip().lower(), []).append(page.page_ref)

        if page.page_type in PAGE_TYPES and not page.source_refs:
            orphan_pages.append({"page_ref": page.page_ref, "title": page.title})

        if page.page_type not in {"sources"} and "[[" not in page.body:
            missing_cross_links.append({"page_ref": page.page_ref, "title": page.title})

        if any(pattern.search(page.body) for pattern in PLACEHOLDER_PATTERNS):
            unresolved_placeholders.append({"page_ref": page.page_ref, "title": page.title})

        updated_at = _updated_at_value(page.updated_at)
        if updated_at is None or updated_at < stale_cutoff:
            stale_pages.append({"page_ref": page.page_ref, "title": page.title, "updated_at": page.updated_at})

    duplicate_titles = [
        {"title": title, "page_refs": refs}
        for title, refs in title_index.items()
        if title and len(refs) > 1
    ]

    missing_control_pages = [
        control
        for control in ("index.md", "log.md", "schema.md")
        if not (_pages_root() / control).exists()
    ]

    return {
        "page_count": len(pages),
        "missing_control_pages": missing_control_pages,
        "orphan_pages": orphan_pages[:limit],
        "missing_cross_links": missing_cross_links[:limit],
        "unresolved_placeholders": unresolved_placeholders[:limit],
        "stale_pages": stale_pages[:limit],
        "potential_duplicate_titles": duplicate_titles[:limit],
    }
