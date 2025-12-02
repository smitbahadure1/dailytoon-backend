from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import base64
import httpx
import urllib.parse
import json
import re
import certifi

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    print("WARNING: MONGO_URL environment variable is not set")
    mongo_url = "mongodb://localhost:27017" # Fallback for local testing if needed

# Add retryWrites to the connection string if it's a cloud URI
if mongo_url.startswith("mongodb+srv://") and '?' not in mongo_url:
    mongo_url += '?retryWrites=true'
elif mongo_url.startswith("mongodb+srv://") and '?' in mongo_url and 'retryWrites' not in mongo_url:
    mongo_url += '&retryWrites=true'

client = None
db = None

# MongoDB connection with SSL compatibility for Python 3.13+
# Using tlsAllowInvalidCertificates to bypass SSL verification issues on Render
try:
    print(f"Attempting to connect to MongoDB...")
    # For Python 3.13.4 on Render, we need to allow invalid certificates
    # This is safe for MongoDB Atlas connections
    client = AsyncIOMotorClient(
        mongo_url, 
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000
    )
    print("MongoDB client initialized")
except Exception as connection_error:
    print(f"MongoDB connection failed: {connection_error}")
    # We don't raise here to allow the app to start, but DB ops will fail

DB_NAME = os.environ.get('DB_NAME', 'dailytoon')
if client:
    db = client[DB_NAME]
    print(f"Using database: {DB_NAME}")
else:
    print("CRITICAL: Could not initialize MongoDB client. Database operations will fail.")

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== MODELS ==========

class Panel(BaseModel):
    panel_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: int
    scene_description: str
    dialogue: str
    character_description: str
    background: str
    image_base64: Optional[str] = None

class ComicEpisode(BaseModel):
    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    user_story_text: str
    created_date: datetime = Field(default_factory=datetime.utcnow)
    panels: List[Panel] = []
    character_profile: Optional[str] = None

class StorySubmit(BaseModel):
    story_text: str
    character_name: Optional[str] = None
    character_appearance: Optional[str] = None

class StoryboardResponse(BaseModel):
    episode_id: str
    title: str
    character_profile: str
    panels: List[Panel]

class PanelGenerateRequest(BaseModel):
    episode_id: str
    panel_id: str

# ========== HELPER FUNCTIONS ==========

async def analyze_story_and_create_storyboard(story_text: str, character_name: Optional[str], character_appearance: Optional[str]) -> dict:
    """
    Use Pollinations.ai (Free Text API) to analyze the story and create a storyboard.
    """
    try:
        # Create character profile
        char_name = character_name or "the main character"
        char_appearance = character_appearance or "a young person with expressive eyes, dark hair, casual modern clothing"
        
        character_profile = f"{char_name}: {char_appearance}"
        
        # Construct prompt for Pollinations
        system_instruction = "You are a manga story expert. Analyze the story and break it into 4-6 dramatic manga-style scenes. Return ONLY valid JSON."
        
        prompt = f"""{system_instruction}

Story: {story_text}
Main Character: {character_profile}

Create 4-6 manga panels. For each panel provide:
1. scene_description (visual)
2. dialogue (speech/thought)
3. background (setting)

Format as JSON:
{{
  "title": "Episode Title",
  "panels": [
    {{
      "scene_description": "...",
      "dialogue": "...",
      "background": "..."
    }}
  ]
}}
"""
        
        logger.info("Sending request to Pollinations Text API...")
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Pollinations Text API failed: {response.status_code}")
            
            response_text = response.text
            logger.info(f"Pollinations Response: {response_text[:100]}...")

        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        try:
            storyboard_data = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                storyboard_data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse JSON from response")

        return {
            "title": storyboard_data.get("title", "My Daily Story"),
            "character_profile": character_profile,
            "panels": storyboard_data.get("panels", [])
        }
        
    except Exception as e:
        logger.error(f"Error in story analysis: {str(e)}")
        return {
            "title": "My Daily Story",
            "character_profile": character_profile,
            "panels": [
                {
                    "scene_description": f"{char_name} is standing there.",
                    "dialogue": "...",
                    "background": "A simple background"
                }
            ]
        }

