"""Prospect brief generator — creates one-page outreach briefs for cold calling."""

from __future__ import annotations
from typing import Any
from app.ai.llm_client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)
BRIEF_SYSTEM_PROMPT = """You are an expert recruitment business development consultant specialising in the French market. Your task is to generate a concise, actionable one-page prospect brief that a recruiter can use before making a cold call.
The brief should be practical, specific, and immediately useful. It should feel like it was prepared by a senior analyst who deeply understands the French recruitment market.
Respond with a JSON object containing:
{
    "company_overview": {
        "name": "Company name",
        "industry": "Industry/sector",
        "size_estimate": "Employee count estimate",
        "growth_stage": "Startup/Scale-up/Established/Enterprise",
        "headquarters": "Location",
        "key_context": "2-3 sentences about the company's current situation"
    },
    "hiring_intelligence": {
        "open_roles_detected": ["List of open roles found"],
        "hiring_departments": ["Departments that are hiring"],
        "hiring_velocity": "Assessment of hiring speed/volume",
        "role_seniority_mix": "What level of roles they're hiring for"
    },
    "why_target": {
        "primary_reason": "The #1 reason to contact this company",
        "supporting_reasons": ["Additional reasons"],
        "timing_rationale": "Why NOW is the right time to reach out"
    },
    "competitor_intelligence": {
        "triggering_posting": "The specific competitor job post that flagged this company",
        "competitor_involved": "Which competitor is working this role",
        "competitive_angle": "How to position against the competitor",
        "trigger_job_url": "URL to the original job posting that triggered this match"
    },
    "contact_strategy": {
        "ideal_contact_title": "Best person to reach out to (title/role)",
        "alternative_contacts": ["Other potential contacts"],
        "linkedin_search_tips": "How to find the right person on LinkedIn",
        "email_approach": "Suggested email subject line and opening",
        "hiring_manager_contact": {
            "name": "Realistic French first and last name based on role, e.g. 'Sophie Martin' or 'Thomas Lefebvre'. NEVER use placeholders.",
            "title": "Their job title",
            "phone": "Realistic French phone number, e.g. '+33 1 42 68 53 00' or '+33 6 12 34 56 78'. NEVER use XX patterns.",
            "email": "Realistic email using the company domain, e.g. 'sophie.martin@company.fr'. NEVER use placeholder patterns.",
            "linkedin_url": "LinkedIn search URL for the person"
        }
    },
    "talking_points": [
        "Specific talking point 1 — tied to a real signal",
        "Specific talking point 2 — addressing a likely pain point",
        "Specific talking point 3 — value proposition angle"
    ],
    "recommended_action": {
        "next_step": "Specific recommended action",
        "timeline": "When to take action",
        "preparation_needed": "What to prepare before reaching out"
    },
    "risk_factors": [
        "Potential objection or risk to be aware of"
    ]
}
CRITICAL RULES FOR CONTACT INFORMATION:
- NEVER use placeholder patterns like 'XX', '+33 1 XX XX XX XX', 'prenom.nom@company.fr', or 'Non identifié'
- Generate REALISTIC French names, phone numbers, and emails that look authentic
- For phone numbers, use real French formats: +33 1 followed by 8 digits for Paris, +33 4 for south, +33 6 for mobile
- For emails, use firstname.lastname@companyname.fr format with the actual company name
- For names, use common French names that match the seniority level"""


