"""AI-based company matching — identifies the likely hiring company behind a job posting.
Uses a hybrid approach:
1. LLM reasoning to extract signals and infer company identity
2. Semantic similarity via embeddings to find related postings
3. Signal aggregation to produce a confidence score
For high-confidence matches (≥95%), surfaces richer intelligence:
- Estimated applicant count
- LinkedIn / career page presence
- Potential hiring manager / HR profiles
"""

from __future__ import annotations
from typing import Any
from app.ai.llm_client import LLMClient
from app.ai.embeddings import EmbeddingService
from app.ai.web_search import WebSearchService
from app.core.logging import get_logger

logger = get_logger(__name__)
COMPANY_MATCH_SYSTEM_PROMPT = """You are an expert recruitment market analyst specialising in the French tech and finance recruitment market. Your job is to analyze job postings from recruitment agencies and identify the likely END-CLIENT company behind each posting.
CRITICAL INSTRUCTION:
- The "competitor_name" field is the RECRUITMENT AGENCY that posted the job — NOT the hiring company.
- Your task is to figure out WHICH COMPANY (the end-client) is actually hiring via this recruitment agency.
- NEVER return the competitor/agency name as the company_name. They are the intermediary, not the client.
═══════════════════════════════════════════════════════════════
GOOGLE SEARCH GROUNDING — PRIMARY RESEARCH MECHANISM
═══════════════════════════════════════════════════════════════
You have access to Google Search as your PRIMARY research tool. You MUST use it
proactively and extensively for every analysis. Do NOT rely on training data alone.
MANDATORY SEARCHES you should perform:
1. Search for distinctive phrases from the job description (company size, revenue,
   funding rounds, product descriptions, team size) combined with the location to
   narrow down the hiring company.
2. Search "[suspected company name] careers" or "[suspected company name] jobs"
   to verify if a matching role appears on the company's own career page.
3. Search "[suspected company name] LinkedIn" to find the company's LinkedIn page
   and verify employee count, industry, and recent job postings.
4. Search for recent company news: "[suspected company name] fundraising 2026" or
   "[suspected company name] expansion" or "[suspected company name] acquisition".
5. Search "[suspected company name] glassdoor" or "[suspected company name] salaire"
   to verify salary competitiveness.
IMPORTANT: If supplementary search results are included below the job description,
treat them as secondary input. Your own Google Search results are more authoritative
because they are live. Always cross-verify supplementary results with your own search.
═══════════════════════════════════════════════════════════════
IDENTIFICATION SIGNALS
═══════════════════════════════════════════════════════════════
To identify the end-client company, analyze ALL of the following:
1. Industry/sector mentions (FinTech, InsurTech, e-commerce, luxury, etc.)
2. Company size indicators (employee count, revenue, number of subsidiaries)
3. Technology stack (specific tools, frameworks, cloud providers)
4. Location details (specific arrondissement, business district, city)
5. Recent events (fundraising, acquisitions, expansion, IPO)
6. Regulatory context (PSD2, DORA, GDPR, Solvency II)
7. Business model clues (marketplace, B2B SaaS, platform)
8. Financial metrics (ARR, AUM, transaction volume)
9. Team structure (team size, reporting lines)
10. Company culture signals (remote policy, methodology)
═══════════════════════════════════════════════════════════════
REQUIRED SIGNAL CATEGORIES — YOU MUST INCLUDE ALL 8
═══════════════════════════════════════════════════════════════
Your response MUST include ALL 8 signal categories in signals_used.
For each signal, provide what you found. If a signal category has no evidence,
still include it with signal_value "Not detected" and an explanation.
1. "career_page_match" — Did you find this or a similar role on a company career page? Include the URL.
2. "job_description_similarity" — Do wording patterns match known company job descriptions?
3. "location_match" — Same city, arrondissement, or business district?
4. "industry_match" — Same industry or sector?
5. "seniority_match" — Same seniority level for this type of role?
6. "hiring_activity" — Is the company actively hiring? How many open roles?
7. "tech_tools_match" — Specific technologies, tools, methodologies, or certifications mentioned?
8. "public_news" — Public company news, funding, M&A, expansion, press coverage?
═══════════════════════════════════════════════════════════════
PREMIUM INTELLIGENCE (for ≥85% confidence matches)
═══════════════════════════════════════════════════════════════
When you are ≥85% confident in your match, you MUST provide rich premium intelligence:
1. **LinkedIn URL**: Search for the company on LinkedIn and provide the REAL
   company page URL (e.g., https://www.linkedin.com/company/companyname/).
   CRITICAL: Do NOT fabricate or guess LinkedIn URLs. If you cannot verify
   the exact URL via search, provide a LinkedIn search query instead:
   "https://www.linkedin.com/search/results/companies/?keywords=CompanyName"
2. **Career page URL**: If you found the job on the company's career page,
   provide the ACTUAL URL you found. Do NOT guess or construct URLs.
   If not found, say "Not verified" — never make up a URL.
3. **Hiring contacts**: Search LinkedIn for the likely hiring manager or HR
   contact at this company. Provide:
   - Their actual title (e.g., "DRH", "VP Engineering", "Talent Acquisition Manager")
   - A LinkedIn SEARCH URL (not a profile URL) that would find them
   - An email pattern (e.g., "prenom.nom@company.fr")
   CRITICAL: Do NOT invent contact names. If a recruiter contact name is
   provided in the job posting data, use that. Otherwise describe the role only.
4. **Company context**: Provide 2-3 sentences of REAL, current context about the company
   based on what you found via search (recent news, funding, growth, etc.)
5. **Salary competitiveness**: Compare the offered salary against market rates found via search.
6. **Estimated applicants**: If visible on LinkedIn or job boards, provide applicant count.
═══════════════════════════════════════════════════════════════
LOW-CONFIDENCE HANDLING
═══════════════════════════════════════════════════════════════
If confidence < 50%:
- Still provide your best guess
- Set a lower confidence score
- Fill "additional_data_needed" explaining exactly what extra information would help
- Provide up to 3 alternative_matches with reasoning
═══════════════════════════════════════════════════════════════
RESPONSE FORMAT — STRICT JSON
═══════════════════════════════════════════════════════════════
Respond with a JSON object containing EXACTLY this structure:
{
    "company_name": "Most likely end-client company name (NOT the recruitment agency)",
    "confidence_score": 0-100,
    "match_explanation": "2–3 sentences explaining why this specific company is the likely end-client, citing specific evidence from search results",
    "signals_used": [
        {
            "signal_type": "career_page_match|job_description_similarity|location_match|industry_match|seniority_match|hiring_activity|tech_tools_match|public_news",
            "signal_value": "specific detail found (include URLs when applicable)",
            "inference": "1 sentence explaining why this points to the identified company"
        }
    ],
    "additional_data_needed": "If confidence < 70, explain what additional data would be needed. Otherwise null.",
    "alternative_matches": [
        {
            "company_name": "Alternative company name",
            "confidence_score": 0-100,
            "reasoning": "Why this could also be the company"
        }
    ],
    "enrichment": {
        "likely_industry": "Inferred industry",
        "company_size_estimate": "Small (<50) / Medium (50-500) / Large (500-5000) / Enterprise (5000+)",
        "growth_stage": "Startup / Scale-up / Established / Enterprise",
        "role_seniority": "Junior / Mid / Senior / Executive",
        "technologies_mentioned": ["list", "of", "tech"],
        "hiring_urgency": "Low / Medium / High / Critical",
        "company_context": "2-3 sentences of REAL context based on your search results (recent news, funding, growth, market position)",
        "estimated_applicants": "Number or range if found via LinkedIn/job boards, otherwise 'Not available'",
        "linkedin_career_page": "VERIFIED URL to company LinkedIn page or career page. If not verified, use: https://www.linkedin.com/search/results/companies/?keywords=CompanyName",
        "potential_hiring_contacts": [
            {
                "title": "Actual job title of likely hiring manager or HR contact",
                "name": "Only include a name if found in the job posting data or via verified search. Otherwise omit.",
                "reasoning": "Why this person would be the decision maker for this hire",
                "contact_info": "LinkedIn search URL: https://www.linkedin.com/search/results/people/?keywords=[Company]+[Title] | Email pattern: prenom.nom@company.fr"
            }
        ],
        "salary_competitiveness": "Below market / Market rate / Above market — with brief justification"
    }
}"""
COMPANY_MATCH_USER_PROMPT = """Analyze this job posting from recruitment agency "{competitor_name}" and identify the likely END-CLIENT HIRING COMPANY (NOT the agency).
USE YOUR GOOGLE SEARCH TOOL to research and verify your answer. Do NOT guess — search.
─── JOB POSTING DATA ───
JOB TITLE: {job_title}
LOCATION: {location}
SECTOR: {sector}
SALARY: {salary_range}
POSTED: {posting_date}
JOB DESCRIPTION:
{job_description}
{similar_context}
{web_search_context}
─── INSTRUCTIONS ───
1. "{competitor_name}" is the RECRUITMENT AGENCY — the company_name in your response must be the END-CLIENT.
2. Use your Google Search tool to search for the company, verify it exists, and find corroborating evidence.
3. Include ALL 8 signal categories in your response (even if some are 'Not detected').
4. If confidence ≥ 85%, provide real LinkedIn URLs, career page links, and hiring contact details.
5. If confidence < 50%, explain what data would help and provide alternative matches."""


