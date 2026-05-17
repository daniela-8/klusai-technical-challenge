"""Mock data fallback for competitors that block scraping.
Used when live scraping fails (e.g., Robert Walters returns HTTP 403).
All mock jobs are tagged with data_source="mocked" for full transparency.
Only the 4 targeted competitors are included.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.scrapers.base import ScrapedJob


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def _rw_jobs() -> list[ScrapedJob]:
    return [
        ScrapedJob(
            competitor_name="Robert Walters",
            job_title="Analyste M&A — Banque d'Investissement",
            job_description=(
                "Banque d'investissement française de premier plan recrute un Analyste M&A "
                "pour des transactions mid-cap de 50 à 500M€. Modélisation financière, due diligence, "
                "pitch books, exécution de deals. 2-4 ans d'expérience en banque d'investissement, "
                "M&A de préférence, grande école de commerce, bilingue français/anglais. Paris. 80-110K€ + bonus."
            ),
            location="Paris, France",
            sector="Banque d'Investissement / M&A",
            salary_range="€80,000 – €110,000/yr + bonus",
            job_url="https://www.robertwalters.fr/en/jobs/analyst-m-and-a-investment-banking.html",
            posting_date=_days_ago(3),
            data_source="mocked",
        ),
        ScrapedJob(
            competitor_name="Robert Walters",
            job_title="VP Ventes — SaaS Entreprise",
            job_description=(
                "Entreprise SaaS en Série C (50M€ ARR, 300 employés) recrute un VP Ventes "
                "pour diriger 15 AE en France et Benelux. Construction de pipeline, coaching d'équipe, "
                "closing de deals entreprise 200K€+. 8+ ans vente SaaS, 4+ ans management, "
                "expérience CRM (Salesforce), méthodologie MEDDIC. OTE 200-250K€. Paris."
            ),
            location="Paris, France",
            sector="Technologie / Direction Commerciale",
            salary_range="€200,000 – €250,000/yr OTE",
            job_url="https://www.robertwalters.fr/en/jobs/vp-sales-enterprise-saas.html",
            posting_date=_days_ago(5),
            data_source="mocked",
        ),
        ScrapedJob(
            competitor_name="Robert Walters",
            job_title="Directeur Juridique — Fintech",
            job_description=(
                "FinTech française en pleine croissance (paiements, 400 employés) recrute son premier Directeur Juridique. "
                "Gestion contractuelle, conformité réglementaire (ACPR/AMF), protection des données, support M&A. "
                "8+ ans, inscrit au Barreau, services financiers obligatoire. Paris. 120-150K€."
            ),
            location="Paris, France",
            sector="FinTech / Juridique",
            salary_range="€120,000 – €150,000/yr",
            job_url="https://www.robertwalters.fr/en/jobs/general-counsel-fintech.html",
            posting_date=_days_ago(8),
            data_source="mocked",
        ),
    ]


def _cpa_jobs() -> list[ScrapedJob]:
    return [
        ScrapedJob(
            competitor_name="CPA Partners",
            job_title="Auditeur Senior — Cabinet Comptable",
            job_description=(
                "Cabinet d'expertise comptable et d'audit (80 collaborateurs, réseau national) "
                "recrute un Auditeur Senior. Missions d'audit légal et contractuel pour PME/ETI "
                "(industrie, commerce, services). Encadrement de 2-3 assistants. "
                "DEC en cours ou validé, 4+ ans cabinet, portefeuille autonome. Paris. 45-55K€."
            ),
            location="Paris, France",
            sector="Audit / Comptabilité",
            salary_range="€45,000 – €55,000/yr",
            job_url="https://www.cpa-partners.fr/offres/",
            posting_date=_days_ago(6),
            data_source="mocked",
        ),
    ]


def _mp_jobs() -> list[ScrapedJob]:
    return [
        ScrapedJob(
            competitor_name="Michael Page",
            job_title="Directeur Commercial Senior — SaaS B2B",
            job_description=(
                "Notre client, une entreprise SaaS en forte croissance spécialisée dans la technologie RH, "
                "recherche un Directeur Commercial Senior pour diriger les ventes entreprise en France. "
                "5+ ans de vente B2B SaaS, track record prouvé de closing supérieur à 100K€ ARR. "
                "Package compétitif : fixe 65-80K€ + variable déplafonné. Paris 9ème."
            ),
            location="Paris, France",
            sector="Technologie / Ventes SaaS",
            salary_range="€65,000 – €80,000/yr + variable",
            job_url="https://www.michaelpage.fr/jobs/technology",
            posting_date=_days_ago(3),
            data_source="mocked",
        ),
    ]


def _rh_jobs() -> list[ScrapedJob]:
    return [
        ScrapedJob(
            competitor_name="Robert Half",
            job_title="Directeur Administratif et Financier — Scale-up SaaS",
            job_description=(
                "Entreprise SaaS B2B en forte croissance (30M€ ARR, 200 employés) recherche son premier DAF. "
                "Construire l'équipe finance, préparer la Série C, mettre en place le FP&A. "
                "12+ ans d'expérience, ancien DAF/VP Finance en tech. Paris. 160-200K€ + equity."
            ),
            location="Paris, France",
            sector="SaaS / Direction Financière",
            salary_range="€160,000 – €200,000/yr + equity",
            job_url="https://www.roberthalf.com/fr/fr/offres-emploi",
            posting_date=_days_ago(2),
            data_source="mocked",
        ),
    ]


def get_mock_jobs() -> dict[str, list[ScrapedJob]]:
    """Return competitor name → list of mock jobs (only for the 4 targets).
    Each job gets a unique URL fragment to avoid dedup collisions.
    """
    all_jobs = {
        "CPA Partners": _cpa_jobs(),
        "Michael Page": _mp_jobs(),
        "Robert Half": _rh_jobs(),
        "Robert Walters": _rw_jobs(),
    }
    counter = 0
    for _competitor, jobs in all_jobs.items():
        for job in jobs:
            counter += 1
            if job.job_url:
                sep = "&" if "?" in job.job_url else "?"
                job.job_url = f"{job.job_url}{sep}ref=mock-{counter}"
    return all_jobs


def get_seed_competitors() -> list[dict]:
    """Return ONLY the 4 targeted competitors."""
    return [
        {
            "name": "CPA Partners",
            "website_url": "https://www.cpa-partner.com",
            "careers_url": "https://www.cpa-partner.com/jobs",
            "category": "finance",
        },
        {
            "name": "Michael Page",
            "website_url": "https://www.michaelpage.fr",
            "careers_url": "https://www.michaelpage.fr/jobs/finance-comptabilité",
            "category": "large",
        },
        {
            "name": "Robert Half",
            "website_url": "https://www.roberthalf.com",
            "careers_url": "https://www.roberthalf.com/fr/fr/offres-emploi",
            "category": "large",
        },
        {
            "name": "Robert Walters",
            "website_url": "https://www.robertwalters.fr",
            "careers_url": "https://www.robertwalters.fr/jobs.html",
            "category": "large",
        },
    ]
