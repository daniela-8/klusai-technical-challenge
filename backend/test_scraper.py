import asyncio
import httpx
from bs4 import BeautifulSoup


async def test_url(url: str):
    print(f"\\n--- Testing {url} ---")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            print(f"Status Code: {response.status_code} for {response.url}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                print(f"Page title: {soup.title.string if soup.title else 'No title'}")
                body = soup.find("body")
                if body:
                    text = body.get_text(separator=" ", strip=True)
                    print(f"Body text snippet: {text[:500]}")
                    if "roberthalf" in url:
                        jobs = soup.select("article")
                        print(f"Found {len(jobs)} articles")
                        for j in jobs[:2]:
                            print(j.get_text(strip=True)[:100])
                    elif "uptoo" in url:
                        jobs = soup.select("a")
                        print(f"Found {len(jobs)} links")
                        for j in jobs[:5]:
                            print(j.get_text(strip=True)[:50])
                    elif "hays" in url:
                        jobs = soup.select("div.search-result")
                        print(f"Found {len(jobs)} div.search-result")
                        for j in jobs[:2]:
                            print(j.get_text(strip=True)[:100])
        except Exception as e:
            print(f"Error: {e}")


async def main():
    urls = [
        "https://www.hays.fr/recherche-d-offres",
        "https://www.roberthalf.com/fr/fr/offres-emploi",
        "https://uptoo.fr/offres-emploi",
    ]
    for url in urls:
        await test_url(url)


if __name__ == "__main__":
    asyncio.run(main())
