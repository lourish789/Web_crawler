"""
AI Research Assistant - Multi-Agent System for Academic Research
This system uses specialized agents to search, analyze, and curate research content
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import requests
from urllib.parse import quote_plus

@dataclass
class ResearchResult:
    """Structure for research results"""
    title: str
    url: str
    snippet: str
    source_type: str  # article, report, paper, website
    relevance_score: float
    published_date: str = ""
    authors: str = ""

class SearchAgent:
    """Agent responsible for searching academic and web sources"""
    
    def __init__(self):
        self.search_apis = {
            'google_scholar': 'https://scholar.google.com/scholar',
            'pubmed': 'https://pubmed.ncbi.nlm.nih.gov',
            'arxiv': 'https://arxiv.org/search',
        }
    
    def search_web(self, query: str, num_results: int = 10) -> List[Dict]:
        """Simulate web search (in production, use actual API like Serper, Brave, etc.)"""
        # This is a mock implementation - replace with actual API calls
        results = []
        
        # Simulate different types of sources
        mock_sources = [
            {
                'title': f'Research on {query}: A Comprehensive Review',
                'url': f'https://example-journal.com/article/{query.replace(" ", "-")}',
                'snippet': f'This comprehensive study examines {query} from multiple perspectives, analyzing recent developments and trends in the field.',
                'source_type': 'article',
                'published_date': '2024-03-15'
            },
            {
                'title': f'{query.title()}: Latest Findings and Implications',
                'url': f'https://research-portal.edu/papers/{query.replace(" ", "-")}',
                'snippet': f'Recent research into {query} reveals significant insights that could transform our understanding of the subject.',
                'source_type': 'paper',
                'published_date': '2024-08-22'
            },
            {
                'title': f'Annual Report on {query}',
                'url': f'https://reports-database.org/{query.replace(" ", "-")}-2024',
                'snippet': f'Comprehensive annual report analyzing trends, statistics, and projections related to {query}.',
                'source_type': 'report',
                'published_date': '2024-01-10'
            },
            {
                'title': f'Understanding {query}: An Expert Guide',
                'url': f'https://academic-resources.com/guides/{query.replace(" ", "-")}',
                'snippet': f'Expert analysis and practical insights into {query}, including methodologies and best practices.',
                'source_type': 'article',
                'published_date': '2024-06-05'
            },
            {
                'title': f'Meta-Analysis of {query} Studies',
                'url': f'https://meta-research.net/analysis/{query.replace(" ", "-")}',
                'snippet': f'A systematic meta-analysis of 50+ studies examining {query}, providing evidence-based conclusions.',
                'source_type': 'paper',
                'published_date': '2024-09-18'
            }
        ]
        
        return mock_sources[:num_results]
    
    def search_academic(self, query: str) -> List[Dict]:
        """Search academic sources specifically"""
        # Mock academic results
        return [
            {
                'title': f'Academic Study: {query}',
                'url': f'https://academic-db.org/study/{query.replace(" ", "-")}',
                'snippet': f'Peer-reviewed academic research investigating {query} with rigorous methodology.',
                'source_type': 'paper',
                'published_date': '2024-04-12',
                'authors': 'Smith, J., Johnson, A., Williams, B.'
            }
        ]

class FilterAgent:
    """Agent responsible for filtering and ranking results"""
    
    def __init__(self):
        self.relevance_keywords = []
    
    def calculate_relevance(self, result: Dict, query: str) -> float:
        """Calculate relevance score based on query match"""
        query_terms = set(query.lower().split())
        title_terms = set(result['title'].lower().split())
        snippet_terms = set(result['snippet'].lower().split())
        
        # Calculate overlap
        title_match = len(query_terms & title_terms) / len(query_terms) if query_terms else 0
        snippet_match = len(query_terms & snippet_terms) / len(query_terms) if query_terms else 0
        
        # Weight title matches higher
        score = (title_match * 0.7 + snippet_match * 0.3)
        
        # Bonus for academic sources
        if result['source_type'] in ['paper', 'report']:
            score *= 1.2
        
        return min(score, 1.0)
    
    def filter_and_rank(self, results: List[Dict], query: str, min_relevance: float = 0.3) -> List[ResearchResult]:
        """Filter and rank results by relevance"""
        research_results = []
        
        for result in results:
            relevance = self.calculate_relevance(result, query)
            
            if relevance >= min_relevance:
                research_results.append(
                    ResearchResult(
                        title=result['title'],
                        url=result['url'],
                        snippet=result['snippet'],
                        source_type=result['source_type'],
                        relevance_score=relevance,
                        published_date=result.get('published_date', ''),
                        authors=result.get('authors', '')
                    )
                )
        
        # Sort by relevance score
        research_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return research_results

class SummaryAgent:
    """Agent responsible for generating summaries and insights"""
    
    def generate_summary(self, results: List[ResearchResult], query: str) -> Dict[str, Any]:
        """Generate a summary of findings"""
        if not results:
            return {
                'overview': f'No relevant results found for "{query}".',
                'total_sources': 0,
                'source_breakdown': {},
                'top_keywords': []
            }
        
        source_types = {}
        for result in results:
            source_types[result.source_type] = source_types.get(result.source_type, 0) + 1
        
        return {
            'overview': f'Found {len(results)} relevant sources on "{query}". The results include a mix of academic papers, articles, and reports from reputable sources.',
            'total_sources': len(results),
            'source_breakdown': source_types,
            'avg_relevance': sum(r.relevance_score for r in results) / len(results),
            'date_range': self._get_date_range(results)
        }
    
    def _get_date_range(self, results: List[ResearchResult]) -> str:
        """Get the date range of results"""
        dates = [r.published_date for r in results if r.published_date]
        if dates:
            return f"{min(dates)} to {max(dates)}"
        return "Various dates"

class ResearchOrchestrator:
    """Main orchestrator that coordinates all agents"""
    
    def __init__(self):
        self.search_agent = SearchAgent()
        self.filter_agent = FilterAgent()
        self.summary_agent = SummaryAgent()
    
    async def research(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Main research pipeline"""
        print(f"[Orchestrator] Starting research for: {query}")
        
        # Step 1: Search multiple sources
        print("[SearchAgent] Searching web sources...")
        web_results = self.search_agent.search_web(query, num_results)
        
        print("[SearchAgent] Searching academic sources...")
        academic_results = self.search_agent.search_academic(query)
        
        # Combine results
        all_results = web_results + academic_results
        
        # Step 2: Filter and rank
        print("[FilterAgent] Filtering and ranking results...")
        filtered_results = self.filter_agent.filter_and_rank(all_results, query)
        
        # Step 3: Generate summary
        print("[SummaryAgent] Generating summary...")
        summary = self.summary_agent.generate_summary(filtered_results, query)
        
        print(f"[Orchestrator] Research complete! Found {len(filtered_results)} results.")
        
        return {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'results': [asdict(r) for r in filtered_results[:num_results]]
        }

