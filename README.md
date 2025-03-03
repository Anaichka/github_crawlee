# GitHub Crawlee

GitHub Crawlee is an asynchronous Python scraper that fetches GitHub repositories based on provided keywords. It supports optional proxy usage to avoid rate limits and can extract additional repository details.

## Features

- Asynchronous requests using aiohttp for efficiency

- Proxy support using free proxies from https://free-proxy-list.net/

- Extracts repositories based on keywords and type (Repositories, Issues, etc.)

- Optionally fetches additional repository details (owner, language statistics)

- Caches gathered proxies for efficiency

## Project Structure
```
github_crawlee/
├── example_output/
│   ├── output.json
├── github_crawlee/
│   ├── main.py
├── tests/
│   ├── test_inputs/
│   │   ├── test_input_dict.json
│   │   ├── test_input_empty.json
│   │   ├── test_input_list.json
│   ├── tests.py
├── input.json
├── LICENSE
├── requirements.txt
```

## Installation

Clone the repository:
```
git clone https://github.com/yourusername/github_crawlee.git
cd github_crawlee
```
Install dependencies:
```
pip install -r requirements.txt
```
## Usage

Prepare an input.json file with the following structure:
```
{
    "keywords": [
        "openstack",
        "nova",
        "css"
    ],
    "type": "Repositories",
    "extra": true
}
```
- ```keywords```: List of search terms.

- ```type```: Type of search (Repositories, Issues, etc.).

- ```extra```: If true, fetches additional repository details.

## Run the scraper:
```
python github_crawlee/main.py
```
The output will be saved in ```output.json```.

## Example Output
```
{
    "openstack": [
        {
            "url": "https://github.com/openstack/nova",
            "extra": {
                "owner": "openstack",
                "language_stats": {
                    "Python": "84.2%",
                    "Shell": "7.1%",
                    "Other": "8.7%"
                }
            }
        }
    ]
}
```
## Proxy Handling

- If proxies are enabled, the script fetches a fresh proxy list from ```https://free-proxy-list.net/```.

- Cached proxies are used to avoid unnecessary re-fetching.

## Running Tests

To run tests:
```
PYTHONPATH=$(pwd) pytest tests/tests.py
```
## License

This project is licensed under the MIT License. See ```LICENSE``` for details.
