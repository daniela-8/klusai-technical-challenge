"""Targeted HTML parsers for each competitor website.
Each parser knows the exact HTML structure of its competitor's job detail
pages and extracts all required fields deterministically using BeautifulSoup.
Strategy per competitor:
- CPA Partners:     Webflow CMS — structured divs with predictable CSS classes
- Michael Page:     Drupal CMS  — combination of HTML elements + JS data layer + LD+JSON
- Robert Half:      React SPA   — ALL data in embedded JSON within <script> tag
- Robert Walters:   AEM CMS     — structured divs with itemprop attributes
"""

from __future__ import annotations
import json
import re
from html import unescape
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, Tag
from app.scrapers.base import ScrapedJob
from app.core.logging import get_logger

logger = get_logger(__name__)
DOMAIN_TO_COMPETITOR: dict[str, str] = {
    "cpa-partner.com": "CPA Partners",
    "michaelpage.fr": "Michael Page",
    "roberthalf.com": "Robert Half",
    "robertwalters.fr": "Robert Walters",
}


def detect_competitor_from_url(url: str) -> str | None:
    """Identify which competitor a URL belongs to by domain matching."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.removeprefix("www.")
        for domain, name in DOMAIN_TO_COMPETITOR.items():
            if hostname == domain or hostname.endswith("." + domain):
                return name
    except Exception:
        pass
    return None


def get_parser_for_competitor(competitor_name: str) -> type | None:
    """Return the parser class for a given competitor name."""
    return _PARSER_REGISTRY.get(competitor_name)


def _strip_html(html_text: str) -> str:
    """Remove HTML tags and clean up whitespace."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "lxml")
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_text(text: str | None) -> str:
    """Normalize whitespace in extracted text."""
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class CPAPartnerParser:
    """Parse CPA Partner job detail pages (Webflow CMS).
    Structure:
    - Title:       h1.heading-style-h1
    - Date:        .blog-post-header_date .text-weight-medium
    - Tags:        .blog-post-header_meta-wrapper .tag_item.is-light (contract, sector, salary)
    - Location:    div.job-location
    - Description: .text-rich-text.w-richtext blocks + h2.heading-style-h4 headings
    - URL:         link[rel=canonical] or page URL
    """

    @staticmethod
    def parse(html: str, url: str) -> ScrapedJob:
        soup = BeautifulSoup(html, "lxml")
        title_el = soup.select_one("h1.heading-style-h1")
        title = _clean_text(title_el.get_text()) if title_el else ""
        posting_date = None
        date_wrapper = soup.select_one(".blog-post-header_date")
        if date_wrapper:
            date_el = date_wrapper.select_one(".text-weight-medium")
            if date_el:
                posting_date = _clean_text(date_el.get_text())
        meta_wrapper = soup.select_one(".blog-post-header_meta-wrapper:not(.hidden)")
        tags: list[str] = []
        if meta_wrapper:
            tag_items = meta_wrapper.select(".tag_item.is-light")
            tags = [_clean_text(t.get_text()) for t in tag_items]
        contract_type = tags[0] if len(tags) > 0 else None
        sector = tags[1] if len(tags) > 1 else None
        salary_range = tags[2] if len(tags) > 2 else None
        location = None
        loc_el = soup.select_one("div.job-location")
        if loc_el:
            location = _clean_text(loc_el.get_text())
        description_parts: list[str] = []
        content_div = soup.select_one(".content_component") or soup.select_one(
            ".section_content"
        )
        if content_div:
            for el in content_div.select(
                "h2.heading-style-h4, .text-rich-text.w-richtext"
            ):
                text = el.get_text(separator="\n", strip=True)
                if text:
                    description_parts.append(text)
        description = "\n\n".join(description_parts)
        canonical = soup.select_one("link[rel='canonical']")
        job_url = canonical["href"] if canonical and canonical.get("href") else url
        logger.info(
            "cpa_partner_parsed",
            title=title[:80] if title else "N/A",
            location=location,
            has_salary=bool(salary_range),
        )
        return ScrapedJob(
            competitor_name="CPA Partners",
            job_title=title,
            job_description=description,
            location=location,
            sector=sector,
            salary_range=salary_range,
            job_url=job_url,
            posting_date=posting_date,
            data_source="scraped",
        )


