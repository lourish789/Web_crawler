"""
Flask API Server with Expanded Sources & RAG Integration
Sources: Google Scholar, News, Substack, Archives, Academic DBs
AI: Google Gemini Flash 2.5 for summarization
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import json
import time
from urllib.parse import quote_plus
import google.generativeai as genai
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')

@dataclass
class ResearchResult:
    title: str
    url: str
    snippet: str
    source_type: str
    relevance_score: float
    published_date: str = ""
    authors: str = ""
    ai_summary: str = ""
    relevance_explanation: str = ""
    content_preview: str = ""
    source_name: str = ""

class EnhancedSearchAgent:
    """Multi-source search agent with expanded coverage"""
    
    def __init__(self):
        self.serper_api_key = os.getenv('SERPER_API_KEY')
        self.brave_api_key = os.getenv('BRAVE_API_KEY')
        self.semantic_scholar_api_key = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_google_scholar(self, query: str, num_results: int = 10) -> List[Dict]:
        """Google Scholar via Serper or Brave"""
        if not self.serper_api_key:
            return []
        
        url = "https://google.serper.dev/scholar"
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
                    'source_type': 'academic',
                    'source_name': 'Google Scholar',
                    'published_date': item.get('year', ''),
                    'authors': item.get('publication', '')
                })
            return results
        except Exception as e:
            print(f"Google Scholar error: {e}")
            return []
    
    def search_google_news(self, query: str, num_results: int = 10) -> List[Dict]:
        """Google News via Serper"""
        if not self.serper_api_key:
            return []
        
        url = "https://google.serper.dev/news"
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
            for item in data.get('news', [])[:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source_type': 'news',
                    'source_name': item.get('source', 'News'),
                    'published_date': item.get('date', '')
                })
            return results
        except Exception as e:
            print(f"Google News error: {e}")
            return []
    
    def search_newsapi(self, query: str, num_results: int = 10) -> List[Dict]:
        """NewsAPI - Multiple news sources"""
        if not self.newsapi_key:
            return []
        
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'pageSize': num_results,
            'sortBy': 'relevancy',
            'language': 'en',
            'apiKey': self.newsapi_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for article in data.get('articles', [])[:num_results]:
                results.append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'snippet': article.get('description', '') or article.get('content', ''),
                    'source_type': 'news',
                    'source_name': article.get('source', {}).get('name', 'News'),
                    'published_date': article.get('publishedAt', '')[:10],
                    'authors': article.get('author', '')
                })
            return results
        except Exception as e:
            print(f"NewsAPI error: {e}")
            return []
    
    def search_substack(self, query: str, num_results: int = 10) -> List[Dict]:
        """Substack articles via web search"""
        if not self.serper_api_key:
            return []
        
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": f"{query} site:substack.com",
            "num": num_results
        })
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
                    'source_type': 'blog',
                    'source_name': 'Substack',
                    'published_date': item.get('date', '')
                })
            return results
        except Exception as e:
            print(f"Substack error: {e}")
            return []
    
    def search_medium(self, query: str, num_results: int = 10) -> List[Dict]:
        """Medium articles via web search"""
        if not self.serper_api_key:
            return []
        
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": f"{query} site:medium.com",
            "num": num_results
        })
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
                    'source_type': 'blog',
                    'source_name': 'Medium',
                    'published_date': item.get('date', '')
                })
            return results
        except Exception as e:
            print(f"Medium error: {e}")
            return []
    
    def search_internet_archive(self, query: str, num_results: int = 10) -> List[Dict]:
        """Internet Archive search"""
        url = "https://archive.org/advancedsearch.php"
        params = {
            'q': query,
            'rows': num_results,
            'page': 1,
            'output': 'json',
            'fl[]': ['identifier', 'title', 'description', 'date', 'creator']
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get('response', {}).get('docs', [])[:num_results]:
                identifier = item.get('identifier', '')
                results.append({
                    'title': item.get('title', ''),
                    'url': f"https://archive.org/details/{identifier}",
                    'snippet': item.get('description', [''])[0] if isinstance(item.get('description'), list) else item.get('description', ''),
                    'source_type': 'archive',
                    'source_name': 'Internet Archive',
                    'published_date': item.get('date', ''),
                    'authors': item.get('creator', [''])[0] if isinstance(item.get('creator'), list) else item.get('creator', '')
                })
            return results
        except Exception as e:
            print(f"Internet Archive error: {e}")
            return []
    
    def search_semantic_scholar(self, query: str, num_results: int = 10) -> List[Dict]:
        """Semantic Scholar API"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        headers = {}
        if self.semantic_scholar_api_key:
            headers['x-api-key'] = self.semantic_scholar_api_key
        
        params = {
            'query': query,
            'limit': num_results,
            'fields': 'title,authors,year,abstract,url,publicationDate,venue'
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
                    'source_type': 'academic',
                    'source_name': paper.get('venue', 'Semantic Scholar'),
                    'published_date': paper.get('publicationDate', '') or str(paper.get('year', '')),
                    'authors': authors
                })
            return results
        except Exception as e:
            print(f"Semantic Scholar error: {e}")
            return []
    
    def search_arxiv(self, query: str, num_results: int = 10) -> List[Dict]:
        """arXiv API"""
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
                    'source_type': 'academic',
                    'source_name': 'arXiv',
                    'published_date': published,
                    'authors': authors_str
                })
            return results
        except Exception as e:
            print(f"arXiv error: {e}")
            return []
    
    def search_pubmed(self, query: str, num_results: int = 10) -> List[Dict]:
        """PubMed API"""
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
                    'source_type': 'academic',
                    'source_name': 'PubMed',
                    'published_date': paper.get('pubdate', ''),
                    'authors': authors_str
                })
            return results
        except Exception as e:
            print(f"PubMed error: {e}")
            return []
    
    def search_general_web(self, query: str, num_results: int = 10) -> List[Dict]:
        """General web search via Serper or Brave"""
        if self.serper_api_key:
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
                        'source_type': 'web',
                        'source_name': 'Web',
                        'published_date': item.get('date', '')
                    })
                return results
            except Exception as e:
                print(f"General web search error: {e}")
                return []
        
        elif self.brave_api_key:
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
                        'source_type': 'web',
                        'source_name': 'Web',
                        'published_date': item.get('age', '')
                    })
                return results
            except Exception as e:
                print(f"Brave search error: {e}")
                return []
        
        return []
    
    def search_all_sources(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search across all available sources"""
        all_results = []
        per_source = max(2, num_results // 8)
        
        print(f"🔍 Searching across multiple sources for: {query}")
        
        # Academic sources
        print("📚 Searching academic sources...")
        all_results.extend(self.search_semantic_scholar(query, per_source))
        all_results.extend(self.search_arxiv(query, per_source))
        all_results.extend(self.search_pubmed(query, per_source))
        all_results.extend(self.search_google_scholar(query, per_source))
        
        # News sources
        print("📰 Searching news sources...")
        all_results.extend(self.search_google_news(query, per_source))
        all_results.extend(self.search_newsapi(query, per_source))
        
        # Blog platforms
        print("📝 Searching blogs...")
        all_results.extend(self.search_substack(query, per_source))
        all_results.extend(self.search_medium(query, per_source))
        
        # Archives
        print("🗄️ Searching archives...")
        all_results.extend(self.search_internet_archive(query, per_source))
        
        # General web
        print("🌐 Searching general web...")
        all_results.extend(self.search_general_web(query, per_source))
        
        print(f"✅ Found {len(all_results)} total results")
        return all_results

class GeminiRAGAgent:
    """RAG Agent using Google Gemini Flash 2.5"""
    
    def __init__(self):
        self.model = model if GEMINI_API_KEY else None
    
    def generate_summary_and_relevance(self, result: Dict, query: str) -> tuple:
        """Generate AI summary and relevance explanation using Gemini"""
        if not self.model:
            return ("Summary unavailable - Gemini API key not configured", 
                   "Relevance assessment unavailable")
        
        try:
            prompt = f"""Analyze this search result in relation to the query: "{query}"

ARTICLE DETAILS:
Title: {result['title']}
Source: {result.get('source_name', 'Unknown')}
Snippet: {result['snippet']}
Type: {result['source_type']}

TASK:
1. Write a concise 2-3 sentence summary of what this article is about
2. Explain in 1-2 sentences why this article is relevant (or not) to the query "{query}"

FORMAT YOUR RESPONSE AS:
SUMMARY: [your summary here]
RELEVANCE: [your relevance explanation here]

Be specific, analytical, and honest about relevance."""

            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Parse response
            summary = ""
            relevance = ""
            
            if "SUMMARY:" in text and "RELEVANCE:" in text:
                parts = text.split("RELEVANCE:")
                summary = parts[0].replace("SUMMARY:", "").strip()
                relevance = parts[1].strip()
            else:
                # Fallback parsing
                lines = text.split('\n')
                summary = ' '.join(lines[:3]).strip()
                relevance = ' '.join(lines[3:]).strip()
            
            return (summary[:500], relevance[:300])
        
        except Exception as e:
            print(f"Gemini error: {e}")
            return (f"Summary: {result['snippet'][:200]}...", 
                   "AI relevance assessment unavailable")
    
    def batch_process_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Process multiple results with AI summaries"""
        print(f"🤖 Generating AI summaries with Gemini Flash 2.5...")
        
        enhanced_results = []
        for i, result in enumerate(results):
            print(f"Processing {i+1}/{len(results)}...")
            
            summary, relevance = self.generate_summary_and_relevance(result, query)
            
            result['ai_summary'] = summary
            result['relevance_explanation'] = relevance
            
            enhanced_results.append(result)
            
            # Rate limiting
            time.sleep(0.5)
        
        return enhanced_results

class EnhancedFilterAgent:
    """Advanced filtering with multiple signals"""
    
    def calculate_relevance(self, result: Dict, query: str) -> float:
        """Calculate relevance score with multiple factors"""
        query_terms = set(query.lower().split())
        title_terms = set(result['title'].lower().split())
        snippet_terms = set(result['snippet'].lower().split())
        
        # Text matching
        title_match = len(query_terms & title_terms) / len(query_terms) if query_terms else 0
        snippet_match = len(query_terms & snippet_terms) / len(query_terms) if query_terms else 0
        
        base_score = (title_match * 0.6 + snippet_match * 0.4)
        
        # Source type bonuses
        source_multipliers = {
            'academic': 1.3,
            'paper': 1.3,
            'news': 1.1,
            'blog': 1.0,
            'archive': 0.9,
            'web': 0.8
        }
        
        source_type = result.get('source_type', 'web')
        base_score *= source_multipliers.get(source_type, 1.0)
        
        # Recency bonus (within last year)
        try:
            date_str = result.get('published_date', '')
            if date_str:
                # Parse various date formats
                for fmt in ['%Y-%m-%d', '%Y-%m', '%Y', '%Y/%m/%d']:
                    try:
                        pub_date = datetime.strptime(date_str[:10], fmt)
                        days_old = (datetime.now() - pub_date).days
                        if days_old < 365:
                            recency_bonus = 1.1
                        elif days_old < 730:
                            recency_bonus = 1.05
                        else:
                            recency_bonus = 1.0
                        base_score *= recency_bonus
                        break
                    except:
                        continue
        except:
            pass
        
        return min(base_score, 1.0)
    
    def filter_and_rank(self, results: List[Dict], query: str, min_relevance: float = 0.15) -> List[ResearchResult]:
        """Filter and rank with enhanced criteria"""
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
                        source_name=result.get('source_name', ''),
                        relevance_score=relevance,
                        published_date=result.get('published_date', ''),
                        authors=result.get('authors', ''),
                        ai_summary=result.get('ai_summary', ''),
                        relevance_explanation=result.get('relevance_explanation', ''),
                        content_preview=result.get('snippet', '')[:200]
                    )
                )
        
        # Sort by relevance
        research_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return research_results

