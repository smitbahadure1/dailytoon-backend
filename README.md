# Daily Toon - AI-Powered Manga Generator

Daily Toon is a mobile application that transforms your daily stories into manga-style comics using AI.

## Features

- Convert personal stories into 4-6 panel manga comics
- AI-powered story analysis and panel creation
- Manga-style image generation using Pollinations.ai
- Character customization
- Offline viewing of created comics

## Tech Stack

### Frontend
- React Native with Expo
- TypeScript
- Expo Router for navigation

### Backend
- FastAPI (Python)
- MongoDB for data storage
- Pollinations.ai for image generation
- Gemini AI for story analysis

## Deployment

### Backend Deployment (Render.com)

1. Fork this repository
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Create a new Web Service
4. Connect your GitHub repository
5. Configure with:
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn backend.server:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   - `MONGO_URL` - Your MongoDB connection string
   - `DB_NAME` - Database name (usually `dailytoon`)
   - `GEMINI_API_KEY` - Your Gemini API key

### Frontend Deployment (Mobile App)

1. Update the `.env` file with your deployed backend URL
2. Build the APK:
   ```bash
   eas build --platform android --profile preview
   ```
3. Download the APK from Expo dashboard
4. Install on Android devices

## Local Development

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `backend/.env`
4. Run the server:
   ```bash
   python server.py
   ```

### Frontend

1. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```
2. Start the development server:
   ```bash
   npx expo start
   ```

## Environment Variables

### Frontend (.env in project root)
- `EXPO_PUBLIC_BACKEND_URL` - Backend API URL

### Backend (backend/.env)
- `MONGO_URL` - MongoDB connection string
- `DB_NAME` - Database name
- `GEMINI_API_KEY` - Gemini API key
- `REPLICATE_API_TOKEN` - Replicate API token (if using Replicate models)

## API Endpoints

- `POST /api/story/submit` - Submit a story and get a storyboard
- `POST /api/panels/generate` - Generate image for a specific panel
- `GET /api/episodes` - Get all episodes
- `GET /api/episodes/{episode_id}` - Get a specific episode

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

This project is licensed under the MIT License.
