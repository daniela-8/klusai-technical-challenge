"""Priority scoring — 10-signal weighted scoring with LLM-generated rationale.
All 10 signals required by the PoC specification:
 1. Number of open roles (hiring_volume)
 2. Role relevance for the recruitment company (role_relevance)
 3. Seniority of the role (seniority)
 4. Urgency signals in the job description (urgency)
 5. Job reposting signals (reposting)
 6. Time since the job was posted (recency)
 7. Company growth signals (company_growth)
 8. Hiring activity in the same department (dept_hiring_activity)
 9. Recent company context: funding, M&A, LBO, expansion, contracts (recent_company_context)
10. Whether a competitor is already working on the role (competitor_overlap)
"""

from __future__ import annotations
from typing import Any
from app.ai.llm_client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)
SCORING_SYSTEM_PROMPT = """You are a recruitment intelligence analyst. Your task is to generate a clear, actionable rationale for a company's priority score.
The score is calculated based on weighted signals. Given the scoring breakdown and company context, write a 2-3 sentence rationale explaining:
1. Why this company should be contacted (or not)
2. What makes it a strong/weak target for the recruitment agency
3. The most compelling signal driving the score
Respond with a JSON object:
{
    "rationale": "Your 2-3 sentence rationale here",
    "recommended_action": "Specific recommended next step",
    "urgency_level": "low/medium/high/critical",
    "best_contact_approach": "How the recruiter should approach this company"
}"""