async def generate_manga_image_pollinations(scene_description: str, dialogue: str, character_profile: str, background: str) -> str:
    """
    Generate a manga-style image using Pollinations.ai (Free API).
    Returns base64 encoded image.
    """
    # Retry configuration
    max_retries = 3
    base_delay = 2
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            base_prompt = f"manga style comic panel, black and white, screentones, {scene_description}, character {character_profile}, setting {background}, mood {dialogue}, high quality, detailed line art"
            encoded_prompt = urllib.parse.quote(base_prompt)
            
            # Add random seed to avoid caching issues
            seed = uuid.uuid4().int % 100000
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={seed}&nologo=true"
            
            logger.info(f"Generating image with Pollinations.ai (Attempt {attempt + 1}/{max_retries})")
            
            # Increased timeout to 60 seconds for slower connections/cold starts
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(image_url)
                if response.status_code == 200:
                    image_bytes = response.content
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    return image_base64
                else:
                    logger.warning(f"Pollinations API returned {response.status_code}")
                    if response.status_code >= 500:
                        # Server error, retry
                        raise HTTPException(status_code=500, detail=f"Pollinations API error: {response.status_code}")
                    else:
                        # Client error, don't retry
                        raise HTTPException(status_code=response.status_code, detail=f"Pollinations API error: {response.status_code}")
                
        except Exception as e:
            last_error = e
            logger.error(f"Error generating image (Attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                import asyncio
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            
    # If we get here, all retries failed
    raise HTTPException(status_code=500, detail=f"Image generation failed after {max_retries} attempts: {str(last_error)}")

# ========== API ENDPOINTS ==========

@api_router.get("/health")
async def health_check():
    """Simple health check that doesn't require DB"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@api_router.get("/")
async def root():
    return {"message": "DailyToon API", "status": "running", "version": "1.0.1"}

@api_router.post("/story/submit", response_model=StoryboardResponse)
async def submit_story(story_input: StorySubmit):
    """
    Submit a daily story and get a storyboard back.
    """
    try:
        logger.info(f"Received story: {story_input.story_text[:100]}...")
        
        storyboard = await analyze_story_and_create_storyboard(
            story_input.story_text,
            story_input.character_name,
            story_input.character_appearance
        )
        
        episode = ComicEpisode(
            title=storyboard["title"],
            user_story_text=story_input.story_text,
            character_profile=storyboard["character_profile"],
            panels=[]
        )
        
        for idx, panel_data in enumerate(storyboard["panels"]):
            panel = Panel(
                order=idx,
                scene_description=panel_data["scene_description"],
                dialogue=panel_data["dialogue"],
                character_description=storyboard["character_profile"],
                background=panel_data["background"],
                image_base64=None
            )
            episode.panels.append(panel)
        
        await db.episodes.insert_one(episode.dict())
        
        logger.info(f"Created episode: {episode.episode_id}")
        
        return StoryboardResponse(
            episode_id=episode.episode_id,
            title=episode.title,
            character_profile=episode.character_profile,
            panels=episode.panels
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Error in submit_story: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/panels/generate")
async def generate_panel_image(request: PanelGenerateRequest):
    """
    Generate manga image for a specific panel using Pollinations.ai.
    """
    try:
        episode_data = await db.episodes.find_one({"episode_id": request.episode_id})
        
        if not episode_data:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        episode = ComicEpisode(**episode_data)
        
        panel = None
        for p in episode.panels:
            if hasattr(p, 'panel_id') and p.panel_id == request.panel_id:
                panel = p
                break
        
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        if hasattr(panel, 'image_base64') and panel.image_base64:
            return {"image_base64": panel.image_base64, "status": "cached"}
        
        logger.info(f"Generating image for panel {panel.panel_id}")
        
        image_base64 = await generate_manga_image_pollinations(
            scene_description=panel.scene_description,
            dialogue=panel.dialogue,
            character_profile=episode.character_profile,
            background=panel.background
        )
        
        result = await db.episodes.update_one(
            {"episode_id": request.episode_id, "panels.panel_id": request.panel_id},
            {"$set": {"panels.$.image_base64": image_base64}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Episode or panel not found for update")
        
        return {"image_base64": image_base64, "status": "generated"}
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error generating panel image: {str(e)}")
        logger.error(f"Traceback: {error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/episodes", response_model=List[ComicEpisode])
async def get_all_episodes():
    try:
        episodes = await db.episodes.find().sort("created_date", -1).to_list(100)
        return [ComicEpisode(**ep) for ep in episodes]
    except Exception as e:
        import traceback
        logger.error(f"Error fetching episodes: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/episodes/{episode_id}", response_model=ComicEpisode)
async def get_episode(episode_id: str):
    try:
        episode_data = await db.episodes.find_one({"episode_id": episode_id})
        
        if not episode_data:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        return ComicEpisode(**episode_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching episode: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/episodes/{episode_id}")
async def delete_episode(episode_id: str):
    try:
        result = await db.episodes.delete_one({"episode_id": episode_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        return {"message": "Episode deleted", "episode_id": episode_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting episode: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
