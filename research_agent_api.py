"""
Flask API Server for AI Research Assistant
Connects the frontend interface with the multi-agent backend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
from typing import Dict, Any
import sys

# Import the research agent system (assuming it's in research_agents.py)
# from research_agents import ResearchAgentSystem

# For demonstration, we'll include a simplified version
import requests
import arxiv


app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication


class SimpleResearchSystem:
    """Simplified research system for the API"""
    
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    async def search_arxiv(self, query: str, max_results: int = 5):
        """Search arXiv"""
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            results = []
            for paper in client.results(search):
                results.append({
                    "title": paper.title,
                    "url": paper.entry_id,
                    "source": "arXiv",
                    "snippet": paper.summary[:300] + "...",
                    "relevance": 0.90,
                    "citations": 0,
                    "authors": [author.name for author in paper.authors][:3],
                    "published_date": paper.published.strftime("%Y-%m-%d")
                })
            
            return results
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    async def search_pubmed(self, query: str, max_results: int = 5):
        """Search PubMed"""
        try:
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            
            # Search
            search_url = f"{base_url}esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json"
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            search_results = response.json()
            id_list = search_results.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return []
            
            # Fetch details
            fetch_url = f"{base_url}esummary.fcgi"
            params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            }
            
            response = requests.get(fetch_url, params=params, timeout=10)
            fetch_results = response.json()
            
            results = []
            for pmid in id_list:
                article = fetch_results.get("result", {}).get(pmid, {})
                if article:
                    results.append({
                        "title": article.get("title", ""),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "source": "PubMed",
                        "snippet": article.get("title", "")[:300],
                        "relevance": 0.88,
                        "citations": 0,
                        "authors": [a.get("name", "") for a in article.get("authors", [])[:3]]
                    })
            
            return results
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def generate_analysis(self, query: str, results: list) -> Dict[str, Any]:
        """Generate basic analysis"""
        sources = list(set([r["source"] for r in results]))
        
        # Extract keywords
        all_words = []
        for result in results:
            words = result["title"].lower().split()
            all_words.extend([w for w in words if len(w) > 4])
        
        word_freq = {}
        for word in all_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        key_topics = [word.title() for word, _ in top_words]
        
        return {
            "summary": f"Based on your query about '{query}', I found {len(results)} relevant research papers from {len(sources)} academic sources. The research covers various methodologies and applications in this field.",
            "key_topics": key_topics if key_topics else ["Research Methods", "Applications", "Theory", "Analysis", "Data"],
            "recommendations": [
                "Start by reviewing the most recent papers for current developments",
                "Look for papers with the highest relevance scores",
                "Check the original sources for full text and citations"
            ]
        }
    
    async def research(self, query: str) -> Dict[str, Any]:
        """Execute research"""
        # Search multiple sources
        arxiv_results = await self.search_arxiv(query, max_results=5)
        pubmed_results = await self.search_pubmed(query, max_results=5)
        
        all_results = arxiv_results + pubmed_results
        
        # Sort by relevance
        all_results.sort(key=lambda x: x["relevance"], reverse=True)
        
        # Generate analysis
        analysis = self.generate_analysis(query, all_results)
        
        return {
            "query": query,
            "results": all_results,
            "analysis": analysis,
            "total_results": len(all_results)
        }


# Initialize the research system
research_system = SimpleResearchSystem()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "AI Research Assistant API"
    })


@app.route('/api/search', methods=['POST'])
def search():
    """Main search endpoint"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' parameter"
            }), 400
        
        query = data['query']
        
        # Execute research
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(research_system.research(query))
        loop.close()
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get available research sources"""
    return jsonify({
        "sources": [
            {"id": "arxiv", "name": "arXiv", "description": "Open access preprints"},
            {"id": "pubmed", "name": "PubMed", "description": "Biomedical literature"},
            {"id": "google_scholar", "name": "Google Scholar", "description": "Academic papers (requires API key)"}
        ]
    })


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error"
    }), 500


if __name__ == '__main__':
    print("🚀 Starting AI Research Assistant API...")
    print("📡 API will be available at: http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  GET  /health          - Health check")
    print("  POST /api/search      - Search research papers")
    print("  GET  /api/sources     - Get available sources")
    print("\nExample request:")
    print('  curl -X POST http://localhost:5000/api/search \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"query": "machine learning"}\'')
    print("\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
