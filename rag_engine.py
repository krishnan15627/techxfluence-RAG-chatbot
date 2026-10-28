"""
rag_engine.py - the "R" (Retrieval) part of RAG for TechXfluence AI.

What it does
------------
1. Loads every .txt / .md / .json file inside the  data/  folder.
2. Splits them into small "chunks" (one chunk = part of one SECTION).
3. Builds a BM25 keyword index (pure Python - no extra libraries needed).
4. For a question, returns the best-matching chunks + their sources.
5. Builds the final prompt that is sent to the local LLM.

Everything is plain Python so beginners can read and modify it.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

NOT_FOUND_MESSAGE = (
    "I couldn't find that information in the available TechXfluence resources. "
    "Please contact the official team."
)
WELCOME_MESSAGE = "Welcome to TechXfluence AI. How can I help you today?"

# ----------------------------------------------------------------------------
# Tunable settings (change these if retrieval feels too strict / too loose)
# ----------------------------------------------------------------------------
MAX_CHUNK_CHARS = 900     # long sections are split into pieces of about this size
TOP_K = 4                 # how many chunks are sent to the LLM
MIN_COVERAGE = 0.4        # share of question keywords a chunk must match
MIN_SCORE = 1.0           # minimum BM25 score to count as "relevant"

# Words that carry no meaning for search
STOPWORDS = set("""
a an the is are was were be been being am do does did of to in on at for from by with about
and or but if so as it its this that these those i you he she we they me my your our their
what which who whom whose when why how can could would should will shall may might must
tell me please give show explain want need know like get have has had any some there here
into over under out up down than then too very just also more most much many
techxfluence techxfluences tech
""".split())

# Tiny synonym map: helps when users use different words than the website.
SYNONYMS = {
    "price": ["cost", "fee", "rs", "pricing", "rupee", "pay"],
    "cost": ["price", "fee", "rs", "pricing"],
    "fee": ["price", "cost", "pricing"],
    "fees": ["price", "cost", "pricing"],
    "plan": ["membership", "tier", "member"],
    "join": ["membership", "member", "become"],
    "job": ["career", "role", "apply", "position", "opening"],
    "jobs": ["career", "role", "apply", "position", "opening"],
    "hiring": ["career", "role", "apply", "opening"],
    "vacancy": ["career", "role", "opening"],
    "email": ["contact", "mail", "enquiries"],
    "mail": ["email", "contact"],
    "phone": ["contact", "number", "call"],
    "address": ["location", "chennai", "contact"],
    "office": ["location", "chennai", "contact"],
    "reach": ["contact", "email"],
    "host": ["organizer", "organiser", "submit", "hosting"],
    "organize": ["host", "organizer", "hosting"],
    "organise": ["host", "organizer", "hosting"],
    "service": ["design", "development", "website", "services"],
    "services": ["design", "development", "website", "service"],
    "website": ["web", "design", "development"],
    "event": ["meetup", "workshop", "hackathon", "events"],
    "events": ["meetup", "workshop", "hackathon", "event"],
    "course": ["workshop", "learn"],
    "learn": ["workshop", "mentorship", "learning"],
    "company": ["about", "community", "mission"],
    "founder": ["team", "leadership", "about"],
    "ceo": ["team", "leadership", "about"],
    "mission": ["vision", "values", "about"],
    "located": ["location", "chennai", "address"],
    "locate": ["location", "chennai", "address"],
    "location": ["chennai", "address", "india"],
    "based": ["location", "chennai"],
    "city": ["location", "chennai"],
}


def stem(word: str) -> str:
    """Very small stemmer so 'events' matches 'event', 'hosting' matches 'host'."""
    for suffix in ("ingly", "ing", "edly", "ed", "ies", "es", "s", "ly"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            if suffix == "ies":
                return word[: -len(suffix)] + "y"
            return word[: -len(suffix)]
    return word


def tokenize(text: str, keep_stopwords: bool = False) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    if not keep_stopwords:
        words = [w for w in words if w not in STOPWORDS]
    return [stem(w) for w in words]


# ----------------------------------------------------------------------------
# Data classes
# ----------------------------------------------------------------------------
@dataclass
class Chunk:
    text: str
    title: str
    source: str       # website URL (or file name when no URL is given)
    filename: str     # file inside data/ that this chunk came from
    tokens: list[str]


@dataclass
class Retrieved:
    chunk: Chunk
    score: float
    coverage: float


# ----------------------------------------------------------------------------
# Loading + chunking
# ----------------------------------------------------------------------------
SECTION_RE = re.compile(r"^===\s*SECTION:\s*(.+?)\s*===\s*$", re.IGNORECASE)


def _split_long(text: str, limit: int) -> list[str]:
    """Split a long body at line breaks so each piece stays under `limit`."""
    pieces, current = [], ""
    for line in text.splitlines():
        if current and len(current) + len(line) + 1 > limit:
            pieces.append(current.strip())
            current = ""
        current += line + "\n"
    if current.strip():
        pieces.append(current.strip())
    return pieces


def _parse_sectioned_text(raw: str, filename: str) -> list[tuple[str, str, str]]:
    """Return a list of (title, source, body) from the === SECTION: === format."""
    sections, title, source, body = [], None, filename, []

    def flush():
        text = "\n".join(body).strip()
        if title and text:
            sections.append((title, source, text))

    for line in raw.splitlines():
        m = SECTION_RE.match(line.strip())
        if m:
            flush()
            title, source, body = m.group(1), filename, []
            continue
        if title is None:
            continue  # header comments before the first section
        if line.strip().upper().startswith("SOURCE:"):
            source = line.split(":", 1)[1].strip() or filename
            continue
        body.append(line)
    flush()

    # Plain text file with no SECTION markers -> split by blank lines.
    if not sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        for i, p in enumerate(paragraphs, 1):
            if not p.startswith("#"):
                sections.append((f"{filename} - part {i}", filename, p))
    return sections


def _parse_json(raw: str, filename: str) -> list[tuple[str, str, str]]:
    """JSON format: [{"title": "...", "source": "...", "text": "..."}, ...]"""
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("sections", [data])
    out = []
    for item in data:
        text = str(item.get("text", "")).strip()
        if text:
            out.append((item.get("title", filename), item.get("source", filename), text))
    return out


def load_chunks(data_dir: Path = DATA_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    if not data_dir.exists():
        return chunks
    for path in sorted(data_dir.rglob("*")):
        if path.suffix.lower() not in {".txt", ".md", ".json"} or not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        try:
            if path.suffix.lower() == ".json":
                sections = _parse_json(raw, path.name)
            else:
                sections = _parse_sectioned_text(raw, path.name)
        except Exception:
            continue  # skip files that cannot be parsed
        for title, source, body in sections:
            for piece in _split_long(body, MAX_CHUNK_CHARS):
                # Title is part of the searchable text so "membership" finds the Membership section.
                tokens = tokenize(f"{title} {title} {piece}")
                chunks.append(Chunk(piece, title, source, path.name, tokens))
    return chunks


# ----------------------------------------------------------------------------
# The retriever
# ----------------------------------------------------------------------------
class Retriever:
    def __init__(self, chunks: list[Chunk] | None = None):
        self.chunks = chunks if chunks is not None else load_chunks()
        self.k1, self.b = 1.5, 0.75
        n = len(self.chunks)
        self.avg_len = (sum(len(c.tokens) for c in self.chunks) / n) if n else 0.0
        df: Counter = Counter()
        for c in self.chunks:
            df.update(set(c.tokens))
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(c.tokens) for c in self.chunks]

    # -- helpers -----------------------------------------------------------
    @property
    def ready(self) -> bool:
        return bool(self.chunks)

    def _expand(self, term: str) -> list[str]:
        """A query word + its synonyms (all stemmed)."""
        words = [term] + [stem(s) for s in SYNONYMS.get(term, [])]
        return list(dict.fromkeys(words))

    def _bm25(self, idx: int, terms: list[str], weight: float = 1.0) -> float:
        tf, length = self.tf[idx], len(self.chunks[idx].tokens)
        score = 0.0
        for t in terms:
            f = tf.get(t, 0)
            if not f:
                continue
            denom = f + self.k1 * (1 - self.b + self.b * length / (self.avg_len or 1))
            score += weight * self.idf.get(t, 0.0) * f * (self.k1 + 1) / denom
        return score

    # -- main search -------------------------------------------------------
    def search(self, question: str, top_k: int = TOP_K) -> list[Retrieved]:
        if not self.chunks:
            return []
        # Query words as the user wrote them (stemmed once). Synonyms are looked up
        # on the raw word first, then stemmed, so "jobs" can find "career".
        raw_words = [w for w in re.findall(r"[a-z0-9]+", question.lower()) if w not in STOPWORDS]
        if not raw_words:
            return []

        results: list[Retrieved] = []
        for i, chunk in enumerate(self.chunks):
            score, matched = 0.0, 0
            for w in raw_words:
                direct = stem(w)
                syns = [stem(s) for s in SYNONYMS.get(w, [])]
                s = self._bm25(i, [direct])
                s_syn = self._bm25(i, syns, weight=0.5)
                if s > 0 or s_syn > 0:
                    matched += 1
                score += s + s_syn
            coverage = matched / len(raw_words)
            if score >= MIN_SCORE and coverage >= MIN_COVERAGE:
                results.append(Retrieved(chunk, score, coverage))

        results.sort(key=lambda r: (r.score, r.coverage), reverse=True)
        # Drop weak tail results: keep chunks scoring at least 35% of the best.
        if results:
            best = results[0].score
            results = [r for r in results if r.score >= 0.35 * best]
        return results[:top_k]


# ----------------------------------------------------------------------------
# Prompt building
# ----------------------------------------------------------------------------
SYSTEM_PROMPT = f"""You are TechXfluence AI, the official assistant for the TechXfluence technology community.

