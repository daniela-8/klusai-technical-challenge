import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
import time


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=2),
    reraise=True,
)
async def test_func():
    print(f"[{time.time()}] Trying...")
    raise ValueError("Hard quota limit reached!")


asyncio.run(test_func())
