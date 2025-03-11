import re
import json
import html
import random
import logging
import aiohttp
import asyncio

from lxml.html import fromstring
from urllib import parse
from typing import Dict, List
from aiohttp import ClientSession, ClientError, TCPConnector

logger = logging.getLogger("CRAWLEE")
logging.basicConfig(level=logging.INFO)

BASE_URL = "https://github.com"
PROXY_RESOURCE = "https://free-proxy-list.net/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
]

BASE_HEADERS = {
    "User-Agent": random.choice(USER_AGENTS),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}


async def load_input(filename: str) -> Dict:
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in input file.")
    return {}


async def validate_proxy(proxy: str) -> bool:
    test_url = "http://www.gstatic.com/generate_204"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, proxy=f"http://{proxy}", timeout=5) as resp:
                if resp.status == 200:
                    logger.info("Proxy %s is working", proxy)
                    return True
    except Exception:
        return False


async def get_valid_proxies(proxies: List[str]) -> List[str]:
    valid_proxies = await asyncio.gather(*[validate_proxy(proxy) for proxy in proxies])
    return [proxy for proxy, is_valid in zip(proxies, valid_proxies) if is_valid]


async def gather_proxies() -> List[str]:
    logger.info("Fetching proxies...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(PROXY_RESOURCE, headers=BASE_HEADERS) as resp:
                if resp.status == 200:
                    proxy_list_raw = await resp.text()
                    proxies = re.findall(
                        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+\b", proxy_list_raw
                    )
                    return proxies
    except ClientError:
        logger.error("Failed to fetch proxies.")
    return []


async def fetch_data(session: ClientSession, keyword: str, search_type: str, extra: bool = False) -> Dict:
    url = parse.urljoin(BASE_URL, "/search")
    params = {"q": keyword, "type": search_type}
    repo_info = []

    try:
        async with session.get(url, params=params, headers=BASE_HEADERS) as resp:
            if resp.status != 200:
                logger.warning("Failed to fetch %s (status %s)", keyword, resp.status)
                return {}

            repo_list = re.findall(r'hl_name":"([^"]+)', await resp.text())

            if not repo_list:
                logger.warning("No repositories found for %s", keyword)
                return {}

            
            seen_links = set()
            for repo in repo_list:
                decoded = html.unescape(repo.encode("utf-8").decode("unicode_escape"))
                clean_part = re.sub(r"<.*?>", "", decoded)
                link = parse.urljoin(BASE_URL, clean_part)

                if link in seen_links:
                    continue
                else:
                    seen_links.add(link)

                if extra:
                    owner = clean_part.split("/")[0]
                    async with session.get(link, headers=BASE_HEADERS) as repo_resp:
                        tree = fromstring(await repo_resp.text())
                        languages = tree.xpath(
                            '//a[@data-ga-click="Repository, language stats search click, location:repo overview"]'
                        )
                        language_stats = {}
                        for selector in languages:
                            lang = selector.xpath(
                                './/span[@class="color-fg-default text-bold mr-1"]/text()'
                            )
                            stat = selector.xpath(".//span[not(@class)]/text()")
                            if lang and stat:
                                language_stats[lang[0]] = stat[0]

                        repo_info.append(
                            {
                                "url": link,
                                "extra": {
                                    "owner": owner,
                                    "language_stats": language_stats,
                                },
                            }
                        )
                else:
                    repo_info.append({"url": link})

            return repo_info
    except ClientError as e:
        logger.error("Request error for %s: %s", keyword, e)
        return {}


async def process_keywords(keywords: List[str], search_type: str, extra: bool, proxies: List[str]) -> Dict:
    output = []

    async with aiohttp.ClientSession(connector=TCPConnector(ssl=False)) as session:
        tasks = [
            fetch_data(session, keyword, search_type, extra) for keyword in keywords
        ]
        results = await asyncio.gather(*tasks)

        for res in results:
            output.extend(res)

    return output


async def main():
    logger.info("Starting GitHub scraper...")

    input_data = await load_input("input.json")
    keywords = input_data.get("keywords", [])
    search_type = input_data.get("type", "Repositories").lower()
    extra = input_data.get("extra", False)
    proxies = input_data.get("proxies", [])

    valid_proxies = await get_valid_proxies(proxies)
    if not valid_proxies:
        valid_proxies = await gather_proxies()
        valid_proxies = await get_valid_proxies(valid_proxies)

    logger.info("Using %s valid proxies.", len(valid_proxies))

    result = await process_keywords(keywords, search_type, extra, valid_proxies)

    with open("output.json", "w") as out_file:
        json.dump(result, out_file, indent=2)
        logger.info("Data successfully saved to output.json")


if __name__ == "__main__":
    asyncio.run(main())
