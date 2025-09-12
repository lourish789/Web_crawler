// server.js
const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize Google Gemini AI
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

// In-memory storage (replace with database in production)
const users = new Map();
const researchCache = new Map();

// JWT Secret
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

// Middleware to verify JWT token
const verifyToken = (req, res, next) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.userId = decoded.userId;
    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

// Google Custom Search function
async function googleSearch(query, numResults = 10) {
  try {
    const response = await axios.get('https://www.googleapis.com/customsearch/v1', {
      params: {
        key: process.env.GOOGLE_API_KEY,
        cx: process.env.GOOGLE_SEARCH_ENGINE_ID,
        q: query,
        num: numResults
      }
    });
    
    return response.data.items || [];
  } catch (error) {
    console.error('Google Search API Error:', error.response?.data || error.message);
    return [];
  }
}

// Alternative search using SerpApi (if Google Custom Search quota exceeded)
async function serpApiSearch(query, numResults = 10) {
  try {
    const response = await axios.get('https://serpapi.com/search.json', {
      params: {
        api_key: process.env.SERPAPI_KEY,
        engine: 'google',
        q: query,
        num: numResults
      }
    });
    
    return response.data.organic_results || [];
  } catch (error) {
    console.error('SerpApi Error:', error.response?.data || error.message);
    return [];
  }
}

