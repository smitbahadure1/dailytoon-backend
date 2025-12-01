from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
from pathlib import Path
import uuid
from datetime import datetime
import base64
import httpx
import urllib.parse
import json
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
    try:
        base_prompt = f"manga style comic panel, black and white, screentones, {scene_description}, character {character_profile}, setting {background}, mood {dialogue}, high quality, detailed line art"
        encoded_prompt = urllib.parse.quote(base_prompt)
        
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={uuid.uuid4().int % 100000}&nologo=true"
        
        logger.info(f"Generating image with Pollinations.ai")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            if response.status_code == 200:
                image_bytes = response.content
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                return image_base64
            else:
                raise HTTPException(status_code=500, detail=f"Failed to generate image from Pollinations.ai: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error generating image with Pollinations.ai: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

# ========== API ENDPOINTS ==========
@api_router.get("/")
async def root():
    return {"message": "DailyToon API", "status": "running"}

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
        
        # Instead of saving to MongoDB, we'll just return the episode data
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
        # For testing purposes, we'll create a mock episode with sample data
        # In a real implementation, this would fetch from a database
        
        # Create a mock episode with sample data
        mock_episode = ComicEpisode(
            episode_id=request.episode_id,
            title="Test Episode",
            user_story_text="Test story",
            character_profile="Test character",
            panels=[
                Panel(
                    panel_id=request.panel_id,
                    order=0,
                    scene_description="A test scene with a character",
                    dialogue="This is a test dialogue",
                    character_description="Test character",
                    background="A simple background",
                    image_base64=None
                )
            ]
        )
        
        # Find the panel
        panel = None
        for p in mock_episode.panels:
            if hasattr(p, 'panel_id') and p.panel_id == request.panel_id:
                panel = p
                break
        
        if not panel:
            raise HTTPException(status_code=404, detail="Panel not found")
        
        logger.info(f"Generating image for panel {panel.panel_id}")
        
        image_base64 = await generate_manga_image_pollinations(
            scene_description=panel.scene_description,
            dialogue=panel.dialogue,
            character_profile=mock_episode.character_profile,
            background=panel.background
        )
        
        return {"image_base64": image_base64, "status": "generated"}
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error generating panel image: {str(e)}")
        logger.error(f"Traceback: {error_details}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)