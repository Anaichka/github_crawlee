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
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
}

PROXY_LIST = None  # cache


async def process_input(filename) -> Dict:
    with open(filename, "r") as input_file:
        input_data = None
        try:
            input_data = json.loads(input_file.read())
        except json.JSONDecodeError:
            logger.error(
                "Please input a valid data type. Only JSON-formatted data is allowed."
            )

        if isinstance(input_data, dict):
            keywords = input_data.get("keywords", [])
            search_type = input_data.get("type").lower()
            extra = input_data.get("extra")
            return await fetch_data(keywords, search_type, extra)
        elif isinstance(input_data, list):
            for member in input_data:
                keywords = member.get("keywords", [])
                search_type = member.get("type").lower()
                extra = member.get("extra")
                return await fetch_data(keywords, search_type, extra)
        else:
            logger.error("JSON file can't be empty")


async def gather_proxies() -> List:
    proxies = {"http": [], "https": []}
    lookup_expr_http = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:(?:80|8080|8008)\b"
    lookup_expr_https = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:(?:443|8443)\b"
    logger.info("Starting to collect proxies...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(PROXY_RESOURCE, headers=BASE_HEADERS) as resp:
                if resp.status == 200:
                    logger.info("Response received. Going to parse proxy list...")
                    proxy_list_raw = await resp.text()
                    proxy_selection_http = re.findall(lookup_expr_http, proxy_list_raw)
                    proxy_selection_https = re.findall(
                        lookup_expr_https, proxy_list_raw
                    )
                    proxies["http"] = proxy_selection_http
                    proxies["https"] = proxy_selection_https
                    logger.info("Proxy list parsed.")
                else:
                    logger.warning(f"Failed to fetch proxies with status {resp.status}")
        except ClientError as e:
            logger.error(f"Error fetching proxies: {e}")
    return proxies


async def prepare_request(use_proxy: bool = False) -> ClientSession:
    if use_proxy:
        proxies = PROXY_LIST if PROXY_LIST else await gather_proxies()
        all_proxies = proxies.get("http", []) + proxies.get("https", [])

        if not all_proxies:
            logger.warning("No proxies available, using direct connection.")
            return ClientSession()

        selected_proxy = random.choice(all_proxies)
        logger.info(f"Using proxy: {selected_proxy}")

        connector = TCPConnector(ssl=False)
        session = ClientSession(
            connector=connector, trust_env=True, proxy=f"http://{selected_proxy}"
        )
    else:
        session = ClientSession()

    return session


async def fetch_data(keywords: List, search_type: str, extra: str = False) -> Dict:
    output_dict = {}
    logger.info("Preparing request")

    async with await prepare_request() as session:
        logger.info("Starting to iterate through keyword list.")
        for word in keywords:
            logger.info(f"Requesting data for keyword: {word}")
            raw_repository_list = []
            await asyncio.sleep(random.uniform(1, 3))

            try:
                async with session.get(
                    parse.urljoin(BASE_URL, "/search"),
                    params={"q": word, "type": search_type},
                    headers=BASE_HEADERS,
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Successfully fetched data for {word}")
                        raw_repository_list = re.findall(
                            r'hl_name":"([^"]+)', await resp.text()
                        )
                    else:
                        logger.warning(
                            f"Received non-200 status code for {word}, retrying."
                        )
                        raise Exception("Non-200 status code received.")
            except ClientError as e:
                logger.error(f"Error encountered: {e}. Retrying with proxy.")

            if raw_repository_list:
                repo_info = []
                for elem in raw_repository_list:
                    decoded_unicode = elem.encode("utf-8").decode("unicode_escape")
                    decoded_url_part = html.unescape(decoded_unicode)  # decode url part
                    clean_part = re.sub(
                        r"<.*?>", "", decoded_url_part
                    )  # remove extra symbols
                    link = parse.urljoin(BASE_URL, clean_part)

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

                output_dict[word] = repo_info
            else:
                logger.error("No links found.")

    return output_dict


async def main():
    with open("output.json", "w") as out_file:
        logger.info("Let's crawl some Github content! Starting...")
        result = await process_input(filename="input.json")
        if result:
            json.dump(result, out_file)
            logger.info("Success! Enjoy your data!")
        else:
            logger.info("Oops, something went wrong. Check logs below!")


if __name__ == "__main__":
    asyncio.run(main())
