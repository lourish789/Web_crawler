"""
AI Research Assistant - Multi-Agent System
A comprehensive research assistant using multiple AI agents for searching,
analyzing, and presenting academic content.
"""

import os
import json
import requests
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import anthropic
from serpapi import GoogleSearch
import arxiv


@dataclass
class ResearchResult:
    """Data class for research results"""
    title: str
    url: str
    source: str
    snippet: str
    relevance: float
    citations: int = 0
    authors: List[str] = None
    published_date: str = None


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Execute the agent's main functionality"""
        pass


class SearchAgent(BaseAgent):
    """Agent responsible for searching multiple sources"""
    
    def __init__(self, serpapi_key: str = None):
        super().__init__("SearchAgent")
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY")
    
    def search_google_scholar(self, query: str, max_results: int = 5) -> List[ResearchResult]:
        """Search Google Scholar for academic papers"""
        if not self.serpapi_key:
            return []
        
        try:
            params = {
                "engine": "google_scholar",
                "q": query,
                "api_key": self.serpapi_key,
                "num": max_results
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            papers = []
            for result in results.get("organic_results", [])[:max_results]:
                papers.append(ResearchResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    source="Google Scholar",
                    snippet=result.get("snippet", ""),
                    relevance=0.9,
                    citations=int(result.get("inline_links", {}).get("cited_by", {}).get("total", 0)),
                    authors=[],
                    published_date=result.get("publication_info", {}).get("summary", "")
                ))
            
            return papers
        except Exception as e:
            print(f"Error searching Google Scholar: {e}")
            return []
    
    def search_arxiv(self, query: str, max_results: int = 5) -> List[ResearchResult]:
        """Search arXiv for research papers"""
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            papers = []
            for result in client.results(search):
                papers.append(ResearchResult(
                    title=result.title,
                    url=result.entry_id,
                    source="arXiv",
                    snippet=result.summary[:300] + "...",
                    relevance=0.85,
                    citations=0,
                    authors=[author.name for author in result.authors],
                    published_date=result.published.strftime("%Y-%m-%d")
                ))
            
            return papers
        except Exception as e:
            print(f"Error searching arXiv: {e}")
            return []
    
    def search_pubmed(self, query: str, max_results: int = 5) -> List[ResearchResult]:
        """Search PubMed for medical research papers"""
        try:
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            
            # Search for article IDs
            search_url = f"{base_url}esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json"
            }
            
            response = requests.get(search_url, params=params)
            search_results = response.json()
            
            id_list = search_results.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return []
            
            # Fetch article details
            fetch_url = f"{base_url}esummary.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            }
            
            response = requests.get(fetch_url, params=params)
            fetch_results = response.json()
            
            papers = []
            for pmid in id_list:
                article = fetch_results.get("result", {}).get(pmid, {})
                if article:
                    papers.append(ResearchResult(
                        title=article.get("title", ""),
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        source="PubMed",
                        snippet=article.get("title", "")[:300],
                        relevance=0.88,
                        citations=0,
                        authors=[author.get("name", "") for author in article.get("authors", [])[:3]],
                        published_date=article.get("pubdate", "")
                    ))
            
            return papers
        except Exception as e:
            print(f"Error searching PubMed: {e}")
            return []
    
    async def execute(self, query: str, sources: List[str] = None) -> List[ResearchResult]:
        """Execute multi-source search"""
        if sources is None:
            sources = ["arxiv", "google_scholar", "pubmed"]
        
        all_results = []
        
        if "arxiv" in sources:
            all_results.extend(self.search_arxiv(query, max_results=3))
        
        if "google_scholar" in sources and self.serpapi_key:
            all_results.extend(self.search_google_scholar(query, max_results=3))
        
        if "pubmed" in sources:
            all_results.extend(self.search_pubmed(query, max_results=3))
        
        # Sort by relevance
        all_results.sort(key=lambda x: x.relevance, reverse=True)
        
        return all_results[:10]


class AnalysisAgent(BaseAgent):
    """Agent responsible for analyzing and summarizing research results"""
    
    def __init__(self, claude_api_key: str = None):
        super().__init__("AnalysisAgent")
        self.claude_api_key = claude_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.claude_api_key) if self.claude_api_key else None
    
    async def execute(self, query: str, results: List[ResearchResult]) -> Dict[str, Any]:
        """Analyze research results and provide insights"""
        if not self.client or not results:
            return self._fallback_analysis(query, results)
        
        try:
            # Prepare context for Claude
            context = f"Research Query: {query}\n\n"
            context += "Search Results:\n"
            for i, result in enumerate(results[:5], 1):
                context += f"{i}. {result.title}\n"
                context += f"   Source: {result.source}\n"
                context += f"   Snippet: {result.snippet}\n\n"
            
            # Ask Claude to analyze
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": f"""{context}

