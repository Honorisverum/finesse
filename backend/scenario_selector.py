"""
Scenario Selector Module
Analyzes onboarding chat and either selects 3 random scenarios from existing skills
or generates new custom scenarios with character images.
"""

import json
import os
import random
from pathlib import Path
from typing import Literal, Optional
from datetime import datetime
import base64

import aiohttp
from pydantic import BaseModel, Field

import dotenv
dotenv.load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"
GENERATED_IMAGES_DIR = Path(__file__).parent / "generated_test_images"  # Temporary for testing only
EXISTING_SKILLS = [
    "smalltalk",
    "negotiation", 
    "attraction",
    "artofpersuasion",
    "conflictresolution",
    "decodingemotions",
    "manipulationdefense"
]

# Create temporary test images directory if it doesn't exist
GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Default voice IDs for generated characters
DEFAULT_VOICE_IDS = {
    "male": "UgBBYS2sOqTuMpoF3BR0",
    "female": "4NejU5DwQjevnR6mh3mb",
    "neutral": "fsYawdZmGnJKupmmEeSt"  # fallback to male voice
}


# ============================================================================
# Pydantic Models
# ============================================================================

class ScenarioData(BaseModel):
    """Single scenario structure"""
    description: str
    goal: str
    opening: str
    character: list[str]
    negprompt: list[str]
    skill: str
    botname: str
    botgender: Literal["male", "female"]
    voice_description: str
    elevenlabs_voice_id: str


class SkillAnalysisResult(BaseModel):
    """Result of chat analysis"""
    skill: str = Field(description="Detected skill name or 'custom'")
    is_custom: bool = Field(description="Whether this is a custom skill")
    custom_description: str = Field(default="", description="Description if custom")
    user_context: str = Field(default="", description="Additional context from chat")


class ScenarioSelectionResult(BaseModel):
    """Final result with scenarios"""
    skill: str
    is_custom: bool
    scenarios: dict[str, ScenarioData]
    character_images: Optional[dict[str, str]] = None  # scenario_id -> image_url


# ============================================================================
# OpenAI Client
# ============================================================================

class OpenAIClient:
    """Simple OpenAI API client for chat and image generation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.chat_url = "https://api.openai.com/v1/chat/completions"
        self.image_url = "https://api.openai.com/v1/images/generations"
        
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4.1",
        temperature: float = 0.7,
        response_format: Optional[dict] = None
    ) -> str:
        """Call OpenAI chat completion API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            payload["response_format"] = response_format
            
        async with aiohttp.ClientSession() as session:
            async with session.post(self.chat_url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1536",
        quality: str = "high",  # gpt-image-1 supports: low, medium, high, auto
        model: str = "gpt-image-1"
    ) -> str:
        """Generate image using GPT-Image-1"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.image_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    raise Exception(f"DALL-E API Error {resp.status}: {error_data}")
                data = await resp.json()
                
                # gpt-image-1 returns base64 encoded image
                if "data" in data and len(data["data"]) > 0:
                    if "b64_json" in data["data"][0]:
                        return data["data"][0]["b64_json"]
                    elif "url" in data["data"][0]:
                        return data["data"][0]["url"]
                
                raise Exception(f"Unexpected API response structure: {data}")


# ============================================================================
# Core Functions
# ============================================================================

async def analyze_chat_for_skill(
    chat_history: list[dict[str, str]],
    openai_client: OpenAIClient
) -> SkillAnalysisResult:
    """
    Analyze chat history to determine which skill user needs.
    
    Args:
        chat_history: List of messages [{"role": "user/assistant", "content": "..."}]
        openai_client: OpenAI client instance
        
    Returns:
        SkillAnalysisResult with detected skill info
    """
    
    # Build context from chat
    chat_context = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in chat_history[-10:]  # Last 10 messages
    ])
    
    existing_skills_list = ", ".join(EXISTING_SKILLS)
    
    prompt = f"""Analyze this onboarding chat and determine which skill the user needs.

EXISTING SKILLS:
{existing_skills_list}

CHAT HISTORY:
{chat_context}

TASK:
1. If the user's need matches one of the EXISTING SKILLS (even approximately), return that skill name
2. If it's completely different, return "custom"
3. Extract key context about what the user wants to practice

Respond in JSON format:
{{
    "skill": "smalltalk" or "negotiation" or ... or "custom",
    "is_custom": true/false,
    "custom_description": "brief description if custom",
    "user_context": "what user wants to practice"
}}

