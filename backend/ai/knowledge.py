"""Company knowledge indexing and hybrid semantic retrieval.

Active policy PDFs are split into searchable chunks. Retrieval uses a hybrid of
lexical signals and optional sentence embeddings. Sentence-transformers is an
optional runtime dependency so SQLite/local development remains usable even if
the model is not installed; when unavailable the deterministic lexical scorer
is retained as a safe fallback.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter

from django.conf import settings

from .models import KnowledgeChunk

CHUNK_WORD_SIZE = 220
MAX_SNIPPET_CHARS = 1400
MIN_TERM_LENGTH = 3
SEMANTIC_WEIGHT = 0.68
LEXICAL_WEIGHT = 0.32
SEMANTIC_CANDIDATE_LIMIT = 2500

_STOPWORDS = {
    "the", "and", "for", "with", "what", "when", "where", "which", "how", "are", "is",
    "my", "me", "i", "of", "to", "a", "an", "in", "on", "do", "does", "can", "tell",
    "show", "please", "about", "this", "that", "from", "give", "get", "have", "has", "be",
    "it", "or", "as", "at", "by", "your", "you", "our", "company", "current", "latest",
}

_SYNONYMS = {
    "salary": {"salary", "pay", "compensation", "earnings", "gross", "income", "wages"},
    "leave": {"leave", "leaves", "timeoff", "pto", "vacation", "absence", "holiday"},
    "attendance": {"attendance", "present", "punch", "checkin", "checkout", "hours", "worked"},
    "working": {"working", "work", "hours", "shift", "schedule", "workinghours"},
    "policy": {"policy", "policies", "rule", "rules", "guideline", "procedure", "regulation"},
    "holiday": {"holiday", "holidays", "off", "weeklyoff", "calendar", "weekend"},
    "payroll": {"payroll", "payslip", "payslips", "deduction", "net", "gross", "pf", "tax"},
    "employee": {"employee", "staff", "worker", "member", "person", "user"},
    "hod": {"hod", "manager", "head", "departmenthead", "department"},
    "admin": {"admin", "administrator", "superadmin"},
}

_ROLE_ALIASES = {
    "EMPLOYEE": {"employee", "staff", "worker"},
    "HOD": {"hod", "head of department", "department head", "manager"},
    "SUPER_ADMIN": {"super admin", "superadmin", "administrator", "admin"},
}

_embedding_model = None
_embedding_failed = False
_embedding_cache = {}


def extract_text_from_pdf(file_path):
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text, words_per_chunk=CHUNK_WORD_SIZE):
    """Create smaller coherent chunks while retaining document order."""
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n\s*\n+", text or "")]
    paragraphs = [part for part in paragraphs if part]
    chunks = []
    current = []
    current_count = 0
    for paragraph in paragraphs:
        words = paragraph.split()
        if current and current_count + len(words) > words_per_chunk:
            chunks.append(" ".join(current).strip())
            current = []
            current_count = 0
        if len(words) <= words_per_chunk:
            current.append(paragraph)
            current_count += len(words)
        else:
            for i in range(0, len(words), words_per_chunk):
                part = " ".join(words[i:i + words_per_chunk]).strip()
                if part:
                    if current:
                        chunks.append(" ".join(current).strip())
                        current = []
                        current_count = 0
                    chunks.append(part)
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def _semantic_enabled():
    return bool(getattr(settings, "AI_SEMANTIC_RETRIEVAL_ENABLED", True))


def _get_embedding_model():
    global _embedding_model, _embedding_failed
    if not _semantic_enabled() or _embedding_failed:
        return None
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
        model_name = getattr(settings, "AI_SEMANTIC_MODEL", "all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(model_name)
        return _embedding_model
    except Exception:
        _embedding_failed = True
        return None


def semantic_retrieval_available():
    return _get_embedding_model() is not None


def _encode_texts(texts):
    model = _get_embedding_model()
    if model is None or not texts:
        return None
    try:
        vectors = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [list(map(float, vector)) for vector in vectors]
    except Exception:
        return None


def index_policy_document(policy_document):
    """Extract PDF text and replace this document's searchable chunks/embeddings."""
    text = extract_text_from_pdf(policy_document.file.path)
    chunks = chunk_text(text)
    KnowledgeChunk.objects.filter(policy_document=policy_document).delete()

    embeddings = _encode_texts(chunks) if chunks else None
    objects = []
    for i, chunk in enumerate(chunks):
        objects.append(KnowledgeChunk(
            policy_document=policy_document,
            chunk_index=i,
            chunk_text=chunk,
            semantic_embedding=json.dumps(embeddings[i], separators=(",", ":")) if embeddings else "",
        ))
    KnowledgeChunk.objects.bulk_create(objects)
    return len(chunks)


def _tokenize(value):
    return [
        token for token in re.findall(r"[\w][\w'-]*", str(value or "").lower(), flags=re.UNICODE)
        if len(token) >= MIN_TERM_LENGTH and token not in _STOPWORDS
    ]


def _expand_terms(query, role=None):
    raw_tokens = _tokenize(query)
    terms = set(raw_tokens)
    for canonical, aliases in _SYNONYMS.items():
        if canonical in raw_tokens or any(alias in raw_tokens for alias in aliases):
            terms.update(aliases)
    if role and re.search(r"\b(my|mine|me|i)\b", str(query or "").lower()):
        terms.update(_ROLE_ALIASES.get(str(role).upper(), set()))
    return terms