# API Endpoint simulation
class ResearchAPI:
    """Simple API wrapper for the research system"""
    
    def __init__(self):
        self.orchestrator = ResearchOrchestrator()
    
    async def search(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """API endpoint for research queries"""
        if not query or len(query.strip()) < 3:
            return {
                'error': 'Query must be at least 3 characters long',
                'results': []
            }
        
        try:
            results = await self.orchestrator.research(query, num_results)
            return results
        except Exception as e:
            return {
                'error': f'Search failed: {str(e)}',
                'results': []
            }

# Example usage
async def main():
    """Example usage of the research assistant"""
    api = ResearchAPI()
    
    # Example research query
    query = "machine learning in healthcare"
    print(f"\n{'='*60}")
    print(f"Research Query: {query}")
    print(f"{'='*60}\n")
    
    results = await api.search(query, num_results=5)
    
    # Display results
    print(f"\n{results['summary']['overview']}\n")
    print(f"Total Sources: {results['summary']['total_sources']}")
    print(f"Source Breakdown: {results['summary']['source_breakdown']}")
    print(f"\nTop Results:\n")
    
    for i, result in enumerate(results['results'], 1):
        print(f"{i}. [{result['source_type'].upper()}] {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Relevance: {result['relevance_score']:.2f}")
        print(f"   {result['snippet'][:150]}...")
        print()

if __name__ == "__main__":
    asyncio.run(main())