Examples:
- "I want to get better at talking to strangers" → skill: "smalltalk"
- "Need to negotiate my salary" → skill: "negotiation"  
- "How to attract someone I like" → skill: "attraction"
- "I want to learn quantum physics communication" → skill: "custom", custom_description: "quantum physics communication"
"""
    
    messages = [
        {"role": "system", "content": "You are a skill classification assistant. Always respond with valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    response = await openai_client.chat_completion(
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    data = json.loads(response)
    return SkillAnalysisResult(**data)


def load_scenarios_from_file(skill: str) -> dict[str, ScenarioData]:
    """Load scenarios from JSON file for given skill"""
    file_path = SCENARIOS_DIR / f"{skill}.json"
    
    if not file_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert to ScenarioData models
    scenarios = {}
    for scenario_id, scenario_dict in data.items():
        scenarios[scenario_id] = ScenarioData(**scenario_dict)
    
    return scenarios


def select_random_scenarios(
    skill: str,
    count: int = 3
) -> dict[str, ScenarioData]:
    """
    Select random scenarios from existing skill file.
    
    Args:
        skill: Skill name (must be in EXISTING_SKILLS)
        count: Number of scenarios to select (default: 3)
        
    Returns:
        Dictionary of scenario_id -> ScenarioData
    """
    all_scenarios = load_scenarios_from_file(skill)
    
    # Select random scenarios
    selected_ids = random.sample(list(all_scenarios.keys()), min(count, len(all_scenarios)))
    
    return {
        scenario_id: all_scenarios[scenario_id]
        for scenario_id in selected_ids
    }


async def generate_custom_scenarios(
    custom_description: str,
    user_context: str,
    openai_client: OpenAIClient,
    count: int = 3
) -> dict[str, ScenarioData]:
    """
    Generate new scenarios using LLM based on user's custom skill request.
    
    Args:
        custom_description: Brief description of the custom skill
        user_context: Additional context from user's chat
        openai_client: OpenAI client instance
        count: Number of scenarios to generate
        
    Returns:
        Dictionary of scenario_id -> ScenarioData
    """
    
    # Load example scenarios for few-shot learning
    example_scenarios = []
    for skill in ["smalltalk", "negotiation"]:
        scenarios = load_scenarios_from_file(skill)
        # Take first scenario as example
        first_id = list(scenarios.keys())[0]
        example_scenarios.append({
            "id": first_id,
            "data": scenarios[first_id].model_dump()
        })
    
    examples_text = "\n\n".join([
        f"EXAMPLE {i+1} - ID: {ex['id']}\n{json.dumps(ex['data'], indent=2)}"
        for i, ex in enumerate(example_scenarios)
    ])
    
    guidelines = """
TECHNICAL SPECIFICATIONS:
- Instructions (`character`, `negprompt`): Direct, unambiguous directives for the AI character
- Describe personality, goals, speech style, and reactions to specific user responses
- Formulate precisely and concisely, avoiding subjective or vague formulations

RESTRICTIONS for scenario texts (except `opening`):
- No direct quotes from user or AI in `character`, `negprompt`, `description`, `goal`
- No references to physical actions (nods, looks)
- No mentions of "bot"/"AI"
- No voice characteristics (tone, speed, intonation) - text-only interaction

STRUCTURE and CONTENT:
- `description`: Intriguing intro hinting at task complexity with non-trivial details. Must NOT duplicate `goal`
- `goal`: Clearly measurable, specific objective, formulated concisely and engagingly
- `opening`: Sets scene: place, time, roles (user/AI), initial situation. Includes AI's first line if present
- `negprompt` logic: Describe resistance mechanisms and gradual concession triggers based ONLY on dialogue text

SCENARIO FOCUS:
- Each scenario trains ONE specific aspect of the parent skill
- All scenarios in one category should cover DIFFERENT aspects
- Scenarios must describe recognizable, life-like situations evoking relatable emotions
"""
    
    prompt = f"""You are an expert scenario designer. Create {count} realistic roleplay scenarios for this custom skill:

CUSTOM SKILL: {custom_description}
USER CONTEXT: {user_context}

GUIDELINES:
{guidelines}

EXAMPLE SCENARIOS FROM EXISTING SKILLS:
{examples_text}

TASK:
Generate {count} diverse scenarios that would help someone practice: {custom_description}

