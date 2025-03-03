import pytest
from unittest.mock import patch, mock_open, MagicMock, AsyncMock
from aioresponses import aioresponses
import json
import aiohttp
from github_crawlee.main import (
    main,
    process_input,
    fetch_data,
    gather_proxies,
    prepare_request,
    PROXY_RESOURCE,
)


# Test data
mock_keywords = ["python", "aiohttp", "github"]
mock_search_type = "repository"
mock_extra = False
mock_repo_response = {
    "python": [
        {"url": "https://github.com/python/cpython"},
        {"url": "https://github.com/python/python"},
    ],
    "aiohttp": [{"url": "https://github.com/aio-libs/aiohttp"}],
}


@pytest.mark.asyncio
async def test_process_input_list():
    mock_fetch_data_result = [
        "https://github.com/python/cpython",
        "https://github.com/aiohttp/aiohttp",
    ]

    with patch("github_crawlee.main.fetch_data", return_value=mock_fetch_data_result):
        result = await process_input("tests/test_inputs/test_input_list.json")

        assert isinstance(result, list), f"Expected list, but got {type(result)}"
        assert result == mock_fetch_data_result, (
            f"Expected {mock_fetch_data_result}, but got {result}"
        )


@pytest.mark.asyncio
async def test_process_input_dict():
    mock_fetch_data_result = ["https://github.com/python/cpython"]

    with patch("github_crawlee.main.fetch_data", return_value=mock_fetch_data_result):
        result = await process_input("tests/test_inputs/test_input_dict.json")

        assert isinstance(result, list), f"Expected list, but got {type(result)}"
        assert result == mock_fetch_data_result, (
            f"Expected {mock_fetch_data_result}, but got {result}"
        )


@pytest.mark.asyncio
async def test_process_input_empty_or_txt():
    result = await process_input("tests/test_inputs/test_input_empty.json")

    assert result is None, f"Expected None or error handling, but got {result}"


@pytest.mark.asyncio
async def test_gather_proxies():
    with aioresponses() as m:
        m.get(PROXY_RESOURCE, payload="<html>...</html>")

        proxies = await gather_proxies()
        assert proxies is not None
        assert "http" in proxies
        assert "https" in proxies


@pytest.mark.asyncio
async def test_prepare_request():
    use_proxy = True
    with patch(
        "github_crawlee.main.gather_proxies",
        return_value={"http": ["http://proxy1"], "https": ["https://proxy1"]},
    ):
        session = await prepare_request(use_proxy=use_proxy)
        assert isinstance(session, aiohttp.ClientSession)


@pytest.mark.asyncio
async def test_main():
    with patch(
        "builtins.open",
        mock_open(
            read_data=json.dumps(
                {"keywords": mock_keywords, "type": mock_search_type, "extra": False}
            )
        ),
    ):
        with patch("json.dump") as mock_json_dump:
            await main()
            mock_json_dump.assert_called_once()


if __name__ == "__main__":
    pytest.main()
