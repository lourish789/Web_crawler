# Research Chatbot Deployment Guide

## 🚀 Complete Setup Instructions

### Prerequisites
1. **Google AI Studio Account** - Get Gemini API key
2. **Google Cloud Console** - For Custom Search API
3. **GitHub Account** - For code repository
4. **Render Account** - For backend hosting
5. **Vercel Account** - For frontend hosting

---

## 📋 Step 1: Get Required API Keys

### 1.1 Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the API key

### 1.2 Google Custom Search API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable "Custom Search API"
4. Create credentials (API Key)
5. Go to [Custom Search Engine](https://cse.google.com/cse/)
6. Create a new search engine
7. Set "Search the entire web" option
8. Copy the Search Engine ID

### 1.3 SerpApi (Optional Backup)
1. Go to [SerpApi](https://serpapi.com/)
2. Sign up for free account (100 searches/month)
3. Copy API key from dashboard

---

## 📁 Step 2: Project Setup

### 2.1 Create Project Structure
```
research-chatbot/
├── backend/
│   ├── server.js
│   ├── package.json
│   ├── .env
│   └── .gitignore
└── frontend/
    ├── src/
    │   ├── App.js
    │   ├── App.css
    │   └── index.js
    ├── public/
    │   └── index.html
    ├── package.json
    ├── .env
    └── .gitignore
```

### 2.2 Backend Setup
1. Create `backend` folder
2. Copy the server.js code into `backend/server.js`
3. Copy the backend package.json
4. Create `.env` file with your API keys:
```
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
SERPAPI_KEY=your_serpapi_key
JWT_SECRET=your-super-secure-random-string
PORT=5000
```

5. Create `.gitignore`:
```
node_modules/
.env
*.log
.DS_Store
```

6. Install dependencies:
```bash
cd backend
npm install
```

### 2.3 Frontend Setup
1. Create React app:
```bash
npx create-react-app frontend
cd frontend
```

2. Replace `src/App.js` with the provided React code
3. Replace `src/App.css` with the provided CSS
4. Create `.env` file:
```
REACT_APP_API_URL=http://localhost:5000
```

5. Update `public/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="AI-powered research assistant" />
    <title>Research Assistant</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
```

---

## 🔧 Step 3: Local Testing

### 3.1 Test Backend
```bash
cd backend
npm run dev
```
Visit: http://localhost:5000/health

### 3.2 Test Frontend
```bash
cd frontend
npm start
```
Visit: http://localhost:3000

---

## 🌐 Step 4: Deploy Backend to Render

### 4.1 Prepare Backend for Deployment
1. Create GitHub repository for your project
2. Push backend code to GitHub
3. Ensure `package.json` has start script: `"start": "node server.js"`

### 4.2 Deploy on Render
1. Go to [Render](https://render.com/)
2. Sign up/Login with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name**: `research-chatbot-backend`
   - **Runtime**: `Node`
   - **Build Command**: `npm install`
   - **Start Command**: `npm start`
   - **Instance Type**: `Free`

### 4.3 Add Environment Variables
In Render dashboard, go to Environment tab and add:
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `GOOGLE_SEARCH_ENGINE_ID`
- `SERPAPI_KEY` (optional)
- `JWT_SECRET`

### 4.4 Deploy
Click "Create Web Service" and wait for deployment.
Copy your backend URL: `https://your-app-name.onrender.com`

---

## 🎨 Step 5: Deploy Frontend to Vercel

### 5.1 Update Frontend Environment
Update `frontend/.env`:
```
REACT_APP_API_URL=https://your-render-backend-app.onrender.com
```

### 5.2 Deploy on Vercel
1. Go to [Vercel](https://vercel.com/)
2. Sign up/Login with GitHub
3. Click "New Project"
4. Import your GitHub repository
5. Configure:
   - **Framework Preset**: `Create React App`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`

### 5.3 Add Environment Variable
In Vercel project settings, add:
- `REACT_APP_API_URL` = `https://your-render-backend-app.onrender.com`

### 5.4 Deploy
Click "Deploy" and wait for completion.

---

## 🔐 Step 6: Security & Production Considerations

### 6.1 Security Enhancements
1. **JWT Secret**: Use a strong, random JWT secret
2. **CORS**: Update CORS settings in backend for production
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Input Validation**: Add input sanitization

### 6.2 Update Backend CORS (in server.js)
```javascript
app.use(cors({
  origin: ['https://your-vercel-app.vercel.app', 'http://localhost:3000'],
  credentials: true
}));
```

---

## 🧪 Step 7: Testing the Full Application

### 7.1 Test Registration/Login
1. Visit your Vercel frontend URL
2. Register a new account
3. Login with credentials

### 7.2 Test Research Functionality
1. Try queries like:
   - "Latest climate change research 2024"
   - "Best practices for remote work"
   - "Artificial intelligence trends"

### 7.3 Verify Sources
1. Check that credible sources are returned
2. Verify links are clickable and valid
3. Test responsive design on mobile

---

## 🎯 Step 8: Optional Enhancements

### 8.1 Database Integration
Replace in-memory storage with:
- **PostgreSQL** (free tier on Railway/Supabase)
- **MongoDB** (free tier on MongoDB Atlas)

### 8.2 Additional Features
- User search history
- Bookmarking sources
- Export to PDF/Word
- Advanced filtering
- Real-time collaborative research

### 8.3 Monitoring & Analytics
- Add Google Analytics
- Implement error tracking (Sentry)
- Monitor API usage

---

## 🚨 Troubleshooting

### Common Issues:

**1. Backend not starting**
- Check all environment variables are set
- Verify API keys are valid
- Check Render logs

**2. Frontend can't connect to backend**
- Verify REACT_APP_API_URL is correct
- Check CORS settings
- Ensure backend is deployed and running

**3. No search results**
- Verify Google Custom Search API is enabled
- Check API quotas
- Test with SerpApi as backup

**4. Authentication issues**
- Check JWT_SECRET is set
- Verify token storage in localStorage
- Check network requests in browser dev tools

### Support Resources:
- [Google AI Studio Documentation](https://ai.google.dev/)
- [Google Custom Search API Docs](https://developers.google.com/custom-search/v1/overview)
- [Render Documentation](https://render.com/docs)
- [Vercel Documentation](https://vercel.com/docs)

---

## 🎉 Congratulations!

Your AI-powered research chatbot is now live! Users can:
- Create accounts and login securely
- Ask research questions
- Get AI-powered responses with credible sources
- Access articles, reports, and academic papers
- Use it for writing and research assistance

The application is fully deployed on free platforms and ready for production use!
