import os

try:
    from duckduckgo_search import DDGS
    _HAS_DDGS = True
except ImportError:
    _HAS_DDGS = False

class WebSearchAgent:
    def __init__(self, use_tavily=False):
        self.use_tavily = use_tavily
        if use_tavily:
            from tavily import TavilyClient
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise ValueError("TAVILY_API_KEY is not set in environment variables.")
            self.tavily_client = TavilyClient(api_key=api_key)
            
    def search_news(self, query, max_results=5):
        """Searches for recent news regarding the query."""
        print(f"Searching web for: {query}")
        
        if self.use_tavily:
            return self._tavily_search(query, max_results)
        else:
            return self._duckduckgo_search(query, max_results)
            
    def _duckduckgo_search(self, query, max_results):
        results = []
        with DDGS(timeout=10) as ddgs:
            # We use text search because 'news' is sometimes rate limited or unstable
            responses = ddgs.text(f"{query} news today", max_results=max_results)
            for r in responses:
                results.append({
                    "title": r.get('title'),
                    "body": r.get('body'),
                    "url": r.get('href')
                })
        return results
        
    def _tavily_search(self, query, max_results):
        response = self.tavily_client.search(
            query=f"{query} breaking financial news", 
            search_depth="advanced", 
            max_results=max_results
        )
        results = []
        for res in response.get('results', []):
            results.append({
                "title": res.get('title'),
                "body": res.get('content'),
                "url": res.get('url')
            })
        return results

if __name__ == "__main__":
    pass