def _personal_salary_query(query):
    normalized = re.sub(r"\s+", " ", str(query or "").strip().lower())
    return bool(re.search(r"\b(my|mine|me|i)\b", normalized) and re.search(r"\b(salary|pay|compensation|earnings|income|wages)\b", normalized))


def _score_chunk(chunk, query, role=None):
    text = chunk.chunk_text or ""
    lower = text.lower()
    doc = chunk.policy_document
    title = (doc.title or "").lower()
    category = (doc.category or "").lower()
    raw_terms = _tokenize(query)
    terms = _expand_terms(query, role)
    if not terms:
        return 0.0, []

    tf = Counter(_tokenize(text))
    score = 0.0
    matched = []
    for term in terms:
        count = tf.get(term, 0)
        if count:
            matched.append(term)
            score += 3.0 + min(5.0, math.log1p(count) * 2.2)
        if re.search(r"\b" + re.escape(term) + r"\b", title):
            score += 4.0
        if term in category:
            score += 2.0

    phrase = re.sub(r"\s+", " ", str(query or "").strip().lower())
    if phrase and phrase in lower:
        score += 7.0

    if _personal_salary_query(query) and role:
        role_terms = _ROLE_ALIASES.get(str(role).upper(), set())
        if any(term in tf for term in role_terms):
            score += 8.0
        if any(term in tf for term in ("salary", "pay", "compensation", "gross", "income")):
            score += 5.0

    return score, matched


def _lexical_similarity(score):
    # Scores vary by query length; squash into a stable 0..1 band before hybrid fusion.
    return 1.0 - math.exp(-max(0.0, score) / 24.0)


def _load_embedding(chunk):
    raw = getattr(chunk, "semantic_embedding", "") or ""
    if not raw:
        return None
    key = (chunk.pk, hashlib.sha1(raw.encode("utf-8")).hexdigest())
    if key in _embedding_cache:
        return _embedding_cache[key]
    try:
        vector = json.loads(raw)
        if not isinstance(vector, list) or not vector:
            return None
        vector = [float(value) for value in vector]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    _embedding_cache[key] = vector
    return vector


def _cosine_from_normalized(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))


def _query_embedding(query):
    vectors = _encode_texts([query])
    return vectors[0] if vectors else None


def _make_snippet(text, terms, query):
    compact = re.sub(r"\s+", " ", str(text or "").strip())
    if len(compact) <= MAX_SNIPPET_CHARS:
        return compact
    lower = compact.lower()
    positions = []
    for term in terms:
        pos = lower.find(term.lower())
        if pos >= 0:
            positions.append(pos)
    phrase_pos = lower.find(re.sub(r"\s+", " ", str(query or "").strip().lower()))
    if phrase_pos >= 0:
        positions.append(phrase_pos)
    center = min(positions) if positions else 0
    start = max(0, center - 420)
    end = min(len(compact), start + MAX_SNIPPET_CHARS)
    snippet = compact[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(compact):
        snippet += "…"
    return snippet


def _format_result(chunk, score, matched, query):
    return {
        "document_title": chunk.policy_document.title,
        "category": chunk.policy_document.category,
        "text": _make_snippet(chunk.chunk_text, matched, query),
        "relevance_score": round(score, 3),
    }


def search_company_policy(query, limit=5, role=None):
    """Return the most relevant evidence using hybrid lexical/semantic ranking."""
    query = re.sub(r"\s+", " ", str(query or "").strip())
    if not query:
        return []
    terms = sorted(_expand_terms(query, role))
    qs = list(
        KnowledgeChunk.objects.filter(policy_document__is_active=True)
        .select_related("policy_document")
    )
    if not qs:
        return []

    semantic_query = _query_embedding(query) if semantic_retrieval_available() else None
    persisted_vectors = {chunk.pk: _load_embedding(chunk) for chunk in qs} if semantic_query is not None else {}
    missing = [chunk for chunk in qs if semantic_query is not None and persisted_vectors.get(chunk.pk) is None]
    transient_vectors = {}
    if semantic_query is not None and missing:
        encoded = _encode_texts([chunk.chunk_text or "" for chunk in missing])
        if encoded:
            transient_vectors = {chunk.pk: vector for chunk, vector in zip(missing, encoded)}

    scored = []
    for chunk in qs:
        lexical_score, matched = _score_chunk(chunk, query, role=role)
        lexical_norm = _lexical_similarity(lexical_score)
        semantic_norm = 0.0
        vector = persisted_vectors.get(chunk.pk) or transient_vectors.get(chunk.pk)
        if semantic_query is not None and vector is not None:
            semantic_norm = max(0.0, _cosine_from_normalized(semantic_query, vector))
            fused = semantic_norm * SEMANTIC_WEIGHT + lexical_norm * LEXICAL_WEIGHT
        else:
            fused = lexical_norm
        if fused > 0:
            scored.append((fused, chunk, matched))

    scored.sort(key=lambda item: (item[0], -item[1].chunk_index), reverse=True)
    return [_format_result(chunk, score, matched, query) for score, chunk, matched in scored[:max(1, min(int(limit), 10))]]
