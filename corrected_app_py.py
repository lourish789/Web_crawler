"""
Flask API Server with Real API Integration
Supports: Serper, Brave, Semantic Scholar, arXiv, PubMed
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import json

app = Flask(__name__)

# FIXED: Proper CORS configuration for production
CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # Allow all origins, or specify: ["https://your-frontend.vercel.app"]
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

@dataclass
class ResearchResult:
    title: str
    url: str
    snippet: str
    source_type: str
    relevance_score: float
    published_date: str = ""
    authors: str = ""

class RealSearchAgent:
    """SearchAgent with real API integrations"""
    
    def __init__(self):
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        self.brave_api_key = os.getenv('BRAVE_API_KEY')
        self.semantic_scholar_api_key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
    
    def search_serper(self, query: str, num_results: int = 10) -> List[Dict]:
        """Serper API (Google Search)"""
        if not self.serper_api_key:
            return []
        
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query, "num": num_results})
        headers = {
            'X-API-KEY': self.serper_api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('organic', [])[:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source_type': 'article',
                    'published_date': item.get('date', '')
                })
            return results
        except Exception as e:
            print(f"Serper error: {e}")
            return []
    
    def search_brave(self, query: str, num_results: int = 10) -> List[Dict]:
        """Brave Search API"""
        if not self.brave_api_key:
            return []
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key
        }
        params = {"q": query, "count": num_results}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('web', {}).get('results', [])[:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('description', ''),
                    'source_type': 'article',
                    'published_date': item.get('age', '')
                })
            return results
        except Exception as e:
            print(f"Brave error: {e}")
            return []
    
    def search_semantic_scholar(self, query: str, num_results: int = 10) -> List[Dict]:
        """Semantic Scholar API - FREE"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {}
        if self.semantic_scholar_api_key:
            headers['x-api-key'] = self.semantic_scholar_api_key
        
        params = {
            'query': query,
            'limit': num_results,
            'fields': 'title,authors,year,abstract,url,publicationDate'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for paper in data.get('data', []):
                authors = ', '.join([author['name'] for author in paper.get('authors', [])[:3]])
                if len(paper.get('authors', [])) > 3:
                    authors += ' et al.'
                
                results.append({
                    'title': paper.get('title', ''),
                    'url': paper.get('url', ''),
                    'snippet': (paper.get('abstract', '')[:300] + '...') if paper.get('abstract') else '',
                    'source_type': 'paper',
                    'published_date': paper.get('publicationDate', '') or str(paper.get('year', '')),
                    'authors': authors
                })
            return results
        except Exception as e:
            print(f"Semantic Scholar error: {e}")
            return []
    
    def search_arxiv(self, query: str, num_results: int = 10) -> List[Dict]:
        """arXiv API - FREE"""
        base_url = 'http://export.arxiv.org/api/query'
        params = {
            'search_query': f'all:{query}',
            'start': 0,
            'max_results': num_results,
            'sortBy': 'relevance'
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            results = []
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                link = entry.find('atom:id', ns).text.strip()
                published = entry.find('atom:published', ns).text.strip()[:10]
                
                authors = [author.find('atom:name', ns).text 
                          for author in entry.findall('atom:author', ns)[:3]]
                authors_str = ', '.join(authors)
                if len(entry.findall('atom:author', ns)) > 3:
                    authors_str += ' et al.'
                
                results.append({
                    'title': title,
                    'url': link,
                    'snippet': summary[:300] + '...',
                    'source_type': 'paper',
                    'published_date': published,
                    'authors': authors_str
                })
            return results
        except Exception as e:
            print(f"arXiv error: {e}")
            return []
    
    def search_pubmed(self, query: str, num_results: int = 10) -> List[Dict]:
        """PubMed API - FREE"""
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': num_results,
            'retmode': 'json'
        }
        
        try:
            search_response = requests.get(search_url, params=search_params, timeout=10)
            search_response.raise_for_status()
            search_data = search_response.json()
            ids = search_data.get('esearchresult', {}).get('idlist', [])
            
            if not ids:
                return []
            
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(ids),
                'retmode': 'json'
            }
            
            fetch_response = requests.get(fetch_url, params=fetch_params, timeout=10)
            fetch_response.raise_for_status()
            fetch_data = fetch_response.json()
            
            results = []
            for pmid in ids:
                paper = fetch_data.get('result', {}).get(pmid, {})
                
                authors = []
                for author in paper.get('authors', [])[:3]:
                    authors.append(author.get('name', ''))
                authors_str = ', '.join(authors)
                if len(paper.get('authors', [])) > 3:
                    authors_str += ' et al.'
                
                results.append({
                    'title': paper.get('title', ''),
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    'snippet': paper.get('source', ''),
                    'source_type': 'paper',
                    'published_date': paper.get('pubdate', ''),
                    'authors': authors_str
                })
            return results
        except Exception as e:
            print(f"PubMed error: {e}")
            return []
    
    def search_all(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search all available sources"""
        all_results = []
        per_source = max(3, num_results // 4)
        
        # Always use free APIs
        print("Searching Semantic Scholar...")
        all_results.extend(self.search_semantic_scholar(query, per_source))
        
        print("Searching arXiv...")
        all_results.extend(self.search_arxiv(query, per_source))
        
        print("Searching PubMed...")
        all_results.extend(self.search_pubmed(query, per_source))
        
        # Use paid APIs if available
        if self.serper_api_key:
            print("Searching with Serper...")
            all_results.extend(self.search_serper(query, per_source))
        elif self.brave_api_key:
            print("Searching with Brave...")
            all_results.extend(self.search_brave(query, per_source))
        
        return all_results

class FilterAgent:
    def calculate_relevance(self, result: Dict, query: str) -> float:
        query_terms = set(query.lower().split())
        title_terms = set(result['title'].lower().split())
        snippet_terms = set(result['snippet'].lower().split())
        
        title_match = len(query_terms & title_terms) / len(query_terms) if query_terms else 0
        snippet_match = len(query_terms & snippet_terms) / len(query_terms) if query_terms else 0
        
        score = (title_match * 0.7 + snippet_match * 0.3)
        
        if result['source_type'] in ['paper', 'report']:
            score *= 1.2
        
        return min(score, 1.0)
    
    def filter_and_rank(self, results: List[Dict], query: str, min_relevance: float = 0.2) -> List[ResearchResult]:
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
        
        research_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return research_results

class SummaryAgent:
    def generate_summary(self, results: List[ResearchResult], query: str) -> Dict[str, Any]:
        if not results:
            return {
                'overview': f'No relevant results found for "{query}".',
                'total_sources': 0,
                'source_breakdown': {},
                'avg_relevance': 0,
                'date_range': ''
            }
        
        source_types = {}
        for result in results:
            source_types[result.source_type] = source_types.get(result.source_type, 0) + 1
        
        dates = [r.published_date for r in results if r.published_date]
        date_range = f"{min(dates)} to {max(dates)}" if dates else "Various dates"
        
        return {
            'overview': f'Found {len(results)} relevant sources on "{query}" from multiple academic and web databases.',
            'total_sources': len(results),
            'source_breakdown': source_types,
            'avg_relevance': sum(r.relevance_score for r in results) / len(results),
            'date_range': date_range
        }

class ResearchOrchestrator:
    def __init__(self):
        self.search_agent = RealSearchAgent()
        self.filter_agent = FilterAgent()
        self.summary_agent = SummaryAgent()
    
    async def research(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        all_results = self.search_agent.search_all(query, num_results * 2)
        filtered_results = self.filter_agent.filter_and_rank(all_results, query)
        summary = self.summary_agent.generate_summary(filtered_results, query)
        
        return {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'results': [asdict(r) for r in filtered_results[:num_results]]
        }

orchestrator = ResearchOrchestrator()

@app.route('/')
def home():
    return jsonify({
        'message': 'AI Research Assistant API with Real Data',
        'version': '2.0',
        'active_sources': {
            'semantic_scholar': True,
            'arxiv': True,
            'pubmed': True,
            'serper': bool(os.getenv('SERPER_API_KEY')),
            'brave': bool(os.getenv('BRAVE_API_KEY'))
        },
        'endpoints': {
            '/api/search': 'POST - Search research content',
            '/health': 'GET - Health check'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        query = data['query'].strip()
        num_results = data.get('num_results', 10)
        
        if len(query) < 3:
            return jsonify({'error': 'Query must be at least 3 characters'}), 400
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(orchestrator.research(query, num_results))
        loop.close()
        
        return jsonify(results)
    
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

# FIXED: Production-ready configuration
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("="*60)
    print("AI Research Assistant API Server (Real APIs)")
    print("="*60)
    print(f"Semantic Scholar: ✓ (FREE)")
    print(f"arXiv: ✓ (FREE)")
    print(f"PubMed: ✓ (FREE)")
    print(f"Serper: {'✓' if os.getenv('SERPER_API_KEY') else '✗'}")
    print(f"Brave: {'✓' if os.getenv('BRAVE_API_KEY') else '✗'}")
    print("="*60)
    print(f"Server running on 0.0.0.0:{port}")
    print("="*60)
    
    # CRITICAL: Use host='0.0.0.0' and debug=False for production
    app.run(host='0.0.0.0', port=port, debug=False)
