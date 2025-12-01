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
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import fal_client
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    raise ValueError("MONGO_URL environment variable is required")

client = AsyncIOMotorClient(mongo_url)

DB_NAME = os.environ.get('DB_NAME')
if not DB_NAME:
    raise ValueError("DB_NAME environment variable is required")
db = client[DB_NAME]

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
if not EMERGENT_LLM_KEY:
    raise ValueError("EMERGENT_LLM_KEY environment variable is required")

FAL_KEY = os.environ.get('FAL_KEY')
if not FAL_KEY:
    raise ValueError("FAL_KEY environment variable is required")

# Configure fal_client
os.environ["FAL_KEY"] = FAL_KEY

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
    Use GPT to analyze the story and create a storyboard with scenes.
    """
    try:
        # Create character profile
        char_name = character_name or "the main character"
        char_appearance = character_appearance or "a young person with expressive eyes, dark hair, casual modern clothing"
        
        character_profile = f"{char_name}: {char_appearance}"
        
        # Create LLM chat instance
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are a manga story expert. You analyze daily life stories and break them into 4-6 dramatic manga-style scenes with dialogue."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze this daily story and create a manga comic storyboard:

Story: {story_text}

Main Character: {character_profile}

Create 4-6 manga panels. For each panel provide:
1. Scene description (what's happening visually)
2. Dialogue (what the character says or thinks)
3. Background setting

Format your response as JSON with this structure:
{{
  "title": "Episode title (3-5 words)",
  "panels": [
    {{
      "scene_description": "Visual description",
      "dialogue": "Character dialogue or thoughts",
      "background": "Setting description"
    }}
  ]
}}

Make it dramatic and manga-style with emotional expressions!"""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        logger.info(f"GPT Response: {response}")
        
        # Parse the JSON response
        response_text = response.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            storyboard_data = json.loads(response_text)
        except json.JSONDecodeError as je:
            logger.error(f"JSON parsing failed: {str(je)}. Response text: {response_text}")
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    storyboard_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    raise HTTPException(status_code=500, detail="Failed to parse storyboard data from LLM response")
            else:
                raise HTTPException(status_code=500, detail="Failed to parse storyboard data from LLM response")
        
        return {
            "title": storyboard_data.get("title", "My Daily Story"),
            "character_profile": character_profile,
            "panels": storyboard_data.get("panels", [])
        }
        
    except Exception as e:
        logger.error(f"Error in story analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Story analysis failed: {str(e)}")

async def generate_manga_image_fal(scene_description: str, dialogue: str, character_profile: str, background: str) -> str:
    """
    Generate a manga-style image using fal.ai.
    Returns base64 encoded image.
    """
    try:
        # Create detailed manga prompt
        prompt = f"""Manga style comic panel, black and white with screentones:
{scene_description}
Character: {character_profile}
Setting: {background}
Mood: {dialogue}

Style: Japanese manga, dramatic angles, expressive emotions, clean linework, screentone shading, professional manga artist quality."""
        
        logger.info(f"Generating image with fal.ai, prompt: {prompt[:100]}...")
        
        # Use fal.ai FLUX model for manga generation
        result = await fal_client.run_async(
            "fal-ai/flux/dev",
            arguments={
                "prompt": prompt,
                "image_size": "square_hd",
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "num_images": 1,
                "enable_safety_checker": False
            }
        )
        
        if result and "images" in result and len(result["images"]) > 0:
            image_url = result["images"][0]["url"]
            
            # Download the image and convert to base64
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                if response.status_code == 200:
                    image_bytes = response.content
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    return image_base64
                else:
                    raise HTTPException(status_code=500, detail="Failed to download generated image")
        else:
            raise HTTPException(status_code=500, detail="No image was generated")
            
    except Exception as e:
        logger.error(f"Error generating image with fal.ai: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

# ========== API ENDPOINTS ==========

@api_router.get("/")
async def root():
    return {"message": "DailyToon API", "status": "running"}

@api_router.post("/story/submit", response_model=StoryboardResponse)
async def submit_story(story_input: StorySubmit):
    """
    Submit a daily story and get a storyboard back.
    This analyzes the story and creates panel descriptions.
    """
    try:
        logger.info(f"Received story: {story_input.story_text[:100]}...")
        
        # Analyze story and create storyboard
        storyboard = await analyze_story_and_create_storyboard(
            story_input.story_text,
            story_input.character_name,
            story_input.character_appearance
        )
        
        # Create episode
        episode = ComicEpisode(
            title=storyboard["title"],
            user_story_text=story_input.story_text,
            character_profile=storyboard["character_profile"],
            panels=[]
        )
        
        # Create panel objects
        for idx, panel_data in enumerate(storyboard["panels"]):
            panel = Panel(
                order=idx,
                scene_description=panel_data["scene_description"],
                dialogue=panel_data["dialogue"],
                character_description=storyboard["character_profile"],
                background=panel_data["background"],
                image_base64=None  # Images generated separately
            )
            episode.panels.append(panel)
        
        # Save to database
        await db.episodes.insert_one(episode.dict())
        
        logger.info(f"Created episode: {episode.episode_id}")
        
        return StoryboardResponse(
            episode_id=episode.episode_id,
            title=episode.title,
            character_profile=episode.character_profile,
            panels=episode.panels
        )
        
    except Exception as e:
        logger.error(f"Error in submit_story: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/panels/generate")
async def generate_panel_image(request: PanelGenerateRequest):
    """
    Generate manga image for a specific panel using fal.ai.
    """
    try:
        # Get episode from database
        episode_data = await db.episodes.find_one({"episode_id": request.episode_id})
        
        if not episode_data:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        episode = ComicEpisode(**episode_data)
        
        # Find the panel
        panel = None
        panel_index = -1
        for i, p in enumerate(episode.panels):
            if hasattr(p, 'panel_id') and p.panel_id == request.panel_id:
                panel = p
                panel_index = i
                break
        
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        # Check if image already exists
        if hasattr(panel, 'image_base64') and panel.image_base64:
            return {"image_base64": panel.image_base64, "status": "cached"}
        
        # Generate image with fal.ai
        logger.info(f"Generating image for panel {panel.panel_id} with fal.ai")
        
        image_base64 = await generate_manga_image_fal(
            scene_description=panel.scene_description,
            dialogue=panel.dialogue,
            character_profile=episode.character_profile,
            background=panel.background
        )
        
        # Update panel with image
        try:
            result = await db.episodes.update_one(
                {"episode_id": request.episode_id, "panels.panel_id": request.panel_id},
                {"$set": {"panels.$.image_base64": image_base64}}
            )
            
            if result.matched_count == 0:
                logger.warning(f"No episode matched for panel update: {request.episode_id}")
                raise HTTPException(status_code=404, detail="Episode or panel not found for update")
                
        except Exception as e:
            logger.error(f"Error updating panel image in database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update panel image: {str(e)}")
        
        return {"image_base64": image_base64, "status": "generated"}
        
    except Exception as e:
        logger.error(f"Error generating panel image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/episodes", response_model=List[ComicEpisode])
async def get_all_episodes():
    """
    Get all comic episodes.
    """
    try:
        episodes = await db.episodes.find().sort("created_date", -1).to_list(100)
        return [ComicEpisode(**ep) for ep in episodes]
    except Exception as e:
        logger.error(f"Error fetching episodes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/episodes/{episode_id}", response_model=ComicEpisode)
async def get_episode(episode_id: str):
    """
    Get a specific episode by ID.
    """
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
    """
    Delete an episode.
    """
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
