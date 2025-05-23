import requests
import json
from typing import List, Dict, Any, Optional
import arxiv
from semanticscholar import SemanticScholar

class ResearchService:
    """Service for gathering research information from various sources"""
    
    def __init__(self):
        self.arxiv_client = arxiv.Client()
        self.semantic_scholar = SemanticScholar()
    
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
        
    def aggregate_research(self, query: str) -> str:
        """Aggregate research from multiple sources and return a text summary"""
        web_results = self.search_web(query)
        arxiv_results = self.search_arxiv(query)
        scholar_results = self.search_semantic_scholar(query)

        # Extract relevant information from each source
        web_summary = "\n".join([f"{result['title']}: {result['snippet']} ({result['url']})" for result in web_results])
        arxiv_summary = "\n".join([f"{paper['title']} by {', '.join(paper['authors'])}: {paper['summary']} ({paper['url']})" for paper in arxiv_results])
        scholar_summary = "\n".join([f"{paper['title']} by {', '.join(paper['authors'])}: {paper['abstract']} ({paper['url']})" for paper in scholar_results])

        # Combine all summaries into a single text string
        final_text = f"Web Search Results:\n{web_summary}\n\nArXiv Papers:\n{arxiv_summary}\n\nSemantic Scholar Papers:\n{scholar_summary}"

        return final_text