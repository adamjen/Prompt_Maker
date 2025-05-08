import os
import requests
import json
from typing import List, Dict, Any, Optional
import arxiv
# from semanticscholar import SemanticScholar # Comment out the direct import

class ResearchService:
    """Service for gathering research information from various sources"""
    
    def __init__(self):
        self.arxiv_client = arxiv.Client()
        self._semantic_scholar = None # Initialize as None
    
    @property
    def semantic_scholar(self):
        """Lazily initialize SemanticScholar"""
        if self._semantic_scholar is None:
            from semanticscholar import SemanticScholar # Import here
            self._semantic_scholar = SemanticScholar()
        return self._semantic_scholar

    def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search the web for information (using a hypothetical search API)"""
        # This would be replaced with an actual search API
        # For example, using SerpAPI, Google Custom Search, or similar
        return [
            {"title": f"Result {i} for {query}", 
             "snippet": f"This is a snippet for result {i}",
             "url": f"https://example.com/{i}"}
            for i in range(1, num_results + 1)
        ]
    
    def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search arXiv for academic papers"""
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for paper in self.arxiv_client.results(search):
            results.append({
                "title": paper.title,
                "authors": [author.name for author in paper.authors],
                "summary": paper.summary,
                "url": paper.pdf_url,
                "published": paper.published.strftime("%Y-%m-%d")
            })
        
        return results
    
    def search_semantic_scholar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for academic papers"""
        papers = self.semantic_scholar.search_paper(query, limit=limit)
        
        results = []
        for paper in papers:
            results.append({
                "title": paper.title,
                "authors": [author.name for author in paper.authors],
                "abstract": paper.abstract,
                "url": paper.url,
                "year": paper.year
            })
        
        return results
        
    class ResearchResult:
        """Standardized research result format containing metadata and snippets"""
        def __init__(self, source: str, title: str, snippet: str, url: str,
                     summary: Optional[str] = None, published: Optional[str] = None,
                     authors: Optional[List[str]] = None):
            self.source = source
            self.title = title
            self.snippet = snippet
            self.url = url
            self.summary = summary
            self.published = published
            self.authors = authors

    def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search the web for information (using a hypothetical search API)"""
        try:
            results = super().search_web(query, num_results)
            return [
                self._format_result(
                    source="web",
                    title=result["title"],
                    snippet=result["snippet"],
                    url=result["url"]
                ) for result in results
            ]
        except Exception as e:
            print(f"Error in web search: {str(e)}")
            return []

    def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search arXiv for academic papers"""
        try:
            results = super().search_arxiv(query, max_results)
            return [
                self._format_result(
                    source="arxiv",
                    title=paper.title,
                    snippet=paper.summary,
                    url=paper.pdf_url,
                    published=paper.published.strftime("%Y-%m-%d"),
                    authors=[author.name for author in paper.authors]
                ) for paper in results
            ]
        except Exception as e:
            print(f"Error in arXiv search: {str(e)}")
            return []

    def search_semantic_scholar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for academic papers"""
        try:
            results = super().search_semantic_scholar(query, limit)
            return [
                self._format_result(
                    source="semantic_scholar",
                    title=paper.title,
                    snippet=paper.abstract,
                    url=paper.url,
                    published=paper.year,
                    authors=[author.name for author in paper.authors]
                ) for paper in results
            ]
        except Exception as e:
            print(f"Error in Semantic Scholar search: {str(e)}")
            return []

    def _format_result(self, source: str, title: str, snippet: str, url: str,
                      published: Optional[str] = None, authors: Optional[List[str]] = None):
        """Helper method to format results consistently"""
        return {
            "source": source,
            "title": title,
            "snippet": snippet,
            "url": url,
            "published": published,
            "authors": authors
        }

    def filter_results(self, results: List[Dict[str, Any]], min_title_length: int = 10,
                      min_snippet_length: int = 20) -> List[Dict[str, Any]]:
        """Filter results based on content length criteria"""
        return [
            result for result in results
            if len(result["title"]) >= min_title_length
            and len(result["snippet"]) >= min_snippet_length
        ]

    def aggregate_research(self, query: str, filter_results: bool = True) -> Dict[str, Any]:
        """Aggregate and process research from multiple sources"""
        try:
            web_results = self.search_web(query)
            arxiv_results = self.search_arxiv(query)
            scholar_results = self.search_semantic_scholar(query)
            
            if filter_results:
                web_results = self.filter_results(web_results)
                arxiv_results = self.filter_results(arxiv_results)
                scholar_results = self.filter_results(scholar_results)

            return {
                "research_results": [
                    {"source": "web", "results": web_results},
                    {"source": "arxiv", "results": arxiv_results},
                    {"source": "semantic_scholar", "results": scholar_results}
                ]
            }
        except Exception as e:
            print(f"Error in aggregation: {str(e)}")
            return {"error": str(e)}
    def integrate_research(self, refined_prompt: str, original_prompt: str, additional_context: str) -> str:
        """Integrate research findings into the refined prompt"""
        try:
            research_results = self.aggregate_research(refined_prompt)
            research_summary = ""
            
            for source in research_results.get("research_results", []):
                research_summary += f"Results from {source['source']}:\n"
                for result in source["results"]:
                    research_summary += f"Title: {result['title']}\nSnippet: {result['snippet']}\nURL: {result['url']}\n\n"
            
            enhanced_prompt = f"{refined_prompt}\n\nResearch Findings:\n{research_summary}"
            return enhanced_prompt
        
        except Exception as e:
            print(f"Error in research integration: {str(e)}")
            return refined_prompt  # Return the refined prompt as is if there's an error

class EXASearchTool:
    """EXA Search API integration tool"""
     
    def __init__(self):
        self.api_key = os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY environment variable is required")
             
    def _run(self, query: str) -> Dict[str, Any]:
        """Execute search using EXA Search API
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary with 'content' and 'source' keys per result
            
        Raises:
            ValueError: For invalid queries
            Exception: For API errors
        """
        # Validate query
        if not query or len(query.strip()) < 3:
            raise ValueError("Search query must be at least 3 characters long")
            
        # Prepare API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Execute search
            response = requests.post(
                "https://api.exa.ai/search",
                json={"query": query},
                headers=headers,
                timeout=10
            )
            
            # Handle API errors
            if response.status_code != 200:
                error_msg = f"EXA API error {response.status_code}: {response.text}"
                raise Exception(error_msg)
                
            # Parse and format results
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                results.append({
                    "content": item.get("text", ""),
                    "source": item.get("url", "")
                })
                
            return {"results": results}
            
        except requests.RequestException as e:
            raise Exception(f"Network error: {str(e)}") from e