class EnhancedSummaryAgent:
    """Generate comprehensive research summary"""
    
    def generate_summary(self, results: List[ResearchResult], query: str) -> Dict[str, Any]:
        if not results:
            return {
                'overview': f'No relevant results found for "{query}".',
                'total_sources': 0,
                'source_breakdown': {},
                'source_type_breakdown': {},
                'avg_relevance': 0,
                'date_range': '',
                'top_sources': []
            }
        
        # Source breakdowns
        source_types = {}
        source_names = {}
        for result in results:
            source_types[result.source_type] = source_types.get(result.source_type, 0) + 1
            if result.source_name:
                source_names[result.source_name] = source_names.get(result.source_name, 0) + 1
        
        # Date range
        dates = [r.published_date for r in results if r.published_date]
        date_range = f"{min(dates)} to {max(dates)}" if dates else "Various dates"
        
        # Top sources
        top_sources = sorted(source_names.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'overview': f'Found {len(results)} highly relevant sources on "{query}" across academic databases, news outlets, blogs, and archives.',
            'total_sources': len(results),
            'source_breakdown': source_names,
            'source_type_breakdown': source_types,
            'avg_relevance': round(sum(r.relevance_score for r in results) / len(results), 3),
            'date_range': date_range,
            'top_sources': [{'name': name, 'count': count} for name, count in top_sources]
        }

