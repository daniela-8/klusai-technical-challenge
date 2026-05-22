"""Tests for the AI pipeline — company matching, scoring, and brief generation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.ai.company_matcher import CompanyMatcher
from app.ai.priority_scorer import PriorityScorer
from app.ai.brief_generator import BriefGenerator
from app.ai.llm_client import LLMClient
from app.ai.embeddings import EmbeddingService


class TestCompanyMatcherFallback:
    """Test the rule-based fallback matching (no LLM required)."""

    def setup_method(self):
        self.llm = LLMClient()
        self.embeddings = MagicMock(spec=EmbeddingService)
        self.embeddings.is_available = False
        self.matcher = CompanyMatcher(self.llm, self.embeddings)

    @pytest.mark.asyncio
    async def test_fallback_detects_fintech_industry(self):
        result = await self.matcher.match_company(
            job_id="test-1",
            competitor_name="Michael Page",
            job_title="VP of Engineering",
            job_description="A leading European FinTech platform processing €2B+ annually.",
            location="Paris, France",
        )
        assert result["company_name"]
        assert result["confidence_score"] == 25.0
        signals = result["signals_used"]
        assert any(
            s.get("signal_type") == "industry" for s in signals if isinstance(s, dict)
        )

    @pytest.mark.asyncio
    async def test_fallback_detects_saas_industry(self):
        result = await self.matcher.match_company(
            job_id="test-2",
            competitor_name="Hays",
            job_title="Account Executive",
            job_description="Join a fast-growing SaaS company specializing in HR technology.",
            location="Lyon, France",
        )
        assert "SaaS" in result["company_name"] or "SaaS" in str(
            result.get("enrichment", {})
        )
        assert result["confidence_score"] == 25.0

    @pytest.mark.asyncio
    async def test_fallback_detects_fundraising_signal(self):
        result = await self.matcher.match_company(
            job_id="test-3",
            competitor_name="Uptoo",
            job_title="Business Developer",
            job_description="The company recently raised a Series B of €30M.",
        )
        signals = result["signals_used"]
        assert any(
            s.get("signal_type") == "fundraising"
            for s in signals
            if isinstance(s, dict)
        )

    @pytest.mark.asyncio
    async def test_fallback_returns_complete_structure(self):
        result = await self.matcher.match_company(
            job_id="test-4",
            competitor_name="Robert Half",
            job_title="Data Analyst",
            job_description="We're hiring a data analyst for a tech startup.",
            location="Paris",
            sector="Tech",
            salary_range="€45-55K",
        )
        assert "company_name" in result
        assert "confidence_score" in result
        assert "match_explanation" in result
        assert "signals_used" in result
        assert "enrichment" in result
        assert isinstance(result["signals_used"], list)

    @pytest.mark.asyncio
    async def test_fallback_handles_empty_description(self):
        result = await self.matcher.match_company(
            job_id="test-5",
            competitor_name="Fed Finance",
            job_title="Unknown Role",
            job_description="",
        )
        assert result["company_name"]
        assert result["confidence_score"] == 25.0


class TestPriorityScorer:
    """Test the multi-signal priority scoring logic."""

    def setup_method(self):
        self.llm = LLMClient()
        self.scorer = PriorityScorer(self.llm)

    @pytest.mark.asyncio
    async def test_score_basic_calculation(self):
        result = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={
                "enrichment": {
                    "likely_industry": "SaaS",
                    "role_seniority": "Senior",
                    "hiring_urgency": "High",
                    "growth_stage": "Scale-up",
                },
                "signals_used": [
                    {"signal_type": "funding", "signal_value": "Series B"}
                ],
            },
            job_count=3,
            job_titles=["VP Sales", "Account Executive"],
            days_since_posted=2,
        )
        assert "priority_score" in result
        assert 0 <= result["priority_score"] <= 100
        assert "scoring_breakdown" in result
        assert "rationale" in result

    @pytest.mark.asyncio
    async def test_score_increases_with_seniority(self):
        junior_result = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={"enrichment": {"role_seniority": "Junior"}, "signals_used": []},
            job_count=1,
        )
        exec_result = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={
                "enrichment": {"role_seniority": "C-level"},
                "signals_used": [],
            },
            job_count=1,
        )
        assert exec_result["priority_score"] > junior_result["priority_score"]

    @pytest.mark.asyncio
    async def test_score_increases_with_job_count(self):
        one_job = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={"enrichment": {}, "signals_used": []},
            job_count=1,
        )
        many_jobs = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={"enrichment": {}, "signals_used": []},
            job_count=5,
        )
        assert many_jobs["priority_score"] > one_job["priority_score"]

    @pytest.mark.asyncio
    async def test_score_recency_effect(self):
        recent = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={"enrichment": {}, "signals_used": []},
            job_count=1,
            days_since_posted=1,
        )
        old = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={"enrichment": {}, "signals_used": []},
            job_count=1,
            days_since_posted=30,
        )
        assert recent["priority_score"] > old["priority_score"]

    @pytest.mark.asyncio
    async def test_scoring_breakdown_has_all_weights(self):
        result = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={"enrichment": {}, "signals_used": []},
            job_count=1,
        )
        breakdown = result["scoring_breakdown"]
        expected_keys = [
            "role_relevance",
            "hiring_volume",
            "seniority",
            "urgency",
            "recency",
            "company_growth",
            "reposting",
            "competitor_overlap",
        ]
        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_high_value_industry_scores_higher(self):
        fintech = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={
                "enrichment": {"likely_industry": "FinTech"},
                "signals_used": [],
            },
            job_count=1,
        )
        unknown = await self.scorer.calculate_score(
            company_name="TestCorp",
            match_data={
                "enrichment": {"likely_industry": "Unknown"},
                "signals_used": [],
            },
            job_count=1,
        )
        assert fintech["priority_score"] > unknown["priority_score"]


class TestBriefGeneratorFallback:
    """Test the fallback brief generation (no LLM required)."""

    def setup_method(self):
        self.llm = LLMClient()
        self.gen = BriefGenerator(self.llm)

    @pytest.mark.asyncio
    async def test_fallback_brief_structure(self):
        result = await self.gen.generate_brief(
            company_name="TestCorp",
            match_data={
                "confidence_score": 75,
                "match_explanation": "Strong match based on industry signals.",
                "signals_used": [],
                "enrichment": {"likely_industry": "SaaS", "role_seniority": "Senior"},
            },
            score_data={
                "priority_score": 82,
                "scoring_breakdown": {},
                "rationale": "High priority",
            },
            job_postings=[
                {
                    "job_title": "Account Executive",
                    "competitor_name": "Michael Page",
                    "location": "Paris",
                },
            ],
        )
        assert "company_overview" in result
        assert "hiring_intelligence" in result
        assert "why_target" in result
        assert "talking_points" in result
        assert "recommended_action" in result
        assert result["company_overview"]["name"] == "TestCorp"

    @pytest.mark.asyncio
    async def test_fallback_brief_includes_jobs(self):
        result = await self.gen.generate_brief(
            company_name="TestCorp",
            match_data={"enrichment": {}, "signals_used": []},
            score_data={"priority_score": 50, "scoring_breakdown": {}, "rationale": ""},
            job_postings=[
                {"job_title": "CTO", "competitor_name": "Hays", "location": "Lyon"},
                {
                    "job_title": "VP Engineering",
                    "competitor_name": "Hays",
                    "location": "Lyon",
                },
            ],
        )
        roles = result["hiring_intelligence"]["open_roles_detected"]
        assert "CTO" in roles
        assert "VP Engineering" in roles


class TestLLMClient:
    """Test LLM client behavior."""

    def test_unavailable_without_key(self):
        client = LLMClient()
        assert not client.is_available

    @pytest.mark.asyncio
    async def test_chat_raises_without_key(self):
        client = LLMClient()
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.chat("system", "user")
