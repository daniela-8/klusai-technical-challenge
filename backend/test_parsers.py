"""Test HTML parsers against local HTML examples.
Validates that each parser correctly extracts all fields from
the provided example HTML files.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.scrapers.html_parsers import (
    CPAPartnerParser,
    MichaelPageParser,
    RobertHalfParser,
    RobertWaltersParser,
    detect_competitor_from_url,
)

HTML_DIR = Path(__file__).parent / "html_examples"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
CYAN = "\033[96m"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _print_job(label: str, job):
    print(f"\n{BOLD}{CYAN}═══ {label} ═══{RESET}")
    print(f"  {BOLD}Title:{RESET}        {job.job_title}")
    print(f"  {BOLD}Competitor:{RESET}   {job.competitor_name}")
    print(f"  {BOLD}Location:{RESET}     {job.location or '(none)'}")
    print(f"  {BOLD}Sector:{RESET}       {job.sector or '(none)'}")
    print(f"  {BOLD}Salary:{RESET}       {job.salary_range or '(none)'}")
    print(f"  {BOLD}Date:{RESET}         {job.posting_date or '(none)'}")
    print(f"  {BOLD}URL:{RESET}          {job.job_url or '(none)'}")
    desc_preview = (
        job.job_description[:200].replace("\n", " ")
        if job.job_description
        else "(none)"
    )
    print(f"  {BOLD}Description:{RESET}  {desc_preview}...")
    print(f"  {BOLD}Data source:{RESET}  {job.data_source}")


def _check(field_name: str, value, expected=None, must_exist=True):
    """Check a field value meets expectations."""
    if must_exist and not value:
        print(f"  {RED}✗ {field_name}: MISSING (expected a value){RESET}")
        return False
    if expected and expected.lower() not in str(value).lower():
        print(
            f"  {YELLOW}⚠ {field_name}: got '{value}', expected to contain '{expected}'{RESET}"
        )
        return False
    print(f"  {GREEN}✓ {field_name}: {str(value)[:80]}{RESET}")
    return True


def test_cpa_partners():
    print(f"\n\n{BOLD}{'='*70}")
    print(f"  CPA PARTNERS PARSER TESTS")
    print(f"{'='*70}{RESET}")
    passed = 0
    total = 0
    html = _read(HTML_DIR / "CPAPartner" / "CPAPartner_ex1.html")
    job = CPAPartnerParser.parse(html, "https://www.cpa-partner.com/jobs/example1")
    _print_job("CPA Partners Example 1", job)
    total += 1
    passed += 1 if _check("title", job.job_title) else 0
    total += 1
    passed += 1 if _check("competitor", job.competitor_name, "CPA Partners") else 0
    total += 1
    passed += 1 if _check("location", job.location) else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    total += 1
    passed += 1 if _check("sector", job.sector, must_exist=False) else 0
    total += 1
    passed += 1 if _check("posting_date", job.posting_date, must_exist=False) else 0
    html = _read(HTML_DIR / "CPAPartner" / "CPAPartner_ex2.html")
    job = CPAPartnerParser.parse(html, "https://www.cpa-partner.com/jobs/example2")
    _print_job("CPA Partners Example 2", job)
    total += 1
    passed += 1 if _check("title", job.job_title) else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    print(f"\n  {BOLD}CPA Partners: {passed}/{total} checks passed{RESET}")
    return passed, total


def test_michael_page():
    print(f"\n\n{BOLD}{'='*70}")
    print(f"  MICHAEL PAGE PARSER TESTS")
    print(f"{'='*70}{RESET}")
    passed = 0
    total = 0
    html = _read(HTML_DIR / "MichaelPage" / "MichaelPage_ex1.html")
    job = MichaelPageParser.parse(
        html, "https://www.michaelpage.fr/job-detail/example1"
    )
    _print_job("Michael Page Example 1", job)
    total += 1
    passed += 1 if _check("title", job.job_title, "Directeur") else 0
    total += 1
    passed += 1 if _check("competitor", job.competitor_name, "Michael Page") else 0
    total += 1
    passed += 1 if _check("location", job.location, "Yvelines") else 0
    total += 1
    passed += 1 if _check("salary", job.salary_range, "80") else 0
    total += 1
    passed += 1 if _check("sector", job.sector) else 0
    total += 1
    passed += 1 if _check("posting_date", job.posting_date) else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    html = _read(HTML_DIR / "MichaelPage" / "MichaelPage_ex2.html")
    job = MichaelPageParser.parse(
        html, "https://www.michaelpage.fr/job-detail/example2"
    )
    _print_job("Michael Page Example 2", job)
    total += 1
    passed += 1 if _check("title", job.job_title) else 0
    total += 1
    passed += 1 if _check("salary", job.salary_range, "40") else 0
    total += 1
    passed += 1 if _check("location", job.location) else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    print(f"\n  {BOLD}Michael Page: {passed}/{total} checks passed{RESET}")
    return passed, total


def test_robert_half():
    print(f"\n\n{BOLD}{'='*70}")
    print(f"  ROBERT HALF PARSER TESTS")
    print(f"{'='*70}{RESET}")
    passed = 0
    total = 0
    html = _read(HTML_DIR / "RobertHalf" / "RobertHalf_ex1.html")
    job = RobertHalfParser.parse(html, "https://www.roberthalf.com/example1")
    _print_job("Robert Half Example 1", job)
    total += 1
    passed += 1 if _check("title", job.job_title) else 0
    total += 1
    passed += 1 if _check("competitor", job.competitor_name, "Robert Half") else 0
    total += 1
    passed += 1 if _check("location", job.location) else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    total += 1
    passed += 1 if _check("salary", job.salary_range, must_exist=False) else 0
    total += 1
    passed += 1 if _check("posting_date", job.posting_date, must_exist=False) else 0
    html = _read(HTML_DIR / "RobertHalf" / "RobertHalf_ex2.html")
    job = RobertHalfParser.parse(html, "https://www.roberthalf.com/example2")
    _print_job("Robert Half Example 2", job)
    total += 1
    passed += 1 if _check("title", job.job_title) else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    print(f"\n  {BOLD}Robert Half: {passed}/{total} checks passed{RESET}")
    return passed, total


def test_robert_walters():
    print(f"\n\n{BOLD}{'='*70}")
    print(f"  ROBERT WALTERS PARSER TESTS")
    print(f"{'='*70}{RESET}")
    passed = 0
    total = 0
    html = _read(HTML_DIR / "RobertWalters" / "RobertWalters_ex1.html")
    job = RobertWaltersParser.parse(html, "https://www.robertwalters.fr/example1")
    _print_job("Robert Walters Example 1", job)
    total += 1
    passed += 1 if _check("title", job.job_title, "qualité") else 0
    total += 1
    passed += 1 if _check("competitor", job.competitor_name, "Robert Walters") else 0
    total += 1
    passed += 1 if _check("location", job.location, "Paris") else 0
    total += 1
    passed += 1 if _check("sector", job.sector, "Ingénieur") else 0
    total += 1
    passed += 1 if _check("salary", job.salary_range) else 0
    total += 1
    passed += 1 if _check("posting_date", job.posting_date, "2026") else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    html = _read(HTML_DIR / "RobertWalters" / "RobertWalters_ex2.html")
    job = RobertWaltersParser.parse(html, "https://www.robertwalters.fr/example2")
    _print_job("Robert Walters Example 2", job)
    total += 1
    passed += 1 if _check("title", job.job_title) else 0
    total += 1
    passed += 1 if _check("location", job.location) else 0
    total += 1
    passed += 1 if _check("description", job.job_description) else 0
    print(f"\n  {BOLD}Robert Walters: {passed}/{total} checks passed{RESET}")
    return passed, total


def test_url_detection():
    print(f"\n\n{BOLD}{'='*70}")
    print(f"  URL DETECTION TESTS")
    print(f"{'='*70}{RESET}")
    passed = 0
    total = 0
    tests = [
        ("https://www.cpa-partner.com/jobs/something", "CPA Partners"),
        ("https://www.michaelpage.fr/job-detail/something", "Michael Page"),
        ("https://www.roberthalf.com/fr/fr/emploi/something", "Robert Half"),
        ("https://www.robertwalters.fr/something/jobs/1234.html", "Robert Walters"),
        ("https://www.google.com", None),
    ]
    for url, expected in tests:
        result = detect_competitor_from_url(url)
        total += 1
        if result == expected:
            print(f"  {GREEN}✓ {url} → {result}{RESET}")
            passed += 1
        else:
            print(f"  {RED}✗ {url} → {result} (expected {expected}){RESET}")
    print(f"\n  {BOLD}URL Detection: {passed}/{total} checks passed{RESET}")
    return passed, total


if __name__ == "__main__":
    print(
        f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗"
    )
    print(f"║         HTML PARSER VALIDATION SUITE                        ║")
    print(f"╚══════════════════════════════════════════════════════════════╝{RESET}")
    results = []
    results.append(test_url_detection())
    results.append(test_cpa_partners())
    results.append(test_michael_page())
    results.append(test_robert_half())
    results.append(test_robert_walters())
    total_passed = sum(r[0] for r in results)
    total_tests = sum(r[1] for r in results)
    print(f"\n\n{BOLD}{'='*70}")
    print(f"  FINAL RESULTS: {total_passed}/{total_tests} checks passed")
    if total_passed == total_tests:
        print(f"  {GREEN}ALL CHECKS PASSED ✓{RESET}")
    else:
        print(f"  {RED}{total_tests - total_passed} CHECKS FAILED ✗{RESET}")
    print(f"{'='*70}{RESET}\n")
    sys.exit(0 if total_passed == total_tests else 1)
