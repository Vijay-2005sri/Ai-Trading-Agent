"""
=============================================================================
WEB SEARCH AGENT — Smart News Fetcher with Tavily/DuckDuckGo
=============================================================================
Tavily Conservation Strategy:
  - Normal mode:     DuckDuckGo (free), Tavily 1x per 4hr cycle
  - Pre-Event mode:  Tavily every 2hrs when high-impact event within 4hrs
  - Sniper mode:     Tavily every 2min during Fed chair / major announcements

If Tavily fails (quota exhausted, rate limit), auto-fallback to DuckDuckGo.
=============================================================================
"""

import os

try:
    from ddgs import DDGS
    _HAS_DDGS = True
except ImportError:
    _HAS_DDGS = False

class WebSearchAgent:
    def __init__(self, use_tavily=False):
        self.use_tavily = use_tavily
        self._tavily_client = None
        self._tavily_available = False
        
        if use_tavily:
            self._init_tavily()
    
    def _init_tavily(self):
        """Initialize Tavily client if API key exists."""
        try:
            from tavily import TavilyClient
            api_key = os.getenv("TAVILY_API_KEY")
            if api_key:
                self._tavily_client = TavilyClient(api_key=api_key)
                self._tavily_available = True
        except ImportError:
            self._tavily_available = False
            
    def search_news(self, query, max_results=5):
        """
        Searches for recent news with smart fallback.
        
        If use_tavily=True and Tavily is available:
          → Try Tavily first
          → On ANY failure (quota, rate limit, error) → fallback to DuckDuckGo
        
        If use_tavily=False:
          → Use DuckDuckGo directly (free, unlimited)
        """
        print(f"Searching web for: {query}")
        
        if self.use_tavily and self._tavily_available:
            try:
                return self._tavily_search(query, max_results)
            except Exception as e:
                print(f"    ⚠️  Tavily failed: {e}")
                print(f"    🔄 Falling back to DuckDuckGo (free)...")
                return self._duckduckgo_search(query, max_results)
        else:
            return self._duckduckgo_search(query, max_results)
            
    def _duckduckgo_search(self, query, max_results):
        """Free, unlimited DuckDuckGo search."""
        if not _HAS_DDGS:
            print("    ⚠️  duckduckgo_search not installed. No news available.")
            return []
            
        results = []
        try:
            with DDGS(timeout=10) as ddgs:
                responses = ddgs.text(f"{query} news today", max_results=max_results)
                for r in responses:
                    results.append({
                        "title": r.get('title'),
                        "body": r.get('body'),
                        "url": r.get('href'),
                        "source": "DuckDuckGo"
                    })
        except Exception as e:
            print(f"    ⚠️  DuckDuckGo search error: {e}")
        return results
        
    def _tavily_search(self, query, max_results):
        """Premium Tavily search — better quality, limited credits."""
        if not self._tavily_client:
            self._init_tavily()
            if not self._tavily_client:
                raise RuntimeError("Tavily client not initialized")
        
        response = self._tavily_client.search(
            query=f"{query} breaking financial news", 
            search_depth="advanced", 
            max_results=max_results
        )
        results = []
        for res in response.get('results', []):
            results.append({
                "title": res.get('title'),
                "body": res.get('content'),
                "url": res.get('url'),
                "source": "Tavily"
            })
        return results

if __name__ == "__main__":
    pass
