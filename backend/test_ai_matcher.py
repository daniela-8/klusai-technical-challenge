import asyncio
import os
from app.ai.llm_client import LLMClient
from app.ai.embeddings import EmbeddingService
from app.ai.company_matcher import CompanyMatcher


async def test_matcher():
    print("Initializing LLM client...")
    llm = LLMClient()
    embeddings = EmbeddingService()
    matcher = CompanyMatcher(llm, embeddings)
    print(f"LLM available: {llm.is_available}")
    print(f"Model: {os.getenv('OPENAI_MODEL')}")
    job_title = "Senior Data Engineer"
    job_description = "We are a fast-growing French HR Tech SaaS company in Paris. We are backed by top-tier VCs and just raised Series B. Tech stack: Python, GCP, React."
    print("\nRunning matcher...")
    try:
        result = await matcher.match_company(
            job_id="test-job-123",
            competitor_name="Michael Page",
            job_title=job_title,
            job_description=job_description,
            location="Paris, France",
            sector="Tech",
        )
        print("\nSUCCESS! Parsed JSON Result:")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"\nFAILED: {e}")
    await llm.close()


if __name__ == "__main__":
    asyncio.run(test_matcher())
