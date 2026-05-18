"""Web search service — supplementary search via Serper API.
Serper provides SUPPLEMENTARY search results that are injected into the LLM prompt.
The PRIMARY search mechanism is Gemini's native Google Search grounding, which
performs live searches directly during inference.
When a Serper API key is configured, the service:
1. Extracts key signals from the job description (industry, tech stack, size hints)
2. Builds 2–3 targeted Google search queries
3. Calls Serper API to get real search results
4. Returns structured context injected into the LLM prompt as secondary evidence
Free tier: 2,500 searches/month — more than enough for a PoC.
"""

from __future__ import annotations
import re
from typing import Any
import httpx
from app.core import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_INDUSTRY_KEYWORDS = {
    "fintech": "FinTech",
    "insurtech": "InsurTech",
    "healthtech": "HealthTech",
    "edtech": "EdTech",
    "proptech": "PropTech",
    "legaltech": "LegalTech",
    "martech": "MarTech",
    "cybersécurité": "Cybersecurity",
    "cybersecurity": "Cybersecurity",
    "saas": "SaaS",
    "e-commerce": "E-commerce",
    "marketplace": "Marketplace",
    "logiciel": "Software",
    "software": "Software",
    "banque": "Banking",
    "banking": "Banking",
    "assurance": "Insurance",
    "insurance": "Insurance",
    "private equity": "Private Equity",
    "luxe": "Luxury",
    "luxury": "Luxury",
    "retail": "Retail",
    "immobilier": "Real Estate",
    "real estate": "Real Estate",
    "paiement": "Payments",
    "payment": "Payments",
}
_SIZE_PATTERNS = [
    (r"(\d+)\s*(?:employés|collaborateurs|employees|salariés|personnes)", "employees"),
    (r"(\d+)\s*(?:ingénieurs|engineers|développeurs|developers)", "engineers"),
    (r"(\d+[.,]?\d*)\s*(?:M€|M\u20ac|millions?)", "revenue"),
    (r"(\d+[.,]?\d*)\s*(?:Md€|Md\u20ac|milliards?|B€)", "revenue_billions"),
]
_FUNDING_PATTERNS = [
    r"[Ss]érie\s+([A-D])",
    r"[Ss]eries?\s+([A-D])",
    r"[Ss]eed",
    r"levée\s+de\s+fonds",
    r"fundrais",
]


class WebSearchService:
    """Performs targeted Google searches via Serper API to ground LLM inference."""

    SERPER_URL = "https://google.serper.dev/search"

    def __init__(self) -> None:
        self._available = settings.has_serper_key
        if self._available:
            logger.info("web_search_initialized", provider="serper")
        else:
            logger.info("web_search_disabled", reason="No SERPER_API_KEY configured")

    @property
    def is_available(self) -> bool:
        return self._available

    async def search_for_company(
        self,
        job_title: str,
        job_description: str,
        location: str | None = None,
        sector: str | None = None,
        competitor_name: str | None = None,
    ) -> dict[str, Any]:
        """Search Google for the likely company behind an anonymized job posting.
        Returns a dict with:
          - queries: list of search queries used
          - results: list of {title, snippet, link} from Google
          - context_text: formatted string ready to inject into an LLM prompt
        """
        if not self._available:
            return {"queries": [], "results": [], "context_text": ""}
        signals = self._extract_signals(job_title, job_description, location, sector)
        queries = self._build_queries(signals, job_title, location, competitor_name)
        all_results: list[dict[str, str]] = []
        for query in queries[:3]:
            try:
                results = await self._serper_search(query)
                all_results.extend(results)
            except Exception as e:
                logger.warning("web_search_failed", query=query, error=str(e))
        seen_urls: set[str] = set()
        unique_results: list[dict[str, str]] = []
        for r in all_results:
            url = r.get("link", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        context_text = self._format_context(unique_results[:8], queries)
        logger.info(
            "web_search_completed",
            queries=len(queries),
            results=len(unique_results),
        )
        return {
            "queries": queries,
            "results": unique_results[:8],
            "context_text": context_text,
        }

    def _extract_signals(
        self,
        job_title: str,
        job_description: str,
        location: str | None,
        sector: str | None,
    ) -> dict[str, Any]:
        """Extract searchable signals from the job posting."""
        desc_lower = job_description.lower()
        signals: dict[str, Any] = {
            "industries": [],
            "technologies": [],
            "company_size_hints": [],
            "funding_hints": [],
            "location": location or "",
            "sector": sector or "",
        }
        for keyword, label in _INDUSTRY_KEYWORDS.items():
            if keyword in desc_lower:
                signals["industries"].append(label)
        tech_keywords = [
            "python",
            "java",
            "react",
            "node",
            "typescript",
            "kubernetes",
            "terraform",
            "aws",
            "gcp",
            "azure",
            "spark",
            "airflow",
            "salesforce",
            "hubspot",
            "sap",
            "oracle",
        ]
        signals["technologies"] = [t for t in tech_keywords if t in desc_lower]
        for pattern, hint_type in _SIZE_PATTERNS:
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                signals["company_size_hints"].append(f"{match.group(0)}")
        for pattern in _FUNDING_PATTERNS:
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                signals["funding_hints"].append(match.group(0))
        return signals

    def _build_queries(
        self,
        signals: dict[str, Any],
        job_title: str,
        location: str | None,
        competitor_name: str | None,
    ) -> list[str]:
        """Build 2–3 targeted Google search queries from extracted signals."""
        queries: list[str] = []
        loc = location.split(",")[0].strip() if location else "France"
        industry = signals["industries"][0] if signals["industries"] else ""
        q1_parts = [job_title, industry, loc, "recrutement", "entreprise"]
        queries.append(" ".join(p for p in q1_parts if p))
        size_hints = signals["company_size_hints"][:1]
        funding_hints = signals["funding_hints"][:1]
        q2_parts = [industry] + size_hints + funding_hints + [loc, "hiring"]
        q2 = " ".join(p for p in q2_parts if p)
        if q2.strip() and q2 != queries[0]:
            queries.append(q2)
        if signals["sector"]:
            tech = " ".join(signals["technologies"][:3])
            q3 = f"{signals['sector']} {tech} {loc} company careers"
            if q3.strip() and q3 not in queries:
                queries.append(q3)
        if len(queries) < 2:
            q_fallback = f"{job_title} {loc} company hiring 2025 2026"
            queries.append(q_fallback)
        return queries[:3]

    async def _serper_search(
        self, query: str, num_results: int = 5
    ) -> list[dict[str, str]]:
        """Execute a single search via Serper API."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self.SERPER_URL,
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "q": query,
                    "gl": "fr",
                    "hl": "fr",
                    "num": num_results,
                },
            )
            response.raise_for_status()
            data = response.json()
        results: list[dict[str, str]] = []
        for item in data.get("organic", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                }
            )
        return results

    def _format_context(
        self,
        results: list[dict[str, str]],
        queries: list[str],
    ) -> str:
        """Format search results into a context block for the LLM prompt."""
        if not results:
            return ""
        lines = [
            "SUPPLEMENTARY WEB SEARCH RESULTS (Serper API — secondary source):",
            "NOTE: These are supplementary results. Use your own Google Search tool for primary verification.",
            f"Search queries used: {'; '.join(queries)}",
            "",
        ]
        for i, r in enumerate(results, 1):
            lines.append(f"  [{i}] {r['title']}")
            if r["snippet"]:
                lines.append(f"      {r['snippet']}")
            if r["link"]:
                lines.append(f"      URL: {r['link']}")
            lines.append("")
        return "\n".join(lines)