Each scenario should:
1. Be realistic and relatable
2. Have a clear, measurable goal
3. Include a character with depth and clear resistance patterns
4. Have gradual concession triggers in negprompt
5. Train a DIFFERENT aspect of the skill

Respond in JSON format:
{{
    "scenario_1": {{
        "description": "...",
        "goal": "...",
        "opening": "...",
        "character": ["...", "..."],
        "negprompt": ["...", "..."],
        "skill": "onword",  // ONE WORD only, lowercase (e.g., "teaching", "debating", "persuading")
        "botname": "...",
        "botgender": "male" or "female" (ONLY these two values allowed),
        "voice_description": "..."
    }},
    "scenario_2": {{ ... }},
    "scenario_3": {{ ... }}
}}

CRITICAL: 
- botgender must be EXACTLY "male" or "female" 
- skill must be ONE WORD ONLY, lowercase, describing the skill based on: {custom_description}
"""
    
    messages = [
        {"role": "system", "content": "You are an expert roleplay scenario designer. Create high-quality, realistic scenarios."},
        {"role": "user", "content": prompt}
    ]
    
    response = await openai_client.chat_completion(
        messages=messages,
        model="gpt-4.1",
        temperature=0.8,
        response_format={"type": "json_object"}
    )
    
    data = json.loads(response)
    
    # Convert to ScenarioData and add default voice IDs
    scenarios = {}
    for scenario_id, scenario_dict in data.items():
        # Normalize botgender to male/female only
        botgender = scenario_dict.get("botgender", "male").lower()
        if botgender not in ["male", "female"]:
            # Default to male if invalid gender provided
            botgender = "male"
        scenario_dict["botgender"] = botgender
        
        # Add default voice ID based on gender
        if "elevenlabs_voice_id" not in scenario_dict:
            scenario_dict["elevenlabs_voice_id"] = DEFAULT_VOICE_IDS[botgender]
        
        scenarios[scenario_id] = ScenarioData(**scenario_dict)
    
    return scenarios


async def save_base64_image(b64_data: str, filename: str) -> str:
    """
    Decode base64 image and save locally.
    
    Args:
        b64_data: Base64 encoded image data
        filename: Filename to save as (without path)
        
    Returns:
        Local file path
    """
    local_path = GENERATED_IMAGES_DIR / filename
    
    # Decode base64 and save
    image_data = base64.b64decode(b64_data)
    
    with open(local_path, 'wb') as f:
        f.write(image_data)
    
    return str(local_path)


async def generate_character_image(
    character_description: list[str],
    character_name: str,
    character_gender: str,
    openai_client: OpenAIClient,
    scenario_id: str = "unknown"
) -> tuple[str, str]:
    """
    Generate character portrait image using GPT-Image-1 and save locally.
    
    Args:
        character_description: List of character traits
        character_name: Character name
        character_gender: "male" or "female"
        openai_client: OpenAI client instance
        scenario_id: Scenario ID for filename
        
    Returns:
        Tuple of (online_url, local_path)
    """
    
    # Build concise description for image generation
    traits = " ".join(character_description[:3])  # Use first 3 traits
    
    # Create optimized prompt for portrait
    prompt = f"""Professional portrait photograph of {character_name}, a {character_gender} character.

Character traits: {traits}

Style: Realistic professional portrait, neutral expression, facing camera, soft lighting, studio background. 
High quality photograph, cinematic, professional headshot style similar to LinkedIn profile photos.