class PriorityScorer:
    """Calculates multi-signal priority scores for matched companies.
    Scoring weights (10 signals, summing to 100%):
    - Role relevance (15%): How relevant is the role to the agency's specialization
    - Hiring volume (12%): Number of open roles detected
    - Seniority level (12%): Higher seniority = higher value placement fee
    - Urgency signals (12%): Urgency language in the job description
    - Recent company context (10%): Funding, M&A, LBO, expansion, major contracts
    - Recency (10%): More recent postings score higher
    - Dept. hiring activity (8%): Multiple roles in the same department/sector
    - Company growth (8%): Growth signals (funding round stage, expansion pace)
    - Reposting (8%): Reposted jobs indicate difficulty filling the role
    - Competitor overlap (5%): Already being worked by competitors
    """

    WEIGHTS = {
        "role_relevance": 0.15,
        "hiring_volume": 0.12,
        "seniority": 0.12,
        "urgency": 0.12,
        "recent_company_context": 0.10,
        "recency": 0.10,
        "dept_hiring_activity": 0.08,
        "company_growth": 0.08,
        "reposting": 0.08,
        "competitor_overlap": 0.05,
    }

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def calculate_score(
        self,
        company_name: str,
        match_data: dict[str, Any],
        job_count: int = 1,
        job_titles: list[str] | None = None,
        days_since_posted: int | None = None,
        job_descriptions: list[str] | None = None,
        job_sectors: list[str] | None = None,
        competitor_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Calculate priority score for a matched company."""
        enrichment = match_data.get("enrichment", {})
        signals = match_data.get("signals_used", [])
        description = match_data.get("match_explanation", "")
        all_descriptions = " ".join(job_descriptions or []).lower()
        raw_breakdown: dict[str, tuple[float, str]] = {}
        raw_breakdown["role_relevance"] = self._score_relevance(
            enrichment, job_titles or []
        )
        vol_score = min(100, job_count * 25)
        vol_just = (
            f"{job_count} open role(s) detected"
            if job_count >= 1
            else "No roles detected"
        )
        raw_breakdown["hiring_volume"] = (vol_score, vol_just)
        seniority = enrichment.get("role_seniority", "Mid")
        seniority_scores = {
            "Junior": 20,
            "Mid": 40,
            "Mid-Senior": 55,
            "Senior": 70,
            "Executive": 85,
            "C-level": 100,
        }
        sen_score = seniority_scores.get(seniority, 50)
        raw_breakdown["seniority"] = (
            sen_score,
            f"{seniority}-level position — {'high' if sen_score >= 70 else 'moderate'} placement value",
        )
        raw_breakdown["urgency"] = self._score_urgency(
            enrichment, description, all_descriptions
        )
        raw_breakdown["recent_company_context"] = self._score_company_context(
            enrichment, signals, all_descriptions
        )
        if days_since_posted is not None:
            rec_score = max(0, 100 - (days_since_posted * 5))
            rec_just = f"Posted {days_since_posted} day(s) ago" + (
                " — very fresh"
                if days_since_posted <= 3
                else " — aging" if days_since_posted > 10 else ""
            )
        else:
            rec_score = 60
            rec_just = "Posting date unavailable — moderate default"
        raw_breakdown["recency"] = (rec_score, rec_just)
        raw_breakdown["dept_hiring_activity"] = self._score_dept_activity(
            job_sectors or [], job_count
        )
        raw_breakdown["company_growth"] = self._score_growth(enrichment, signals)
        raw_breakdown["reposting"] = self._score_reposting(signals, all_descriptions)
        raw_breakdown["competitor_overlap"] = self._score_competitor_overlap(
            competitor_names or []
        )
        breakdown: dict[str, dict[str, Any]] = {}
        for key, (score, justification) in raw_breakdown.items():
            breakdown[key] = {"score": score, "justification": justification}
        total_score = sum(
            raw_breakdown[key][0] * weight for key, weight in self.WEIGHTS.items()
        )
        total_score = round(min(100, max(0, total_score)), 1)
        rationale_data = await self._generate_rationale(
            company_name,
            total_score,
            {k: v[0] for k, v in raw_breakdown.items()},
            enrichment,
        )
        return {
            "priority_score": total_score,
            "scoring_breakdown": breakdown,
            "rationale": rationale_data.get(
                "rationale",
                f"{company_name} scored {total_score}/100 based on multi-signal analysis.",
            ),
            "recommended_action": rationale_data.get(
                "recommended_action", "Review and assess fit"
            ),
            "urgency_level": rationale_data.get("urgency_level", "medium"),
            "best_contact_approach": rationale_data.get(
                "best_contact_approach", "Direct outreach to hiring manager"
            ),
        }

    def _score_relevance(
        self, enrichment: dict, job_titles: list[str]
    ) -> tuple[float, str]:
        """Score role relevance to a tech/finance recruitment agency."""
        score = 50.0
        reasons: list[str] = []
        industry = enrichment.get("likely_industry", "").lower()
        high_value = ["fintech", "saas", "cybersecurity", "banking", "private equity"]
        medium_value = ["healthtech", "e-commerce", "proptech", "edtech", "insurance"]
        if any(hv in industry for hv in high_value):
            score = 85
            reasons.append(
                f"High-value sector: {enrichment.get('likely_industry', '')}"
            )
        elif any(mv in industry for mv in medium_value):
            score = 70
            reasons.append(
                f"Medium-value sector: {enrichment.get('likely_industry', '')}"
            )
        else:
            reasons.append("Standard sector relevance")
        for title in job_titles:
            title_lower = title.lower()
            if any(
                kw in title_lower
                for kw in ["vp", "director", "head", "cfo", "cto", "chief"]
            ):
                score = min(100, score + 15)
                reasons.append(f"Executive-level title: {title}")
                break
            elif any(kw in title_lower for kw in ["senior", "lead", "manager"]):
                score = min(100, score + 8)
                reasons.append(f"Senior-level title: {title}")
                break
        return (score, "; ".join(reasons))

    def _score_urgency(
        self, enrichment: dict, description: str, all_descriptions: str
    ) -> tuple[float, str]:
        """Score urgency based on language and signals."""
        urgency = enrichment.get("hiring_urgency", "Medium")
        urgency_scores = {"Low": 20, "Medium": 50, "High": 75, "Critical": 95}
        base = urgency_scores.get(urgency, 50)
        reasons = [f"Hiring urgency: {urgency}"]
        combined = (description + " " + all_descriptions).lower()
        urgency_words = [
            "urgent",
            "immediately",
            "asap",
            "rapidly",
            "quickly",
            "immédiat",
            "rapidement",
            "dès que possible",
            "critical",
            "as soon as possible",
            "without delay",
            "time-sensitive",
        ]
        found = [w for w in urgency_words if w in combined]
        if found:
            base = min(100, base + 20)
            reasons.append(f"Urgency language detected: {', '.join(found[:3])}")
        return (base, "; ".join(reasons))

    def _score_company_context(
        self, enrichment: dict, signals: list, all_descriptions: str
    ) -> tuple[float, str]:
        """Score recent company context: funding, M&A, LBO, expansion, major contracts."""
        score = 30.0
        reasons: list[str] = []
        growth_stage = enrichment.get("growth_stage", "").lower()
        if growth_stage in ("startup", "scale-up"):
            score += 15
            reasons.append(f"Growth stage: {growth_stage}")
        combined = all_descriptions + " " + " ".join(str(s) for s in signals).lower()
        funding_keywords = [
            "series a",
            "series b",
            "series c",
            "series d",
            "seed round",
            "raised",
            "funding",
            "fundraise",
            "levée de fonds",
            "financement",
            "tour de table",
        ]
        funding_count = sum(1 for kw in funding_keywords if kw in combined)
        if funding_count >= 2:
            score += 25
            reasons.append("Multiple funding signals detected")
        elif funding_count == 1:
            score += 15
            reasons.append("Funding activity detected")
        ma_keywords = [
            "acquisition",
            "merger",
            "lbo",
            "leveraged buyout",
            "rachat",
            "racheté",
            "fusionner",
            "prise de participation",
            "buyout",
            "carve-out",
            "spin-off",
        ]
        if any(kw in combined for kw in ma_keywords):
            score += 20
            reasons.append("M&A / LBO activity detected")
        expansion_keywords = [
            "expansion",
            "new market",
            "international",
            "opening office",
            "nouveau marché",
            "développement international",
            "implantation",
            "scaling",
            "new country",
            "european expansion",
        ]
        if any(kw in combined for kw in expansion_keywords):
            score += 10
            reasons.append("Expansion activity detected")
        contract_keywords = [
            "major contract",
            "won contract",
            "awarded",
            "mandate",
            "contrat majeur",
            "appel d'offre",
            "marché public",
        ]
        if any(kw in combined for kw in contract_keywords):
            score += 10
            reasons.append("Major contract activity")
        if not reasons:
            reasons.append("No specific company events detected")
        return (min(100, score), "; ".join(reasons))

    def _score_dept_activity(
        self, job_sectors: list[str], job_count: int
    ) -> tuple[float, str]:
        """Score hiring activity in the same department/sector."""
        if not job_sectors or job_count <= 1:
            return (30.0, "Single role detected — low departmental signal")
        sector_counts: dict[str, int] = {}
        for sector in job_sectors:
            if sector:
                normalized = sector.lower().split("/")[0].strip()
                sector_counts[normalized] = sector_counts.get(normalized, 0) + 1
        if not sector_counts:
            return (30.0, "No sector data available")
        max_in_one_dept = max(sector_counts.values())
        top_dept = max(sector_counts, key=sector_counts.get)
        if max_in_one_dept >= 4:
            return (95.0, f"Critical: {max_in_one_dept} roles in {top_dept} dept")
        elif max_in_one_dept == 3:
            return (80.0, f"High: {max_in_one_dept} roles in {top_dept} dept")
        elif max_in_one_dept == 2:
            return (65.0, f"{max_in_one_dept} roles in {top_dept} dept")
        elif len(sector_counts) >= 3:
            return (55.0, f"Hiring across {len(sector_counts)} departments")
        else:
            return (40.0, f"Limited departmental hiring signal")

    def _score_growth(self, enrichment: dict, signals: list) -> tuple[float, str]:
        """Score company growth based on signals."""
        score = 40.0
        reasons: list[str] = []
        growth_stage = enrichment.get("growth_stage", "")
        if growth_stage in ("Startup", "Scale-up"):
            score = 75
            reasons.append(f"Growth stage: {growth_stage}")
        elif growth_stage == "Established":
            score = 55
            reasons.append("Established company")
        else:
            reasons.append("Growth stage unknown")
        signal_texts = " ".join(str(s) for s in signals).lower()
        growth_keywords = [
            "funding",
            "series",
            "raised",
            "expansion",
            "acquisition",
            "growth",
            "levée",
        ]
        found = [kw for kw in growth_keywords if kw in signal_texts]
        if found:
            score = min(100, score + 20)
            reasons.append(f"Growth keywords: {', '.join(found[:3])}")
        return (score, "; ".join(reasons))

    def _score_reposting(
        self, signals: list, all_descriptions: str
    ) -> tuple[float, str]:
        """Score reposting signals — reposted jobs indicate difficulty filling."""
        combined = all_descriptions + " " + " ".join(str(s) for s in signals).lower()
        repost_keywords = [
            "repost",
            "re-post",
            "republished",
            "relisted",
            "still looking",
            "extended deadline",
            "position still open",
            "toujours en recherche",
            "annonce prolongée",
        ]
        found = [kw for kw in repost_keywords if kw in combined]
        if found:
            return (80.0, f"Reposting signals: {', '.join(found[:2])}")
        return (30.0, "No reposting signals detected")

    def _score_competitor_overlap(
        self, competitor_names: list[str]
    ) -> tuple[float, str]:
        """Score based on how many competitors are working on this company's roles."""
        unique_competitors = len(set(competitor_names))
        if unique_competitors >= 3:
            return (90.0, f"{unique_competitors} agencies sourcing for this company")
        elif unique_competitors == 2:
            return (70.0, f"2 agencies confirmed: {', '.join(set(competitor_names))}")
        elif unique_competitors == 1:
            names = list(set(competitor_names))
            return (50.0, f"Single agency: {names[0] if names else 'unknown'}")
        else:
            return (30.0, "No competitor overlap data")

    async def _generate_rationale(
        self,
        company_name: str,
        total_score: float,
        breakdown: dict[str, float],
        enrichment: dict,
    ) -> dict[str, str]:
        """Use LLM to generate a human-readable scoring rationale."""
        if not self.llm.is_available:
            top_signal = max(breakdown, key=breakdown.get)
            return {
                "rationale": (
                    f"{company_name} received a priority score of {total_score}/100. "
                    f"The strongest signal is {top_signal.replace('_', ' ')} ({breakdown[top_signal]:.0f}/100). "
                    f"Industry: {enrichment.get('likely_industry', 'Unknown')}."
                ),
                "recommended_action": "Review company profile and assess outreach opportunity",
                "urgency_level": (
                    "high"
                    if total_score > 70
                    else "medium" if total_score > 40 else "low"
                ),
                "best_contact_approach": "Direct outreach to talent acquisition team",
            }
        prompt = (
            f"Company: {company_name}\n"
            f"Priority Score: {total_score}/100\n"
            f"Scoring Breakdown: {breakdown}\n"
            f"Industry: {enrichment.get('likely_industry', 'Unknown')}\n"
            f"Growth Stage: {enrichment.get('growth_stage', 'Unknown')}\n"
            f"Role Seniority: {enrichment.get('role_seniority', 'Unknown')}\n"
            f"Hiring Urgency: {enrichment.get('hiring_urgency', 'Unknown')}\n"
        )
        try:
            return await self.llm.chat_json(
                system_prompt=SCORING_SYSTEM_PROMPT,
                user_prompt=prompt,
                model=None,
            )
        except Exception as e:
            logger.warning("rationale_generation_failed", error=str(e))
            return {
                "rationale": f"{company_name} scored {total_score}/100 based on multi-signal analysis.",
                "recommended_action": "Review and assess fit",
                "urgency_level": "medium",
                "best_contact_approach": "Direct outreach",
            }
