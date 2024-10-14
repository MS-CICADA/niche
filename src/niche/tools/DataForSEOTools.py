# niche/tools/DataForSEOTools.py

import requests
import json
import os
import base64
from typing import List, Dict
from crewai_tools import BaseTool
from dotenv import load_dotenv
from pydantic import PrivateAttr

# Load environment variables
load_dotenv()

# Load DataForSEO credentials from environment variables
DATAFORSEO_LOGIN = os.getenv('DATAFORSEO_LOGIN')
DATAFORSEO_PASSWORD = os.getenv('DATAFORSEO_PASSWORD')

class DataForSEOClient:
    def __init__(self, debug: bool = False):
        self.base_url = 'https://api.dataforseo.com/v3/'
        self.credentials = base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()
        self.headers = {
            'Authorization': f'Basic {self.credentials}',
            'Content-Type': 'application/json'
        }
        self.cache = {}
        self.api_call_count = 0
        self.debug = debug

    def get_keywords_for_keywords(self, keywords: List[str]) -> Dict[str, Dict]:
        payload = [{
            "keywords": keywords,
            "language_code": "en",
            "location_code": 2840  # USA
        }]
        url = self.base_url + 'keywords_data/google_ads/keywords_for_keywords/live'
        response = requests.post(url, headers=self.headers, data=json.dumps(payload))
        self.api_call_count += 1
        return response.json()

    def get_google_trends_data(self, keywords: List[str]) -> Dict[str, Dict]:
        results = {}
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i+5]
            payload = {
                "keywords": batch
            }
            url = self.base_url + 'keywords_data/google_trends/explore/live'
            if self.debug:
                print(f"[DEBUG-API-INPUT] get_google_trends_data payload: {json.dumps(payload, indent=2)}")
            try:
                response = requests.post(url, headers=self.headers, data=json.dumps(payload))
                self.api_call_count += 1
                data = response.json()
                if self.debug:
                    print(f"[DEBUG-API-OUTPUT] get_google_trends_data response: {json.dumps(data, indent=2)}")
                if 'tasks' in data:
                    for task in data.get('tasks', []):
                        if 'result' in task:
                            for result in task.get('result', []):
                                for keyword in result.get('keywords', []):
                                    results[keyword] = result
                else:
                    print(f"API error: {data.get('status_message')}")
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
        return results

class KeywordExpansionTool(BaseTool):
    name: str = "KeywordExpansionTool"
    description: str = """
    Expands a set of seed keywords using the Google Ads keywords_for_keywords API.
    Calculates CompS score and returns up to the top 1000 keywords based on this score.

    Input: A string of comma-separated keywords.
    Example: "desk gadgets, office accessories, workplace tech"

    Output: A JSON string containing expanded keywords with their CompS scores.
    """
    _client: DataForSEOClient = PrivateAttr()
    _debug: bool = PrivateAttr(default=True)

    def __init__(self, client: DataForSEOClient, debug: bool = True):
        super().__init__()
        self._client = client
        self._debug = debug

    def _run(self, keywords: str) -> str:
        try:
            keyword_list = [k.strip() for k in keywords.split(',')]
            
            if self._debug:
                print(f"[DEBUG-API-INPUT] KeywordExpansionTool input keywords: {keyword_list}")

            data = self._client.get_keywords_for_keywords(keyword_list)
            
            if self._debug:
                total_objects = sum(len(task.get('result', [])) for task in data.get('tasks', []))
                print(f"[DEBUG-API-OUTPUT] KeywordExpansionTool total objects received: {total_objects}")

            processed_data = self._process_keyword_data(data)
            top_keywords = self._select_top_keywords(processed_data, 40)

            return json.dumps(top_keywords, indent=2)
        except Exception as e:
            error_message = f"Error in KeywordExpansionTool: {str(e)}"
            if self._debug:
                print(f"[DEBUG-ERROR] {error_message}")
            return error_message

    def _process_keyword_data(self, data: Dict) -> List[Dict]:
        processed_data = []
        if 'tasks' in data:
            for task in data.get('tasks', []):
                if 'result' in task:
                    for item in task.get('result', []):
                        keyword_data = {
                            'keyword': item.get('keyword'),
                            'competition': item.get('competition'),
                            'competition_index': item.get('competition_index'),
                            'search_volume': item.get('search_volume'),
                            'cpc': item.get('cpc')
                        }
                        keyword_data['compS'] = self._calculate_compS(keyword_data)
                        processed_data.append(keyword_data)
        return processed_data

    def _calculate_compS(self, keyword_data: Dict) -> float:
        # Normalize scores
        sv_norm = min(keyword_data['search_volume'] / 1000, 100) if keyword_data['search_volume'] else 0
        ics_norm = 100 - keyword_data['competition_index'] if keyword_data['competition_index'] is not None else 0
        ms_norm = min(keyword_data['cpc'] * 10, 100) if keyword_data['cpc'] else 0

        # Weights (adjust as needed)
        w_sv, w_ics, w_ms = 0.4, 0.4, 0.2

        # Calculate CompS
        compS = (w_sv * sv_norm) + (w_ics * ics_norm) + (w_ms * ms_norm)
        return round(compS, 2)

    def _select_top_keywords(self, keywords: List[Dict], top_n: int = 1000) -> List[Dict]:
        sorted_keywords = sorted(keywords, key=lambda x: x['compS'], reverse=True)
        return sorted_keywords[:top_n]

