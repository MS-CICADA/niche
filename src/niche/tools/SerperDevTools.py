# niche/tools/SerperDevTools.py

import os
import requests
from crewai_tools import BaseTool
import traceback
import json
from typing import List
from dotenv import load_dotenv
from pydantic import PrivateAttr

# Load environment variables
load_dotenv()


class SerperDevScraper(BaseTool):
    name: str = "SerperDevScraper"
    description: str = """
    Fetches SERP (Search Engine Results Page) data using the SerperDev API.

    Input: A single search query string.
    Example: "best hiking trails in California"

    Output: A JSON string containing the top search results for the given query.

    IMPORTANT USAGE GUIDELINES:
    1. Use this tool to get top search results for a given keyword or query.
    2. Provide only one search query at a time.
    3. Limit the total number of API calls to stay within the allowed limits.
    """
    _api_key: str = PrivateAttr()
    _base_url: str = PrivateAttr()
    _headers: dict = PrivateAttr()
    _debug: bool = PrivateAttr(default=False)

    def __init__(self, debug: bool = False):
        super().__init__()
        self._api_key = os.getenv('SERPER_API_KEY')
        if not self._api_key:
            raise ValueError("SERPER_API_KEY environment variable is not set.")
        self._base_url = 'https://google.serper.dev/search'
        self._headers = {
            'X-API-KEY': self._api_key,
            'Content-Type': 'application/json'
        }
        self._debug = debug

    def _run(self, query: str) -> str:
        try:
            # Debug: Print input
            if self._debug:
                print(f"[DEBUG-API-INPUT] SerperDevScraper input query: {query}")

            payload = {
                "q": query,
                "gl": "us",  # Geo location
                "hl": "en"   # Language
            }
            response = requests.post(self._base_url, headers=self._headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Debug: Print output
            if self._debug:
                print(f"[DEBUG-API-OUTPUT] SerperDevScraper response: {json.dumps(data, indent=2)}")

            # Process the data to extract relevant information
            search_results = self.process_results(data)
            output = json.dumps(search_results, indent=2)
            return output
        except Exception as e:
            # Debug: Print error
            if self._debug:
                error_message = f"SerperDevScraper error: {str(e)}\n{traceback.format_exc()}"
                print(f"[DEBUG-ERROR] {error_message}")
            return f"Error: {str(e)}"

    def process_results(self, data) -> List[dict]:
        # Extract the organic search results
        organic_results = data.get('organic', [])
        processed_results = []
        for result in organic_results:
            processed_result = {
                'position': result.get('position'),
                'title': result.get('title'),
                'link': result.get('link'),
                'snippet': result.get('snippet'),
            }
            processed_results.append(processed_result)
        return processed_results