class MichaelPageParser:
    """Parse Michael Page job detail pages (Drupal CMS).
    Structure:
    - Title:       h1.job-apply-job-title > span
    - Location:    span.job-location > strong
    - Salary:      thunderheadDataLayer JS variable (salary + salaryCurrency)
    - Sector:      Summary section dl items
    - Date:        p.job-posted-date or LD+JSON datePosted
    - Description: .job_advert__job-desc-* divs
    - Contact:     .job-contact-info .field--item
    - URL:         meta[property='og:url'] or canonical
    """

    @staticmethod
    def parse(html: str, url: str) -> ScrapedJob:
        soup = BeautifulSoup(html, "lxml")
        title = ""
        title_el = soup.select_one("h1.job-apply-job-title")
        if title_el:
            span = title_el.select_one("span")
            title = _clean_text(span.get_text() if span else title_el.get_text())
        location = None
        loc_el = soup.select_one("span.job-location strong")
        if loc_el:
            location = _clean_text(loc_el.get_text())
        else:
            location = MichaelPageParser._extract_summary_field(soup, "Localisation")
        salary_range = None
        salary_div = soup.select_one("div.job-salary")
        if salary_div:
            salary_text = _clean_text(salary_div.get_text())
            salary_range = MichaelPageParser._parse_job_salary_div(salary_text)
        if not salary_range:
            for script in soup.find_all("script"):
                script_text = script.string or ""
                if "thunderheadDataLayer" in script_text:
                    salary_match = re.search(r'"salary"\s*:\s*(\d+)', script_text)
                    if salary_match:
                        salary_val = int(salary_match.group(1))
                        if salary_val > 0:
                            salary_range = f"\u20ac{salary_val:,}/yr"
                    break
        if not salary_range:
            deal_div = soup.select_one(".job_advert__job-desc-deal")
            if deal_div:
                deal_text = deal_div.get_text(separator=" ", strip=True)
                salary_range = MichaelPageParser._extract_salary_from_text(deal_text)
        if not salary_range:
            desc_area = soup.select_one("#job-description")
            if desc_area:
                desc_text = desc_area.get_text(separator=" ", strip=True)
                salary_range = MichaelPageParser._extract_salary_from_text(desc_text)
        sector = MichaelPageParser._extract_summary_field(soup, "Spécialisation")
        industry = MichaelPageParser._extract_summary_field(soup, "Secteur d'activité")
        if industry and sector:
            sector = f"{sector} — {industry}"
        elif industry:
            sector = industry
        contract_el = soup.select_one("span.job-contract-type strong")
        contract_type = _clean_text(contract_el.get_text()) if contract_el else None
        posting_date = None
        date_el = soup.select_one("p.job-posted-date")
        if date_el:
            date_text = _clean_text(date_el.get_text())
            date_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_text)
            if date_match:
                day, month, year = (
                    date_match.group(1),
                    date_match.group(2),
                    date_match.group(3),
                )
                posting_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        if not posting_date:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    ld_data = json.loads(script.string or "")
                    if isinstance(ld_data, dict) and "datePosted" in ld_data:
                        posting_date = ld_data["datePosted"]
                        break
                except (json.JSONDecodeError, TypeError):
                    continue
        desc_parts: list[str] = []
        bullets_div = soup.select_one(".job-bullet-points")
        if bullets_div:
            desc_parts.append(bullets_div.get_text(separator="\n", strip=True))
        about_div = soup.select_one(".job_advert__job-desc-company")
        if about_div:
            desc_parts.append(
                "À propos de notre client:\n"
                + about_div.get_text(separator="\n", strip=True)
            )
        role_div = soup.select_one(".job_advert__job-desc-role")
        if role_div:
            desc_parts.append(
                "Description du poste:\n"
                + role_div.get_text(separator="\n", strip=True)
            )
        candidate_div = soup.select_one(".job_advert__job-desc-candidate")
        if candidate_div:
            desc_parts.append(
                "Profil recherché:\n"
                + candidate_div.get_text(separator="\n", strip=True)
            )
        deal_div = soup.select_one(".job_advert__job-desc-deal")
        if deal_div:
            desc_parts.append(
                "Conditions et Avantages:\n"
                + deal_div.get_text(separator="\n", strip=True)
            )
        description = "\n\n".join(desc_parts)
        og_url = soup.select_one("meta[property='og:url']")
        job_url = og_url["content"] if og_url and og_url.get("content") else url
        contact_info = soup.select_one(".job-contact-info")
        contact_name = None
        if contact_info:
            name_el = contact_info.select_one(".field--item")
            if name_el:
                contact_name = _clean_text(name_el.get_text())
        logger.info(
            "michaelpage_parsed",
            title=title[:80] if title else "N/A",
            location=location,
            salary=salary_range,
            has_date=bool(posting_date),
        )
        return ScrapedJob(
            competitor_name="Michael Page",
            job_title=title,
            job_description=description,
            location=location,
            sector=sector,
            salary_range=salary_range,
            job_url=job_url,
            posting_date=posting_date,
            data_source="scraped",
        )

    @staticmethod
    def _extract_summary_field(soup: BeautifulSoup, label: str) -> str | None:
        """Extract a value from the summary section's <dl> items."""
        for dt in soup.select("dt.summary-detail-field-label"):
            if label.lower() in _clean_text(dt.get_text()).lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    return _clean_text(dd.get_text())
        return None

    @staticmethod
    def _parse_job_salary_div(text: str) -> str | None:
        """Parse salary from the div.job-salary element.
        Handles European number format:
          €65.000 - €70.000 par an  → €65,000 – €70,000/yr
          €104.748 - €123.793 par an → €104,748 – €123,793/yr
          €150.000 - €160.000 par an → €150,000 – €160,000/yr
        """
        if not text:
            return None
        m = re.search(
            r"€\s*([\d.]+)\s*[-–]\s*€\s*([\d.]+)\s*(?:par\s+an)?",
            text,
        )
        if m:
            low_str = m.group(1).replace(".", "")
            high_str = m.group(2).replace(".", "")
            try:
                low = int(low_str)
                high = int(high_str)
                if low > 0 and high > 0:
                    return f"\u20ac{low:,} \u2013 \u20ac{high:,}/yr"
            except ValueError:
                pass
        m = re.search(r"€\s*([\d.]+)\s*(?:par\s+an)?", text)
        if m:
            val_str = m.group(1).replace(".", "")
            try:
                val = int(val_str)
                if val > 0:
                    return f"\u20ac{val:,}/yr"
            except ValueError:
                pass
        return None

    @staticmethod
    def _extract_salary_from_text(text: str) -> str | None:
        """Extract salary range from free-text mentions in the job description.
        Returns unified format: €XX,000/yr or €XX,000 – €YY,000/yr
        """
        if not text:
            return None
        m = re.search(
            r"(\d{2,3})\s*[Kk]\s*€?\s*[-–àa]\s*(\d{2,3})\s*[Kk]\s*€"
            r"(\s*[+/]\s*[\w\séèê]+)?",
            text,
        )
        if m:
            low, high = int(m.group(1)) * 1000, int(m.group(2)) * 1000
            extra = m.group(3).strip() if m.group(3) else ""
            result = f"\u20ac{low:,} \u2013 \u20ac{high:,}/yr"
            if extra:
                result += f" {extra}"
            return result
        m = re.search(
            r"(\d{2,3})\s*0{3}\s*€\s*[-–àa]\s*(\d{2,3})\s*0{3}\s*€",
            text,
        )
        if m:
            low, high = int(m.group(1)) * 1000, int(m.group(2)) * 1000
            return f"\u20ac{low:,} \u2013 \u20ac{high:,}/yr"
        m = re.search(r"(\d{2,3})\s*[Kk]\s*€\s*(/an)?", text)
        if m:
            val = int(m.group(1)) * 1000
            return f"\u20ac{val:,}/yr"
        return None