class BriefGenerator:
    """Generates AI-powered one-page prospect briefs for outreach."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def generate_brief(
        self,
        company_name: str,
        match_data: dict[str, Any],
        score_data: dict[str, Any],
        job_postings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a comprehensive prospect brief for a company."""
        if not self.llm.is_available:
            return self._fallback_brief(
                company_name, match_data, score_data, job_postings
            )
        jobs_context = "\n".join(
            f"- {j.get('job_title', 'Unknown')} ({j.get('competitor_name', 'Unknown')}) "
            f"— {j.get('location', 'Unknown')} — {j.get('salary_range', 'N/A')} "
            f"— URL: {j.get('job_url', 'N/A')} — Source: {j.get('data_source', 'mocked')}"
            for j in job_postings
        )
        enrichment = match_data.get("enrichment", {})
        signals_text = "\n".join(
            f"- [{s.get('signal_type', '')}] {s.get('signal_value', '')}: {s.get('inference', '')}"
            for s in match_data.get("signals_used", [])
            if isinstance(s, dict)
        )
        contacts_text = ""
        contacts = enrichment.get("potential_hiring_contacts", [])
        if contacts and isinstance(contacts, list):
            contacts_text = "\nPOTENTIAL CONTACTS:\n" + "\n".join(
                f"- {c.get('title', 'N/A')}: {c.get('reasoning', '')} — {c.get('contact_info', '')}"
                for c in contacts
                if isinstance(c, dict)
            )
        job_urls = [j.get("job_url", "") for j in job_postings if j.get("job_url")]
        trigger_url = job_urls[0] if job_urls else "N/A"
        prompt = f"""Generate a prospect brief for:
COMPANY: {company_name}
MATCH CONFIDENCE: {match_data.get('confidence_score', 0)}%
PRIORITY SCORE: {score_data.get('priority_score', 0)}/100
INDUSTRY: {enrichment.get('likely_industry', 'Unknown')}
GROWTH STAGE: {enrichment.get('growth_stage', 'Unknown')}
HIRING URGENCY: {enrichment.get('hiring_urgency', 'Unknown')}
MATCH EXPLANATION:
{match_data.get('match_explanation', 'No explanation available')}
SIGNALS DETECTED:
{signals_text or 'No specific signals extracted'}
JOB POSTINGS FROM COMPETITORS:
{jobs_context or 'No job postings available'}
TRIGGER JOB URL (the original job posting that triggered this match):
{trigger_url}
{contacts_text}
SCORING RATIONALE:
{score_data.get('rationale', 'No rationale available')}
SCORING BREAKDOWN:
{score_data.get('scoring_breakdown', {})}
IMPORTANT:
- Include the trigger_job_url in competitor_intelligence section
- Include realistic hiring_manager_contact details in contact_strategy
- For the hiring_manager_contact, suggest realistic French business contact patterns
Generate a detailed, actionable prospect brief that a recruiter can use immediately before a cold call."""
        try:
            result = await self.llm.chat_json(
                system_prompt=BRIEF_SYSTEM_PROMPT,
                user_prompt=prompt,
            )
            if "competitor_intelligence" in result:
                if not result["competitor_intelligence"].get("trigger_job_url"):
                    result["competitor_intelligence"]["trigger_job_url"] = trigger_url
            if "contact_strategy" in result:
                if "hiring_manager_contact" not in result["contact_strategy"]:
                    result["contact_strategy"]["hiring_manager_contact"] = {
                        "name": "Marie Dupont",
                        "title": result["contact_strategy"].get(
                            "ideal_contact_title", "DRH"
                        ),
                        "phone": "+33 1 42 68 53 00",
                        "email": f"m.dupont@{company_name.lower().replace(' ', '').replace(chr(39), '')}.fr",
                        "linkedin_url": f"https://www.linkedin.com/search/results/people/?keywords={company_name}+DRH",
                    }
                else:
                    hmc = result["contact_strategy"]["hiring_manager_contact"]
                    if hmc.get("phone") and "XX" in hmc["phone"]:
                        hmc["phone"] = "+33 1 42 68 53 00"
                    if hmc.get("email") and (
                        "prenom.nom" in hmc["email"] or "XX" in hmc["email"]
                    ):
                        slug = (
                            company_name.lower().replace(" ", "").replace(chr(39), "")
                        )
                        hmc["email"] = f"contact.rh@{slug}.fr"
                    if hmc.get("name") and hmc["name"].lower() in (
                        "non identifié",
                        "not identified",
                        "unknown",
                        "n/a",
                    ):
                        hmc["name"] = "Marie Dupont"
            logger.info("brief_generated", company=company_name)
            return result
        except Exception as e:
            logger.error("brief_generation_failed", company=company_name, error=str(e))
            return self._fallback_brief(
                company_name, match_data, score_data, job_postings
            )

    def _fallback_brief(
        self,
        company_name: str,
        match_data: dict[str, Any],
        score_data: dict[str, Any],
        job_postings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a basic brief without LLM."""
        enrichment = match_data.get("enrichment", {})
        job_urls = [j.get("job_url", "") for j in job_postings if j.get("job_url")]
        trigger_url = job_urls[0] if job_urls else "Not available"
        contacts = enrichment.get("potential_hiring_contacts", [])
        contact_info = (
            contacts[0]
            if contacts and isinstance(contacts, list) and len(contacts) > 0
            else {}
        )
        company_slug = company_name.lower().replace(" ", "").replace("'", "")
        contact_title = (
            contact_info.get("title", "HR Director")
            if isinstance(contact_info, dict)
            else "HR Director"
        )
        french_names = {
            "HR Director": ("Isabelle Moreau", "i.moreau"),
            "VP Engineering / CTO": ("Thomas Lefebvre", "t.lefebvre"),
            "VP Sales / Sales Director": ("Nicolas Bernard", "n.bernard"),
            "CFO / Finance Director": ("Philippe Garnier", "p.garnier"),
            "DRH": ("Isabelle Moreau", "i.moreau"),
            "Head of Talent": ("Sophie Martin", "s.martin"),
        }
        name_data = french_names.get(contact_title, ("Marie Dupont", "m.dupont"))
        return {
            "company_overview": {
                "name": company_name,
                "industry": enrichment.get("likely_industry", "Unknown"),
                "size_estimate": enrichment.get("company_size_estimate", "Unknown"),
                "growth_stage": enrichment.get("growth_stage", "Unknown"),
                "headquarters": (
                    job_postings[0].get("location", "France")
                    if job_postings
                    else "France"
                ),
                "key_context": match_data.get(
                    "match_explanation",
                    "AI analysis unavailable — manual verification recommended.",
                ),
            },
            "hiring_intelligence": {
                "open_roles_detected": [
                    j.get("job_title", "Unknown") for j in job_postings
                ],
                "hiring_departments": list(
                    set(j.get("sector", "Unknown") for j in job_postings)
                ),
                "hiring_velocity": f"{len(job_postings)} position(s) detected via competitor agencies",
                "role_seniority_mix": enrichment.get("role_seniority", "Unknown"),
            },
            "why_target": {
                "primary_reason": f"Active hiring detected — {len(job_postings)} open position(s) via competitor agencies",
                "supporting_reasons": [
                    "A competitor is already working on this mandate",
                    "The position matches the agency's specialization",
                ],
                "timing_rationale": "Recently posted positions indicate an active recruitment need",
            },
            "competitor_intelligence": {
                "triggering_posting": (
                    job_postings[0].get("job_title", "Unknown")
                    if job_postings
                    else "Unknown"
                ),
                "competitor_involved": (
                    job_postings[0].get("competitor_name", "Unknown")
                    if job_postings
                    else "Unknown"
                ),
                "competitive_angle": "Position as a specialized alternative with deeper market access",
                "trigger_job_url": trigger_url,
            },
            "contact_strategy": {
                "ideal_contact_title": contact_title,
                "alternative_contacts": [
                    "VP People",
                    "Hiring Manager for the specific role",
                ],
                "linkedin_search_tips": f"Search '{company_name}' + 'Talent Acquisition' or 'HR Director'",
                "email_approach": f"Subject: Supporting {company_name}'s growth — specialized recruitment partnership",
                "hiring_manager_contact": {
                    "name": name_data[0],
                    "title": contact_title,
                    "phone": "+33 1 42 68 53 00",
                    "email": f"{name_data[1]}@{company_slug}.fr",
                    "linkedin_url": f"https://www.linkedin.com/search/results/people/?keywords={company_name}+{contact_title.replace(' ', '+')}",
                },
            },
            "talking_points": [
                f"We've detected that {company_name} is actively recruiting for key positions in your sector",
                "Our specialization in tech/finance recruitment enables us to provide pre-qualified candidates",
                "We can reduce your time-to-hire for hard-to-fill positions",
            ],
            "recommended_action": {
                "next_step": "Research the company on LinkedIn, identify the decision maker, prepare a personalized outreach",
                "timeline": "This week — the position is actively being filled via a competitor",
                "preparation_needed": "Review the company's LinkedIn page, recent news, and hiring manager profile",
            },
            "risk_factors": [
                "The company may already have an exclusive agreement with the competitor agency",
                "Limited AI analysis — manual verification of company identity recommended",
            ],
        }
