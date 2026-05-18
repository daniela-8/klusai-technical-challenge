import asyncio
import os
from app.ai.llm_client import LLMClient
import json


async def test_llm():
    llm = LLMClient()
    system_prompt = """You must respond with a JSON object containing EXACTLY this structure:
{
    "company_name": "Most likely company name",
    "confidence_score": 0-100,
    "match_explanation": "1 short sentence explaining why",
    "signals_used": [
        {
            "signal_type": "industry or location or tech",
            "signal_value": "specific detail",
            "inference": "1 short sentence"
        }
    ],
    "alternative_matches": [],
    "enrichment": {
        "likely_industry": "Inferred industry",
        "company_size_estimate": "Small/Medium/Large/Enterprise",
        "growth_stage": "Startup/Scale-up/Established",
        "role_seniority": "Junior/Mid/Senior/Executive",
        "technologies_mentioned": ["list", "of", "tech"],
        "company_context": "1 short sentence about company context"
    }
}"""
    user_prompt = "Job description: We are a fast-growing French HR Tech SaaS company in Paris. We are backed by top-tier VCs and just raised Series B. Tech stack: Python, GCP, React."
    try:
        print("Calling LLM...")
        text = await llm.chat(
            system_prompt, user_prompt, response_format={"type": "json_object"}
        )
        print("--- RAW TEXT RETURNED ---")
        print(text)
        print("-------------------------")
        print(f"Length: {len(text)}")
        json.loads(text)
        print("JSON parses successfully!")
    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(test_llm())
