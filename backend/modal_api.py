"""
Modal API endpoint for scenario selection
"""
import modal
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Paths
backend_dir = Path(__file__).parent
project_root = backend_dir.parent

# Build image with all necessary files
image = (
    modal.Image.debian_slim()
    .pip_install("aiohttp", "pydantic", "fastapi[standard]")
    .add_local_file(backend_dir / "scenario_selector.py", "/root/scenario_selector.py")
    .add_local_dir(project_root / "scenarios", "/scenarios")
    .add_local_dir(project_root / "frontend/public/photos", "/photos")
)

app = modal.App("finesse-scenario-selector", image=image)

# Secret
if modal.is_local():
    api_key = os.getenv("FOPENAI_API_KEY", "")
    local_secret = modal.Secret.from_dict({"FOPENAI_API_KEY": api_key}) if api_key else modal.Secret.from_dict({})
else:
    local_secret = modal.Secret.from_dict({})


@app.function(secrets=[local_secret], timeout=300)
@modal.fastapi_endpoint(method="POST")
async def get_scenarios(data: dict):
    """POST /get_scenarios - Returns 3 scenarios with base64 images"""
    import os
    import base64
    from pathlib import Path
    from scenario_selector import select_or_generate_scenarios
    
    chat_history = data.get("chat_history", [])
    api_key = os.getenv("FOPENAI_API_KEY")
    
    result = await select_or_generate_scenarios(
        chat_history=chat_history,
        openai_api_key=api_key,
        generate_images=False  # Don't generate images for custom scenarios
    )
    
    # For custom skills, extract skill name from scenarios
    skill_name = result.skill
    if result.is_custom and result.scenarios:
        # Get skill name from first scenario
        first_scenario = next(iter(result.scenarios.values()))
        skill_name = first_scenario.skill
    
    scenarios_list = []
    for scenario_id, scenario_data in result.scenarios.items():
        scenario_dict = scenario_data.model_dump()
        scenario_dict["id"] = scenario_id
        
        if result.is_custom:
            scenario_dict["image_base64"] = None
        else:
            try:
                img_path = Path(f"/photos/{result.skill}/{scenario_id}.png")
                with open(img_path, 'rb') as f:
                    scenario_dict["image_base64"] = base64.b64encode(f.read()).decode('utf-8')
            except:
                scenario_dict["image_base64"] = None
        
        scenarios_list.append(scenario_dict)
    
    return {
        "skill": skill_name,
        "is_custom": result.is_custom,
        "scenarios": scenarios_list
    }
