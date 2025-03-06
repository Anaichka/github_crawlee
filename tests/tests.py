import re
import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, mock_open
from aioresponses import aioresponses
from github_crawlee.main import (
    load_input, validate_proxy, get_valid_proxies,
    gather_proxies, fetch_data, process_keywords
)


@pytest.mark.asyncio
async def test_load_input():
    valid_json = '{"keywords": ["test"], "type": "Repositories", "extra": true}'
    with patch("builtins.open", mock_open(read_data=valid_json)):
        result = await load_input("input.json")
        assert result == {"keywords": ["test"], "type": "Repositories", "extra": True}


    with patch("builtins.open", mock_open(read_data="{invalid_json}")):
        result = await load_input("input.json")
        assert result == {}  


@pytest.mark.asyncio
async def test_validate_proxy():
    with aioresponses() as mock_resp:
        mock_resp.get("https://httpbin.org/ip", status=200)
        assert await validate_proxy("192.168.1.1:8080") is True

        mock_resp.get("https://httpbin.org/ip", status=500)
        assert await validate_proxy("192.168.1.1:8080") is False


@pytest.mark.asyncio
async def test_get_valid_proxies():
    with patch("github_crawlee.main.validate_proxy", side_effect=[True, False, True]):
        proxies = ["192.168.1.1:8080", "192.168.1.2:8080", "192.168.1.3:8080"]
        valid_proxies = await get_valid_proxies(proxies)
        assert valid_proxies == ["192.168.1.1:8080", "192.168.1.3:8080"]


@pytest.mark.asyncio
async def test_gather_proxies():
    proxy_page_html = "192.168.1.1:8080\n192.168.1.2:8080\n"
    with aioresponses() as mock_resp:
        mock_resp.get("https://free-proxy-list.net/", status=200, body=proxy_page_html)
        proxies = await gather_proxies()
        assert "192.168.1.1:8080" in proxies
        assert "192.168.1.2:8080" in proxies


@pytest.mark.asyncio
async def test_fetch_data():
    html_response = '{"hl_name":"repo1"}{"hl_name":"repo2"}'
    repo_page = '<a data-ga-click="Repository, language stats search click, location:repo overview"></a>'

    with aioresponses() as mock_resp:
        mock_resp.get(re.compile(r"https://github.com/search.*"), status=200, body=html_response)

        mock_resp.get("https://github.com/repo1", status=200, body=repo_page)
        mock_resp.get("https://github.com/repo2", status=200, body=repo_page)

        async with aiohttp.ClientSession() as session:
            result = await fetch_data(session, "test", "Repositories", extra=True)

    assert "test" in result
    assert len(result["test"]) == 2


@pytest.mark.asyncio
async def test_process_keywords():
    with patch("github_crawlee.main.fetch_data", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [
            {"keyword1": [{"url": "https://github.com/repo1"}]},
            {"keyword2": [{"url": "https://github.com/repo2"}]},
        ]
        result = await process_keywords(["keyword1", "keyword2"], "Repositories", False, [])

    assert "keyword1" in result
    assert "keyword2" in result
    assert result["keyword1"][0]["url"] == "https://github.com/repo1"


@pytest.mark.asyncio
async def test_main():
    mock_input = '{"keywords": ["test"], "type": "Repositories", "extra": false, "proxies": []}'
    with patch("builtins.open", mock_open(read_data=mock_input)), \
         patch("github_crawlee.main.get_valid_proxies", new_callable=AsyncMock, return_value=[]), \
         patch("github_crawlee.main.gather_proxies", new_callable=AsyncMock, return_value=[]), \
         patch("github_crawlee.main.process_keywords", new_callable=AsyncMock, return_value={"test": []}), \
         patch("json.dump") as mock_json_dump:

        from github_crawlee.main import main
        await main()

        mock_json_dump.assert_called_once()