class EnhancedResearchOrchestrator:
    """Orchestrate multi-source research with RAG"""
    
    def __init__(self):
        self.search_agent = EnhancedSearchAgent()
        self.rag_agent = GeminiRAGAgent()
        self.filter_agent = EnhancedFilterAgent()
        self.summary_agent = EnhancedSummaryAgent()
    
    async def research(self, query: str, num_results: int = 15) -> Dict[str, Any]:
        print(f"\n{'='*60}")
        print(f"🔬 Starting enhanced research: {query}")
        print(f"{'='*60}\n")
        
        # Step 1: Multi-source search
        all_results = self.search_agent.search_all_sources(query, num_results * 3)
        print(f"\n✅ Collected {len(all_results)} raw results\n")
        
        # Step 2: AI Enhancement with RAG
        if all_results and GEMINI_API_KEY:
            # Process top results with AI
            top_results = all_results[:min(num_results * 2, len(all_results))]
            enhanced_results = self.rag_agent.batch_process_results(top_results, query)
            
            # Merge with remaining results
            all_results = enhanced_results + all_results[len(enhanced_results):]
        
        # Step 3: Filter and rank
        filtered_results = self.filter_agent.filter_and_rank(all_results, query)
        print(f"\n✅ Filtered to {len(filtered_results)} relevant results\n")
        
        # Step 4: Generate summary
        summary = self.summary_agent.generate_summary(filtered_results[:num_results], query)
        
        print(f"{'='*60}")
        print(f"✨ Research complete!")
        print(f"{'='*60}\n")
        
        return {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'results': [asdict(r) for r in filtered_results[:num_results]],
            'ai_powered': bool(GEMINI_API_KEY)
        }