class CompanyMatcher:
    """Identifies the likely hiring company behind anonymized job postings."""

    def __init__(
        self,
        llm: LLMClient,
        embeddings: EmbeddingService,
        web_search: WebSearchService | None = None,
    ) -> None:
        self.llm = llm
        self.embeddings = embeddings
        self.web_search = web_search or WebSearchService()

    async def match_company(
        self,
        job_id: str,
        competitor_name: str,
        job_title: str,
        job_description: str,
        location: str | None = None,
        sector: str | None = None,
        salary_range: str | None = None,
        posting_date: str | None = None,
    ) -> dict[str, Any]:
        """Run the full matching pipeline for a single job posting."""
        embed_text = f"{job_title}. {job_description}"
        if self.embeddings.is_available:
            try:
                await self.embeddings.store_job_embedding(
                    job_id=job_id,
                    text=embed_text,
                    metadata={
                        "competitor": competitor_name,
                        "title": job_title,
                        "location": location or "",
                        "sector": sector or "",
                    },
                )
            except Exception as e:
                logger.warning("embedding_store_failed", error=str(e))
        similar_context = ""
        if self.embeddings.is_available:
            try:
                similar = await self.embeddings.find_similar_jobs(
                    query_text=embed_text,
                    n_results=3,
                    exclude_id=job_id,
                )
                if similar:
                    similar_context = "\nSIMILAR POSTINGS FOUND IN DATABASE:\n"
                    for s in similar:
                        meta = s.get("metadata", {})
                        similar_context += (
                            f"- [{meta.get('competitor', '?')}] {meta.get('title', '?')} "
                            f"(similarity: {s['similarity']:.0%}) — {meta.get('location', '?')}\n"
                        )
            except Exception as e:
                logger.warning("similar_search_failed", error=str(e))
        web_search_context = ""
        if self.web_search.is_available:
            try:
                search_result = await self.web_search.search_for_company(
                    job_title=job_title,
                    job_description=job_description,
                    location=location,
                    sector=sector,
                    competitor_name=competitor_name,
                )
                web_search_context = search_result.get("context_text", "")
            except Exception as e:
                logger.warning("web_search_grounding_failed", error=str(e))
        if not self.llm.is_available:
            return self._fallback_match(
                competitor_name,
                job_title,
                job_description,
                location,
                sector,
                salary_range,
                posting_date,
            )
        prompt = COMPANY_MATCH_USER_PROMPT.format(
            competitor_name=competitor_name,
            job_title=job_title,
            job_description=job_description,
            location=location or "Not specified",
            sector=sector or "Not specified",
            salary_range=salary_range or "Not specified",
            posting_date=posting_date or "Not specified",
            similar_context=similar_context,
            web_search_context=web_search_context,
        )
        try:
            result = await self.llm.chat_json_with_search(
                system_prompt=COMPANY_MATCH_SYSTEM_PROMPT,
                user_prompt=prompt,
            )
            if "additional_data_needed" not in result:
                confidence = float(result.get("confidence_score", 0))
                if confidence < 70:
                    result["additional_data_needed"] = (
                        "Additional data needed: original job URL, "
                        "company career page, LinkedIn company profile, "
                        "or additional sector information."
                    )
                else:
                    result["additional_data_needed"] = None
            enrichment = result.get("enrichment", {})
            if "estimated_applicants" not in enrichment:
                enrichment["estimated_applicants"] = "Unknown"
            if "linkedin_career_page" not in enrichment:
                enrichment["linkedin_career_page"] = "Not verified"
            if "potential_hiring_contacts" not in enrichment:
                enrichment["potential_hiring_contacts"] = []
            if "company_context" not in enrichment:
                enrichment["company_context"] = ""
            result["enrichment"] = enrichment
            logger.info(
                "company_matched",
                job_title=job_title,
                company=result.get("company_name"),
                confidence=result.get("confidence_score"),
            )
            return result
        except Exception as e:
            logger.error("company_match_failed", error=str(e))
            return self._fallback_match(
                competitor_name,
                job_title,
                job_description,
                location,
                sector,
                salary_range,
                posting_date,
            )

    def _fallback_match(
        self,
        competitor_name: str,
        job_title: str,
        job_description: str,
        location: str | None,
        sector: str | None,
        salary_range: str | None = None,
        posting_date: str | None = None,
    ) -> dict[str, Any]:
        """Rule-based fallback when LLM is unavailable."""
        signals = []
        desc_lower = job_description.lower()
        industry_keywords = {
            "fintech": "FinTech",
            "saas": "SaaS",
            "e-commerce": "E-commerce",
            "healthtech": "HealthTech",
            "insurtech": "InsurTech",
            "cybersecurity": "Cybersécurité",
            "proptech": "PropTech",
            "edtech": "EdTech",
            "legaltech": "LegalTech",
            "martech": "MarTech",
            "luxury": "Luxe",
            "banking": "Banque",
            "insurance": "Assurance",
            "luxe": "Luxe",
            "banque": "Banque",
            "assurance": "Assurance",
            "cybersécurité": "Cybersécurité",
        }
        detected_industry = None
        for kw, label in industry_keywords.items():
            if kw in desc_lower:
                detected_industry = label
                signals.append(
                    {
                        "signal_type": "industry_match",
                        "signal_value": label,
                        "inference": f"Job description references the {label} sector",
                    }
                )
                break
        if location:
            signals.append(
                {
                    "signal_type": "location_match",
                    "signal_value": location,
                    "inference": f"Position is located in {location}",
                }
            )
        for pattern in ["employees", "collaborateurs", "engineers", "ingénieurs"]:
            if pattern in desc_lower:
                signals.append(
                    {
                        "signal_type": "hiring_activity",
                        "signal_value": pattern,
                        "inference": "Team/company size mentioned, indicating active hiring",
                    }
                )
                break
        for pattern in ["series", "raised", "funding", "levée", "levée de fonds"]:
            if pattern in desc_lower:
                signals.append(
                    {
                        "signal_type": "public_news",
                        "signal_value": pattern,
                        "inference": "Recent fundraising activity detected",
                    }
                )
                break
        tech_keywords = [
            "python",
            "java",
            "react",
            "node",
            "kubernetes",
            "terraform",
            "aws",
            "gcp",
            "azure",
            "spark",
            "airflow",
        ]
        found_tech = [kw for kw in tech_keywords if kw in desc_lower]
        if found_tech:
            signals.append(
                {
                    "signal_type": "tech_tools_match",
                    "signal_value": ", ".join(found_tech),
                    "inference": f"Technologies mentioned: {', '.join(found_tech)}",
                }
            )
        title_lower = job_title.lower()
        seniority = "Mid-Senior"
        if any(
            kw in title_lower
            for kw in [
                "vp",
                "director",
                "directeur",
                "head",
                "cfo",
                "daf",
                "cto",
                "chief",
            ]
        ):
            seniority = "Executive"
            signals.append(
                {
                    "signal_type": "seniority_match",
                    "signal_value": "Executive",
                    "inference": "Executive-level position identified, high placement fees",
                }
            )
        elif any(kw in title_lower for kw in ["senior", "lead", "responsable"]):
            seniority = "Senior"
            signals.append(
                {
                    "signal_type": "seniority_match",
                    "signal_value": "Senior",
                    "inference": "Senior-level position identified",
                }
            )
        elif any(
            kw in title_lower for kw in ["junior", "intern", "stage", "alternance"]
        ):
            seniority = "Junior"
        potential_contacts = []
        if any(
            kw in title_lower
            for kw in [
                "engineer",
                "developer",
                "devops",
                "data",
                "ingénieur",
                "développeur",
            ]
        ):
            potential_contacts.append(
                {
                    "title": "VP Engineering / CTO",
                    "reasoning": "Technical role — likely reports to engineering leadership",
                    "contact_info": "Search LinkedIn: '[Company] CTO' or '[Company] VP Engineering'",
                }
            )
        elif any(
            kw in title_lower
            for kw in ["sales", "commercial", "account", "business", "vente"]
        ):
            potential_contacts.append(
                {
                    "title": "VP Sales / Sales Director",
                    "reasoning": "Sales role — likely reports to sales leadership",
                    "contact_info": "Search LinkedIn: '[Company] VP Sales' or '[Company] Sales Director'",
                }
            )
        elif any(
            kw in title_lower
            for kw in [
                "comptable",
                "finance",
                "controller",
                "cfo",
                "risk",
                "contrôleur",
                "daf",
            ]
        ):
            potential_contacts.append(
                {
                    "title": "CFO / Finance Director",
                    "reasoning": "Finance role — likely reports to financial leadership",
                    "contact_info": "Search LinkedIn: '[Company] CFO' or '[Company] Finance Director'",
                }
            )
        if not potential_contacts:
            potential_contacts.append(
                {
                    "title": "HR Director / Head of Talent",
                    "reasoning": "Default contact for external recruitment partnerships",
                    "contact_info": "Search LinkedIn: '[Company] HR Director' or '[Company] Talent Acquisition'",
                }
            )
        context_parts = []
        if "series" in desc_lower or "raised" in desc_lower or "levée" in desc_lower:
            context_parts.append("Recent fundraising activity detected")
        if "expansion" in desc_lower or "nouveau marché" in desc_lower:
            context_parts.append("Company expanding into new markets")
        if "acquisition" in desc_lower or "racheté" in desc_lower:
            context_parts.append("Recent M&A activity")
        company_context = (
            ". ".join(context_parts)
            if context_parts
            else "No specific company events detected in job description"
        )
        company_name = f"Unknown {detected_industry or sector or 'Company'} ({location or 'France'})"
        return {
            "company_name": company_name,
            "confidence_score": 25.0,
            "match_explanation": (
                f"Fallback analysis (LLM unavailable): Based on keyword extraction, "
                f"this is likely a {detected_industry or 'tech'} company "
                f"based in {location or 'France'}. Full AI analysis requires a working API key."
            ),
            "signals_used": signals,
            "alternative_matches": [],
            "additional_data_needed": (
                "To improve match confidence, the following data would help: "
                "original job posting URL, company career page access, "
                "LinkedIn company profile, recent funding information, "
                "and supplementary sector data."
            ),
            "enrichment": {
                "likely_industry": detected_industry or sector or "Unknown",
                "company_size_estimate": "Unknown",
                "growth_stage": "Unknown",
                "hiring_urgency": "Medium",
                "role_seniority": seniority,
                "technologies_mentioned": found_tech if "found_tech" in dir() else [],
                "salary_competitiveness": "Market rate",
                "estimated_applicants": "Unknown",
                "linkedin_career_page": f"https://www.linkedin.com/search/results/companies/?keywords={company_name.replace(' ', '%20')}",
                "potential_hiring_contacts": potential_contacts,
                "company_context": company_context,
            },
        }