class GoogleTrendsDataForSEOTool(BaseTool):
    name: str = "GoogleTrendsDataForSEOTool"
    description: str = """
    Fetches Google Trends data for given keywords using the DataForSEO API.

    Input: A string of comma-separated keywords (up to 5 keywords).
    Example: "desk gadgets, MOFT, Microsoft Surface, ergonomic accessories, smart office"

    Output: A JSON string containing trend data for each keyword.

    IMPORTANT USAGE GUIDELINES:
    1. You can specify up to 5 keywords per API call.
    2. Keywords should be separated by commas.
    3. Limit the total number of calls to this tool to the allowed API call limits.
    """
    _client: DataForSEOClient = PrivateAttr()
    _debug: bool = PrivateAttr(default=True)

    def __init__(self, client: DataForSEOClient, debug: bool = True):
        super().__init__()
        self._client = client
        self._debug = debug

    def _run(self, keywords: str) -> str:
        try:
            keyword_list = [k.strip() for k in keywords.split(',')]
            
            if self._debug:
                print(f"[DEBUG-API-INPUT] GoogleTrendsDataForSEOTool input keywords: {keyword_list}")

            data = self._client.get_google_trends_data(keyword_list)
            
            if self._debug:
                total_objects = len(data)
                print(f"[DEBUG-API-OUTPUT] GoogleTrendsDataForSEOTool total objects received: {total_objects}")

            processed_data = self.process_results(data)

            if self._debug:
                print("[DEBUG-TOOL-OUTPUT] GoogleTrendsDataForSEOTool top 5 processed results:")
                for keyword, result in list(processed_data.items())[:5]:
                    print(f"Keyword: {keyword}")
                    print(json.dumps(result, indent=2))
                    print()

            return json.dumps(processed_data, indent=2)
        except Exception as e:
            error_message = f"Error in GoogleTrendsDataForSEOTool: {str(e)}"
            if self._debug:
                print(f"[DEBUG-ERROR] {error_message}")
            return error_message

    def process_results(self, data: Dict[str, Dict]) -> Dict[str, Dict]:
        processed = {}
        for keyword, result in data.items():
            items = result.get('items', [])
            trends_data = []
            for item in items:
                if item.get('type') == 'google_trends_graph':
                    for data_point in item.get('data', []):
                        trends_data.append({
                            'date_from': data_point.get('date_from'),
                            'date_to': data_point.get('date_to'),
                            'timestamp': data_point.get('timestamp'),
                            'value': data_point.get('value')
                        })
            processed[keyword] = {
                'trends_data': trends_data
            }
        return processed