class RobertHalfParser:
    """Parse Robert Half job detail pages (React SPA with embedded JSON).
    The page embeds ALL job data in a <script> tag:
      aemSettings.rh_job_search.jobDetails = JSON.parse('{...}')
    Fields extracted from JSON:
    - jobtitle, description, city, stateprovince, functional_role,
      emptype, payrate_min, payrate_max, payrate_period,
      salary_currency, date_posted, job_detail_url, industry
    """

    @staticmethod
    def parse(html: str, url: str) -> ScrapedJob:
        soup = BeautifulSoup(html, "lxml")
        job_data = RobertHalfParser._extract_job_json(soup)
        if not job_data:
            logger.warning("roberthalf_no_json_found", url=url)
            return ScrapedJob(
                competitor_name="Robert Half",
                job_title="Extraction failed",
                job_description="Could not extract job data from page.",
                job_url=url,
                data_source="scraped",
            )
        title = job_data.get("jobtitle", "")
        raw_desc = job_data.get("description", "")
        description = _strip_html(raw_desc)
        city = job_data.get("city", "")
        state = job_data.get("stateprovince", "")
        location = ", ".join(filter(None, [city, state]))
        sector = job_data.get("functional_role", None)
        industry = job_data.get("industry", None)
        if industry and sector:
            sector = f"{sector} — {industry}"
        elif industry:
            sector = industry
        salary_range = RobertHalfParser._format_salary(job_data)
        posting_date = job_data.get("date_posted", None)
        if posting_date:
            posting_date = (
                posting_date.split("T")[0] if "T" in posting_date else posting_date
            )
        job_url = job_data.get("job_detail_url", url)
        emp_type = job_data.get("emptype", "")
        logger.info(
            "roberthalf_parsed",
            title=title[:80] if title else "N/A",
            location=location,
            salary=salary_range,
            has_date=bool(posting_date),
        )
        return ScrapedJob(
            competitor_name="Robert Half",
            job_title=title,
            job_description=description,
            location=location,
            sector=sector,
            salary_range=salary_range,
            job_url=job_url,
            posting_date=posting_date,
            data_source="scraped",
        )

    @staticmethod
    def _extract_job_json(soup: BeautifulSoup) -> dict | None:
        """Extract the job details JSON from the embedded script tag."""
        for script in soup.find_all("script"):
            script_text = script.string or ""
            if "rh_job_search" not in script_text or "jobDetails" not in script_text:
                continue
            match = re.search(
                r"aemSettings\.rh_job_search\.jobDetails\s*=\s*JSON\.parse\(\s*'(.*?)'\s*\)",
                script_text,
                re.DOTALL,
            )
            if not match:
                continue
            try:
                raw_json = match.group(1)
                decoded = raw_json.encode("raw_unicode_escape").decode("unicode_escape")
                parsed = json.loads(decoded)
                jobs_response = parsed.get("jobDetailsResponse", {})
                data = jobs_response.get("data", {})
                jobs = data.get("jobs", [])
                if jobs:
                    return jobs[0]
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.warning("roberthalf_json_parse_error", error=str(e))
                continue
        return None

    @staticmethod
    def _format_salary(job_data: dict) -> str | None:
        """Format salary range from min/max/period/currency fields.
        Outputs unified format: €XX,000/yr
        """
        pay_min = job_data.get("payrate_min", "")
        pay_max = job_data.get("payrate_max", "")
        period = job_data.get("payrate_period", "")
        if not pay_min and not pay_max:
            return None
        try:
            min_val = int(float(pay_min)) if pay_min else None
            max_val = int(float(pay_max)) if pay_max else None
        except ValueError:
            return None
        period_label = "/yr"
        if period:
            period_map = {
                "Yearly": "/yr",
                "Monthly": "/mo",
                "Hourly": "/hr",
                "Daily": "/day",
            }
            period_label = period_map.get(period, "/yr")
        if min_val and max_val and min_val != max_val:
            return f"\u20ac{min_val:,} \u2013 \u20ac{max_val:,}{period_label}"
        elif min_val:
            return f"\u20ac{min_val:,}{period_label}"
        elif max_val:
            return f"\u20ac{max_val:,}{period_label}"
        return None