STRICT RULES:
1. Answer ONLY using the CONTEXT provided. Never use outside knowledge.
2. Never invent company details, event dates, prices, names, or contact information.
3. If the CONTEXT does not contain the answer, reply with exactly this sentence and nothing else:
   "{NOT_FOUND_MESSAGE}"
4. Be clear, friendly and concise. Use short bullet points for lists.
5. Event details, prices and job openings can change - mention checking the official website when you give them.
6. Do not mention the word "CONTEXT" in your answer."""


def build_prompt(question: str, retrieved: list[Retrieved]) -> str:
    blocks = []
    for n, r in enumerate(retrieved, 1):
        blocks.append(f"[Source {n}: {r.chunk.title} | {r.chunk.source}]\n{r.chunk.text}")
    context = "\n\n".join(blocks)
    return f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER (use only the context above):"


def unique_sources(retrieved: list[Retrieved]) -> list[dict]:
    """Deduplicated list of sources to show under an answer."""
    seen, out = set(), []
    for r in retrieved:
        key = (r.chunk.source, r.chunk.title)
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": r.chunk.title, "source": r.chunk.source, "file": r.chunk.filename})
    return out


def is_not_found(answer: str) -> bool:
    """True when the LLM itself said the information is missing."""
    return "couldn't find that information" in answer.lower()


_GREETING_RE = re.compile(r"^\s*(hi|hello|hey|hii+|vanakkam|good (morning|afternoon|evening)|thanks?|thank you|ok|okay)\W*$", re.I)


def is_greeting(text: str) -> bool:
    return bool(_GREETING_RE.match(text))
