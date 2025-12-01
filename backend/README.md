# DailyToon Backend API

This is the backend API for the DailyToon mobile application. It handles story submission, manga panel generation, and image creation using AI services.

## Deployment to Render.com

1. Fork this repository to your GitHub account
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New+" → "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - Name: `dailytoon-backend`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables:
   - `MONGO_URL` - Your MongoDB connection string
   - `DB_NAME` - Database name (usually `dailytoon`)
   - `GEMINI_API_KEY` - Your Gemini API key (if using Gemini)
7. Click "Create Web Service"

## Environment Variables

- `MONGO_URL` - MongoDB connection string
- `DB_NAME` - Database name
- `GEMINI_API_KEY` - Gemini API key (optional)
- `REPLICATE_API_TOKEN` - Replicate API token (optional)

## API Endpoints

- `GET /api/` - Health check endpoint
- `POST /api/story/submit` - Submit a story and get a storyboard
- `POST /api/panels/generate` - Generate image for a specific panel

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up environment variables in `.env` file

3. Run the server:
   ```
   python server.py
   ```

The API will be available at `http://localhost:8003`