// Web scraping function to get page metadata
async function getPageMetadata(url) {
  try {
    const response = await axios.get(url, {
      timeout: 5000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });
    
    const html = response.data;
    
    // Extract basic metadata using regex (simple approach)
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    const descMatch = html.match(/<meta[^>]*name=["']description["'][^>]*content=["']([^"']+)["']/i);
    
    return {
      title: titleMatch ? titleMatch[1].trim() : 'No title',
      description: descMatch ? descMatch[1].trim() : 'No description available',
      domain: new URL(url).hostname
    };
  } catch (error) {
    console.error('Metadata extraction error for', url, ':', error.message);
    return {
      title: 'Unable to fetch title',
      description: 'Unable to fetch description',
      domain: new URL(url).hostname
    };
  }
}

// AI Research Agent
class ResearchAgent {
  constructor() {
    this.model = genAI.getGenerativeModel({ model: 'gemini-pro' });
  }

  async analyzeQuery(userQuery) {
    const prompt = `
    Analyze this research query and extract:
    1. Main topic/subject
    2. Research intent (academic, news, general info, etc.)
    3. 3-5 specific search queries that would find relevant sources
    4. Suggested content types (articles, reports, studies, news)

    Query: "${userQuery}"

    Respond in JSON format:
    {
      "mainTopic": "...",
      "researchIntent": "...",
      "searchQueries": [...],
      "contentTypes": [...]
    }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const text = response.text();
      
      // Clean up the response to extract JSON
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
      
      // Fallback if JSON parsing fails
      return {
        mainTopic: userQuery,
        researchIntent: "general",
        searchQueries: [userQuery],
        contentTypes: ["articles", "reports"]
      };
    } catch (error) {
      console.error('Query analysis error:', error);
      return {
        mainTopic: userQuery,
        researchIntent: "general",
        searchQueries: [userQuery],
        contentTypes: ["articles", "reports"]
      };
    }
  }

  async filterAndRankSources(sources, originalQuery) {
    // Basic filtering for credible sources
    const credibleDomains = [
      'edu', 'gov', 'org', 'scholar.google.com', 'researchgate.net',
      'arxiv.org', 'pubmed.ncbi.nlm.nih.gov', 'nature.com', 'science.org',
      'bbc.com', 'reuters.com', 'ap.org', 'npr.org', 'pbs.org'
    ];
    
    const filtered = sources.filter(source => {
      const domain = source.domain || source.displayLink || '';
      return credibleDomains.some(credible => domain.includes(credible)) ||
             !domain.includes('.com') || // Prefer non-commercial domains
             source.title.toLowerCase().includes('research') ||
             source.title.toLowerCase().includes('study') ||
             source.title.toLowerCase().includes('report');
    });

    // If we have filtered results, use them; otherwise use all sources
    const finalSources = filtered.length > 0 ? filtered : sources;

    // Sort by relevance (basic keyword matching)
    const keywords = originalQuery.toLowerCase().split(' ');
    
    return finalSources.sort((a, b) => {
      const aScore = keywords.reduce((score, keyword) => {
        const titleMatch = (a.title || '').toLowerCase().includes(keyword) ? 2 : 0;
        const descMatch = (a.snippet || a.description || '').toLowerCase().includes(keyword) ? 1 : 0;
        return score + titleMatch + descMatch;
      }, 0);

      const bScore = keywords.reduce((score, keyword) => {
        const titleMatch = (b.title || '').toLowerCase().includes(keyword) ? 2 : 0;
        const descMatch = (b.snippet || b.description || '').toLowerCase().includes(keyword) ? 1 : 0;
        return score + titleMatch + descMatch;
      }, 0);

      return bScore - aScore;
    });
  }

  async generateResponse(sources, originalQuery) {
    const sourcesText = sources.slice(0, 5).map((source, idx) => 
      `${idx + 1}. ${source.title} - ${source.snippet || source.description}`
    ).join('\n');

    const prompt = `
    Based on these search results, provide a helpful research summary for the query: "${originalQuery}"

    Search Results:
    ${sourcesText}

    Provide a concise, informative response that:
    1. Summarizes key findings
    2. Highlights the most relevant sources
    3. Suggests what type of information the user can find in each source
    4. Is helpful for research purposes

    Keep it under 200 words and make it engaging.
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    } catch (error) {
      console.error('Response generation error:', error);
      return `I found ${sources.length} relevant sources for your research on "${originalQuery}". The sources include academic articles, reports, and credible publications that should provide comprehensive information on this topic.`;
    }
  }
}

const researchAgent = new ResearchAgent();

// Routes

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Register endpoint
app.post('/api/register', async (req, res) => {
  try {
    const { email, password, name } = req.body;

    if (!email || !password || !name) {
      return res.status(400).json({ error: 'All fields are required' });
    }

    if (users.has(email)) {
      return res.status(400).json({ error: 'User already exists' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = Date.now().toString();

    users.set(email, {
      id: userId,
      email,
      password: hashedPassword,
      name,
      createdAt: new Date()
    });

    const token = jwt.sign({ userId, email }, JWT_SECRET, { expiresIn: '7d' });

    res.status(201).json({
      message: 'User registered successfully',
      token,
      user: { id: userId, email, name }
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Registration failed' });
  }
});

// Login endpoint
app.post('/api/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' });
    }

    const user = users.get(email);
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const isValidPassword = await bcrypt.compare(password, user.password);
    if (!isValidPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const token = jwt.sign({ userId: user.id, email }, JWT_SECRET, { expiresIn: '7d' });

    res.json({
      message: 'Login successful',
      token,
      user: { id: user.id, email: user.email, name: user.name }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

// Token validation endpoint
app.get('/api/validate-token', verifyToken, (req, res) => {
  res.json({ valid: true, userId: req.userId });
});

// Main research endpoint
app.post('/api/research', verifyToken, async (req, res) => {
  try {
    const { query } = req.body;

    if (!query || query.trim().length === 0) {
      return res.status(400).json({ error: 'Query is required' });
    }

    // Check cache first
    const cacheKey = query.toLowerCase().trim();
    if (researchCache.has(cacheKey)) {
      const cachedResult = researchCache.get(cacheKey);
      return res.json(cachedResult);
    }

    console.log(`Processing research query: ${query}`);

    // Step 1: Analyze the query
    const analysis = await researchAgent.analyzeQuery(query);
    console.log('Query analysis:', analysis);

    // Step 2: Perform searches
    let allSources = [];
    
    for (const searchQuery of analysis.searchQueries.slice(0, 3)) { // Limit to 3 queries
      try {
        // Try Google Custom Search first
        let searchResults = await googleSearch(searchQuery, 5);
        
        // If Google Custom Search fails, try SerpApi
        if (searchResults.length === 0 && process.env.SERPAPI_KEY) {
          console.log('Falling back to SerpApi for:', searchQuery);
          searchResults = await serpApiSearch(searchQuery, 5);
        }

        // Process search results
        const processedResults = await Promise.all(
          searchResults.slice(0, 5).map(async (result) => {
            try {
              let sourceData;
              
              if (result.link) {
                // Google Custom Search result
                sourceData = {
                  title: result.title,
                  url: result.link,
                  description: result.snippet,
                  domain: result.displayLink,
                  publishDate: result.pagemap?.metatags?.[0]?.['article:published_time'] || null
                };
              } else if (result.link) {
                // SerpApi result
                sourceData = {
                  title: result.title,
                  url: result.link,
                  description: result.snippet,
                  domain: result.displayed_link,
                  publishDate: result.date || null
                };
              } else {
                return null;
              }

              return sourceData;
            } catch (error) {
              console.error('Error processing search result:', error);
              return null;
            }
          })
        );

        allSources.push(...processedResults.filter(source => source !== null));
      } catch (error) {
        console.error(`Search error for query "${searchQuery}":`, error);
      }
    }

    // Step 3: Filter and rank sources
    const filteredSources = await researchAgent.filterAndRankSources(allSources, query);
    const topSources = filteredSources.slice(0, 8); // Limit to top 8 sources

    // Step 4: Generate AI response
    const aiResponse = await researchAgent.generateResponse(topSources, query);

    const result = {
      response: aiResponse,
      sources: topSources,
      query: query,
      timestamp: new Date().toISOString()
    };

    // Cache the result for 1 hour
    researchCache.set(cacheKey, result);
    setTimeout(() => researchCache.delete(cacheKey), 60 * 60 * 1000);

    res.json(result);

  } catch (error) {
    console.error('Research endpoint error:', error);
    res.status(500).json({
      error: 'Failed to process research request',
      response: 'I apologize, but I encountered an error while researching your query. Please try again with a different search term.',
      sources: []
    });
  }
});

// Get user research history (optional feature)
app.get('/api/history', verifyToken, (req, res) => {
  // This would typically fetch from a database
  // For now, we'll return an empty array since we're using in-memory storage
  res.json({ history: [] });
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log('Environment variables check:');
  console.log('- GEMINI_API_KEY:', process.env.GEMINI_API_KEY ? 'Set' : 'Missing');
  console.log('- GOOGLE_API_KEY:', process.env.GOOGLE_API_KEY ? 'Set' : 'Missing');
  console.log('- GOOGLE_SEARCH_ENGINE_ID:', process.env.GOOGLE_SEARCH_ENGINE_ID ? 'Set' : 'Missing');
  console.log('- SERPAPI_KEY:', process.env.SERPAPI_KEY ? 'Set (Optional)' : 'Not set (Optional)');
});