Portrait orientation, vertical composition, focused on face and upper body."""
    
    # Generate image (1024x1536 - vertical portrait like cautiousFriendAdventure.png)
    b64_image = await openai_client.generate_image(
        prompt=prompt,
        size="1024x1536",
        quality="high",
        model="gpt-image-1"
    )
    
    # Save locally with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{scenario_id}_{character_name}_{timestamp}.png"
    local_path = await save_base64_image(b64_image, filename)
    
    return b64_image, local_path


# ============================================================================
# Main Function
# ============================================================================

async def select_or_generate_scenarios(
    chat_history: list[dict[str, str]],
    openai_api_key: str | None = None,
    generate_images: bool = True
) -> ScenarioSelectionResult:
    """
    Main function: analyze chat and either select existing scenarios or generate new ones.
    
    Args:
        chat_history: Onboarding chat history
        openai_api_key: OpenAI API key (if None, reads from FOPENAI_API_KEY env var)
        generate_images: Whether to generate character images for custom scenarios
        
    Returns:
        ScenarioSelectionResult with selected/generated scenarios
    """
    
    # Use FOPENAI_API_KEY if no key provided
    if openai_api_key is None:
        openai_api_key = os.getenv("FOPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("FOPENAI_API_KEY environment variable not set")
    
    client = OpenAIClient(openai_api_key)
    
    # Step 1: Analyze chat to determine skill
    analysis = await analyze_chat_for_skill(chat_history, client)
    
    # Step 2: Select or generate scenarios
    if analysis.is_custom:
        # Generate custom scenarios
        scenarios = await generate_custom_scenarios(
            custom_description=analysis.custom_description,
            user_context=analysis.user_context,
            openai_client=client,
            count=3
        )
        
        # Generate character images if requested
        character_images = {}
        if generate_images:
            for scenario_id, scenario in scenarios.items():
                try:
                    print(f"Generating image for {scenario_id} ({scenario.botname})...")
                    b64_data, local_path = await generate_character_image(
                        character_description=scenario.character,
                        character_name=scenario.botname,
                        character_gender=scenario.botgender,
                        openai_client=client,
                        scenario_id=scenario_id
                    )
                    character_images[scenario_id] = b64_data  # Store base64
                    print(f"✓ Image generated for {scenario_id}")
                    print(f"  Saved to: {local_path}")
                except Exception as e:
                    print(f"✗ Failed to generate image for {scenario_id}:")
                    print(f"  Error: {e}")
                    # Continue without image
        
        return ScenarioSelectionResult(
            skill=analysis.skill,
            is_custom=True,
            scenarios=scenarios,
            character_images=character_images if character_images else None
        )
    
    else:
        # Select random from existing
        scenarios = select_random_scenarios(analysis.skill, count=3)
        
        return ScenarioSelectionResult(
            skill=analysis.skill,
            is_custom=False,
            scenarios=scenarios,
            character_images=None
        )


# ============================================================================
# CLI Test Interface
# ============================================================================

async def main():
    """Test function - demonstrates custom skill with character image generation"""
    import asyncio
    
    # Example: Custom skill that doesn't exist in predefined list
    test_chat = [
        {"role": "assistant", "content": "What skill would you like to practice?"},
        {"role": "user", "content": "I want to learn how to teach complex technical topics to complete beginners"},
        {"role": "assistant", "content": "Interesting! Tell me more about what you want to learn."},
        {"role": "user", "content": "Yeah, like explaining programming or science concepts to people with zero background. Making it simple without being condescending."}
    ]
    
    # Use FOPENAI_API_KEY env var
    api_key = os.getenv("FOPENAI_API_KEY")
    if not api_key:
        print("❌ Error: FOPENAI_API_KEY environment variable not set")
        return
    
    print("🔍 Analyzing chat...")
    print("💭 Generating custom scenarios with character images (this may take 30-60 seconds)...\n")
    
    result = await select_or_generate_scenarios(
        test_chat, 
        api_key, 
        generate_images=True  # Enable image generation for custom scenarios
    )
    
    print(f"\n{'='*70}")
    print(f"=== RESULT ===")
    print(f"{'='*70}")
    print(f"✅ Skill: {result.skill}")
    print(f"🎨 Is Custom: {result.is_custom}")
    print(f"🎭 Number of scenarios: {len(result.scenarios)}")
    
    if result.character_images:
        print(f"🖼️  Character images generated: {len(result.character_images)}")
    
    for i, (scenario_id, scenario) in enumerate(result.scenarios.items(), 1):
        print(f"\n{'-'*70}")
        print(f"SCENARIO #{i}: {scenario_id}")
        print(f"{'-'*70}")
        print(f"👤 Character: {scenario.botname} ({scenario.botgender})")
        print(f"📝 Description: {scenario.description}")
        print(f"🎯 Goal: {scenario.goal}")
        print(f"💬 Opening line: {scenario.opening[:150]}...")
        
        # Show character image URL if generated
        if result.character_images and scenario_id in result.character_images:
            print(f"\n🖼️  CHARACTER IMAGE:")
            print(f"   {result.character_images[scenario_id]}")
        
        print(f"\n🎭 Character traits ({len(scenario.character)}):")
        for trait in scenario.character[:3]:  # Show first 3 traits
            print(f"   • {trait}")
    
    print(f"\n{'='*70}")
    print("✨ Test completed! Check the image URLs above to see generated portraits.")
    print(f"{'='*70}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

