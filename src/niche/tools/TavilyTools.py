from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from crewai_tools import BaseTool
import os
import traceback
from pydantic import PrivateAttr

class AIWebSearch(BaseTool):
    name: str = "AIWebSearch"
    description: str = """
    Performs AI-powered web search using the Tavily Search API, optimized for LLMs and AI agents.

    Input: A single search query string.
    Example: "What happened in the latest burning man floods?"

    Output: A dictionary containing search results with the following structure:
    {
        'query': str,  # The original search query
        'results': List[Dict],  # List of search result dictionaries
        'response_time': float  # Time taken for the search in seconds
    }

    Each result in the 'results' list contains:
    - 'title': str  # Title of the web page
    - 'url': str  # URL of the web page
    - 'content': str  # Relevant content snippet from the page
    - 'score': float  # Relevance score of the result

    Usage tips for AI agents:
    1. Use clear, specific queries to get the most relevant results.
    2. The 'content' field in each result contains the most relevant information.
    3. Results are already ranked by relevance, with the most relevant appearing first.
    4. Use the information from multiple results to cross-reference and verify facts.
    5. The tool handles web scraping and content aggregation, so you can focus on analyzing the provided information.

    Note: This tool is designed for factual information retrieval. For complex research tasks, consider using the results as a starting point and requesting additional searches if needed.
    """
    _debug: bool = PrivateAttr(default=False)
    _tavily_search: TavilySearchAPIWrapper = PrivateAttr()

    def __init__(self, debug: bool = False):
        super().__init__()
        self._debug = debug
        self._tavily_search = TavilySearchAPIWrapper(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    def _run(self, query: str) -> str:
        try:
            if self._debug:
                print(f"[DEBUG-TOOL-INPUT] AIWebSearch input: query={query}")

            results = self._tavily_search.results(
                query,
                max_results=5,
                search_depth="advanced",
                include_answer=True
            )

            if self._debug:
                total_objects = len(results)
                print(f"[DEBUG-API-OUTPUT] AIWebSearch total objects received: {total_objects}")

                print("[DEBUG-TOOL-OUTPUT] AIWebSearch top 5 results:")
                for i, result in enumerate(results[:5], 1):
                    print(f"{i}. {result['title']}")
                    print(f"   URL: {result['url']}")
                    print(f"   Snippet: {result['content'][:100]}...")
                    print()

            output = f"Web search results for '{query}':\n" + "\n".join(
                [f"{i+1}. {r['content']} - {r['url']}" for i, r in enumerate(results)]
            )

            return output

        except Exception as e:
            error_message = f"AIWebSearch error: {str(e)}\n{traceback.format_exc()}"
            if self._debug:
                print(f"[DEBUG-TOOL-ERROR] {error_message}")
            return f"Error: {str(e)}"