orchestrator = EnhancedResearchOrchestrator()

@app.route('/')
def home():
    return jsonify({
        'message': 'Enhanced AI Research Assistant with RAG',
        'version': '3.0',
        'features': [
            'Multi-source search (Academic, News, Blogs, Archives)',
            'AI-powered summaries via Gemini Flash 2.5',
            'Intelligent relevance scoring',
            'RAG-enhanced analysis'
        ],
        'active_sources': {
            'semantic_scholar': True,
            'arxiv': True,
            'pubmed': True,
            'google_scholar': bool(os.getenv('SERPER_API_KEY')),
            'google_news': bool(os.getenv('SERPER_API_KEY')),
            'newsapi': bool(os.getenv('NEWSAPI_KEY')),
            'substack': bool(os.getenv('SERPER_API_KEY')),
            'medium': bool(os.getenv('SERPER_API_KEY')),
            'internet_archive': True,
            'general_web': bool(os.getenv('SERPER_API_KEY') or os.getenv('BRAVE_API_KEY')),
            'gemini_rag': bool(os.getenv('GEMINI_API_KEY'))
        },
        'endpoints': {
            '/api/search': 'POST - Comprehensive research search',
            '/api/sources': 'GET - List available sources',
            '/health': 'GET - Health check'
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'gemini_configured': bool(GEMINI_API_KEY),
        'sources_available': sum([
            bool(os.getenv('SERPER_API_KEY')),
            bool(os.getenv('BRAVE_API_KEY')),
            bool(os.getenv('NEWSAPI_KEY')),
            True,  # Free APIs always available
        ])
    })

@app.route('/api/sources')
def list_sources():
    """List all available search sources"""
    sources = {
        'academic': [
            {'name': 'Semantic Scholar', 'status': 'active', 'free': True},
            {'name': 'arXiv', 'status': 'active', 'free': True},
            {'name': 'PubMed', 'status': 'active', 'free': True},
            {'name': 'Google Scholar', 'status': 'active' if os.getenv('SERPER_API_KEY') else 'inactive', 'free': False}
        ],
        'news': [
            {'name': 'Google News', 'status': 'active' if os.getenv('SERPER_API_KEY') else 'inactive', 'free': False},
            {'name': 'NewsAPI', 'status': 'active' if os.getenv('NEWSAPI_KEY') else 'inactive', 'free': False}
        ],
        'blogs': [
            {'name': 'Substack', 'status': 'active' if os.getenv('SERPER_API_KEY') else 'inactive', 'free': False},
            {'name': 'Medium', 'status': 'active' if os.getenv('SERPER_API_KEY') else 'inactive', 'free': False}
        ],
        'archives': [
            {'name': 'Internet Archive', 'status': 'active', 'free': True}
        ],
        'web': [
            {'name': 'General Web Search', 'status': 'active' if (os.getenv('SERPER_API_KEY') or os.getenv('BRAVE_API_KEY')) else 'inactive', 'free': False}
        ],
        'ai': [
            {'name': 'Gemini Flash 2.5 RAG', 'status': 'active' if GEMINI_API_KEY else 'inactive', 'free': False}
        ]
    }
    
    return jsonify({
        'sources': sources,
        'total_active': sum(1 for category in sources.values() for source in category if source['status'] == 'active')
    })

@app.route('/api/search', methods=['POST'])
def search():
    """Enhanced search endpoint with RAG"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        query = data['query'].strip()
        num_results = data.get('num_results', 15)
        
        if len(query) < 3:
            return jsonify({'error': 'Query must be at least 3 characters'}), 400
        
        if num_results > 50:
            return jsonify({'error': 'Maximum 50 results allowed'}), 400
        
        # Run async research
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(orchestrator.research(query, num_results))
        loop.close()
        
        return jsonify(results)
    
    except Exception as e:
        print(f"Search error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/api/search/academic', methods=['POST'])
def search_academic_only():
    """Search only academic sources"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        num_results = data.get('num_results', 10)
        
        if len(query) < 3:
            return jsonify({'error': 'Query must be at least 3 characters'}), 400
        
        agent = EnhancedSearchAgent()
        results = []
        results.extend(agent.search_semantic_scholar(query, num_results // 3))
        results.extend(agent.search_arxiv(query, num_results // 3))
        results.extend(agent.search_pubmed(query, num_results // 3))
        
        # Apply RAG if available
        if GEMINI_API_KEY and results:
            rag = GeminiRAGAgent()
            results = rag.batch_process_results(results[:num_results], query)
        
        filter_agent = EnhancedFilterAgent()
        filtered = filter_agent.filter_and_rank(results, query)
        
        return jsonify({
            'query': query,
            'source_filter': 'academic',
            'results': [asdict(r) for r in filtered[:num_results]]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/news', methods=['POST'])
def search_news_only():
    """Search only news sources"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        num_results = data.get('num_results', 10)
        
        if len(query) < 3:
            return jsonify({'error': 'Query must be at least 3 characters'}), 400
        
        agent = EnhancedSearchAgent()
        results = []
        results.extend(agent.search_google_news(query, num_results // 2))
        results.extend(agent.search_newsapi(query, num_results // 2))
        
        # Apply RAG if available
        if GEMINI_API_KEY and results:
            rag = GeminiRAGAgent()
            results = rag.batch_process_results(results[:num_results], query)
        
        filter_agent = EnhancedFilterAgent()
        filtered = filter_agent.filter_and_rank(results, query)
        
        return jsonify({
            'query': query,
            'source_filter': 'news',
            'results': [asdict(r) for r in filtered[:num_results]]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("\n" + "="*70)
    print("🚀 ENHANCED AI RESEARCH ASSISTANT API SERVER v3.0")
    print("="*70)
    print("\n📚 ACADEMIC SOURCES:")
    print(f"  ✓ Semantic Scholar (FREE)")
    print(f"  ✓ arXiv (FREE)")
    print(f"  ✓ PubMed (FREE)")
    print(f"  {'✓' if os.getenv('SERPER_API_KEY') else '✗'} Google Scholar")
    
    print("\n📰 NEWS SOURCES:")
    print(f"  {'✓' if os.getenv('SERPER_API_KEY') else '✗'} Google News")
    print(f"  {'✓' if os.getenv('NEWSAPI_KEY') else '✗'} NewsAPI")
    
    print("\n📝 BLOG PLATFORMS:")
    print(f"  {'✓' if os.getenv('SERPER_API_KEY') else '✗'} Substack")
    print(f"  {'✓' if os.getenv('SERPER_API_KEY') else '✗'} Medium")
    
    print("\n🗄️ ARCHIVES:")
    print(f"  ✓ Internet Archive (FREE)")
    
    print("\n🌐 WEB SEARCH:")
    print(f"  {'✓' if os.getenv('SERPER_API_KEY') else '✗'} Serper (Google)")
    print(f"  {'✓' if os.getenv('BRAVE_API_KEY') else '✗'} Brave Search")
    
    print("\n🤖 AI ENHANCEMENT:")
    print(f"  {'✓' if GEMINI_API_KEY else '✗'} Gemini Flash 2.5 RAG")
    
    print("\n" + "="*70)
    print(f"🌍 Server running on http://0.0.0.0:{port}")
    print("="*70)
    
    print("\n📋 ENDPOINTS:")
    print(f"  • GET  /           - API information")
    print(f"  • GET  /health     - Health check")
    print(f"  • GET  /api/sources - List all sources")
    print(f"  • POST /api/search - Comprehensive search (all sources)")
    print(f"  • POST /api/search/academic - Academic sources only")
    print(f"  • POST /api/search/news - News sources only")
    
    print("\n🔧 ENVIRONMENT VARIABLES:")
    print(f"  • GEMINI_API_KEY: {'✓ Configured' if GEMINI_API_KEY else '✗ Not set'}")
    print(f"  • SERPER_API_KEY: {'✓ Configured' if os.getenv('SERPER_API_KEY') else '✗ Not set'}")
    print(f"  • BRAVE_API_KEY: {'✓ Configured' if os.getenv('BRAVE_API_KEY') else '✗ Not set'}")
    print(f"  • NEWSAPI_KEY: {'✓ Configured' if os.getenv('NEWSAPI_KEY') else '✗ Not set'}")
    print(f"  • SEMANTIC_SCHOLAR_API_KEY: {'✓ Configured' if os.getenv('SEMANTIC_SCHOLAR_API_KEY') else '✗ Not set (optional)'}")
    
    print("\n" + "="*70 + "\n")
    
    # Run server
    app.run(host='0.0.0.0', port=port, debug=False)