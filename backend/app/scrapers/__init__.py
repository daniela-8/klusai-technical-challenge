"""Scraping pipeline — base scraper and competitor-specific implementations."""

from app.scrapers.base import BaseScraper
from app.scrapers.manager import ScrapingManager

__all__ = ["BaseScraper", "ScrapingManager"]