class RobertWaltersParser:
    """Parse Robert Walters job detail pages (AEM CMS).
    Structure:
    - Title:       div.job-advert-title h1
    - Description: div.job-advert-description
    - Attributes:  .job-advert-attributes-item spans (contract, expertise,
                   role, industry, salary, location, date, consultant)
    - Date:        .job-advert-attribute-date-posted or itemprop="datePosted"
    - URL:         link[rel=canonical] or page URL
    """

    @staticmethod
    def parse(html: str, url: str) -> ScrapedJob:
        soup = BeautifulSoup(html, "lxml")
        title = ""
        title_el = soup.select_one("div.job-advert-title h1")
        if title_el:
            title = _clean_text(title_el.get_text())
        desc_el = soup.select_one("div.job-advert-description")
        description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""
        attributes = RobertWaltersParser._extract_attributes(soup)
        location = attributes.get("Localisation") or attributes.get("Localisation ")
        expertise = attributes.get("Expertise")
        industry = attributes.get("Secteur")
        role = attributes.get("Rôle")
        sector_parts = [p for p in [expertise, industry] if p]
        sector = " — ".join(sector_parts) if sector_parts else None
        salary_range = attributes.get("Salaire") or attributes.get("Salaire ")
        contract_type = attributes.get("Type de contrat")
        posting_date = attributes.get("Date de publication") or attributes.get(
            "Date de publication "
        )
        if not posting_date:
            date_itemprop = soup.select_one("span[itemprop='datePosted']")
            if date_itemprop:
                posting_date = _clean_text(date_itemprop.get_text())
        consultant = attributes.get("Consultant")
        canonical = soup.select_one("link[rel='canonical']")
        job_url = canonical["href"] if canonical and canonical.get("href") else url
        if job_url and not job_url.startswith("http"):
            job_url = urljoin("https://www.robertwalters.fr", job_url)
        logger.info(
            "robertwalters_parsed",
            title=title[:80] if title else "N/A",
            location=location,
            salary=salary_range,
            has_date=bool(posting_date),
        )
        return ScrapedJob(
            competitor_name="Robert Walters",
            job_title=title,
            job_description=description,
            location=location,
            sector=sector,
            salary_range=salary_range,
            job_url=job_url,
            posting_date=posting_date,
            data_source="scraped",
        )

    @staticmethod
    def _extract_attributes(soup: BeautifulSoup) -> dict[str, str]:
        """Extract all key-value attribute pairs from the sidebar."""
        attrs: dict[str, str] = {}
        for item in soup.select(".job-advert-attributes-item"):
            label_el = item.select_one(".job-advert-attribute-label")
            value_el = item.select_one(".job-advert-attribute-value")
            if label_el and value_el:
                label = _clean_text(label_el.get_text()).rstrip(":")
                value = _clean_text(value_el.get_text())
                attrs[label] = value
        return attrs


_PARSER_REGISTRY: dict[str, type] = {
    "CPA Partners": CPAPartnerParser,
    "Michael Page": MichaelPageParser,
    "Robert Half": RobertHalfParser,
    "Robert Walters": RobertWaltersParser,
}