Based on these research results, please provide:
1. A concise summary (2-3 sentences) of the research landscape
2. 3-5 key topics or themes
3. 3 specific recommendations for the researcher

Format your response as JSON with keys: summary, key_topics, recommendations"""
                }]
            )
            
            response_text = message.content[0].text
            
            # Try to parse JSON from response
            try:
                # Find JSON in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    analysis = json.loads(response_text[json_start:json_end])
                else:
                    analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # If parsing fails, use fallback
                return self._fallback_analysis(query, results)
            
            return analysis
            
        except Exception as e:
            print(f"Error in analysis: {e}")
            return self._fallback_analysis(query, results)
    
    def _fallback_analysis(self, query: str, results: List[ResearchResult]) -> Dict[str, Any]:
        """Provide basic analysis without AI"""
        sources = list(set([r.source for r in results]))
        
        # Extract common words from titles
        all_words = []
        for result in results:
            words = result.title.lower().split()
            all_words.extend([w for w in words if len(w) > 4])
        
        word_freq = {}
        for word in all_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        top_topics = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        key_topics = [word.capitalize() for word, _ in top_topics]
        
        return {
            "summary": f"Found {len(results)} relevant research papers across {len(sources)} sources. The results cover various aspects of {query} with different methodological approaches and applications.",
            "key_topics": key_topics if key_topics else ["Research Methodology", "Applications", "Theory", "Analysis"],
            "recommendations": [
                f"Start with the highest-cited papers from {sources[0] if sources else 'academic sources'}",
                "Review recent publications (last 2 years) for cutting-edge developments",
                "Look for systematic reviews or meta-analyses for comprehensive overviews"
            ]
        }


class RankingAgent(BaseAgent):
    """Agent responsible for ranking and filtering results"""
    
    def __init__(self):
        super().__init__("RankingAgent")
    
    async def execute(self, results: List[ResearchResult], criteria: str = "relevance") -> List[ResearchResult]:
        """Rank results based on specified criteria"""
        if criteria == "relevance":
            return sorted(results, key=lambda x: x.relevance, reverse=True)
        elif criteria == "citations":
            return sorted(results, key=lambda x: x.citations, reverse=True)
        elif criteria == "date":
            return sorted(results, key=lambda x: x.published_date or "", reverse=True)
        else:
            return results


class ResearchAgentSystem:
    """Main orchestrator for the multi-agent research system"""
    
    def __init__(self, serpapi_key: str = None, claude_api_key: str = None):
        self.search_agent = SearchAgent(serpapi_key)
        self.analysis_agent = AnalysisAgent(claude_api_key)
        self.ranking_agent = RankingAgent()
    
    async def research(self, query: str, sources: List[str] = None, 
                      ranking_criteria: str = "relevance") -> Dict[str, Any]:
        """Execute full research pipeline"""
        print(f"🔍 Searching for: {query}")
        
        # Step 1: Search
        results = await self.search_agent.execute(query, sources)
        print(f"✅ Found {len(results)} results")
        
        # Step 2: Rank
        ranked_results = await self.ranking_agent.execute(results, ranking_criteria)
        print(f"📊 Ranked results by {ranking_criteria}")
        
        # Step 3: Analyze
        analysis = await self.analysis_agent.execute(query, ranked_results)
        print(f"🤖 Generated analysis")
        
        return {
            "query": query,
            "results": [asdict(r) for r in ranked_results],
            "analysis": analysis,
            "total_results": len(ranked_results)
        }


# Example usage
async def main():
    """Example usage of the research agent system"""
    # Initialize system (add your API keys)
    system = ResearchAgentSystem(
        serpapi_key=os.getenv("SERPAPI_KEY"),  # Optional
        claude_api_key=os.getenv("ANTHROPIC_API_KEY")  # Optional
    )
    
    # Perform research
    results = await system.research(
        query="machine learning in healthcare",
        sources=["arxiv", "pubmed"],
        ranking_criteria="relevance"
    )
    
    # Display results
    print("\n" + "="*80)
    print(f"RESEARCH RESULTS FOR: {results['query']}")
    print("="*80 + "\n")
    
    print("📝 ANALYSIS:")
    print(f"Summary: {results['analysis']['summary']}\n")
    print(f"Key Topics: {', '.join(results['analysis']['key_topics'])}\n")
    print("Recommendations:")
    for i, rec in enumerate(results['analysis']['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print("\n" + "="*80)
    print(f"PAPERS ({results['total_results']} found):")
    print("="*80 + "\n")
    
    for i, paper in enumerate(results['results'][:5], 1):
        print(f"{i}. {paper['title']}")
        print(f"   Source: {paper['source']} | Citations: {paper['citations']}")
        print(f"   URL: {paper['url']}")
        print(f"   {paper['snippet'][:150]}...")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
