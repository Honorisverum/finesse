import gradio as gr
import random
import json
import litellmapi
import checker
import re
from pathlib import Path

ROLEPLAY_SYSTEM_PROMPT_ADDITION = """
Keep your responses concise - no more than 1 short sentences <= 10 words.
Use expressive actions and emotions in *asterisks* to describe your actions.
Stay in your role no matter what. Never break character or deviate from the personality.
"""

AVAILABLE_MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "gemini/gemini-2.0-flash",
    "deepseek/deepseek-chat",
    "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
]

def load_scenarios():
    scenarios = []
    script_dir = Path(__file__).parent
    for file_path in script_dir.glob('*.json'):
        with open(file_path, "r") as f:
            scenario_data = json.load(f)
            scenarios.append(scenario_data)
    return scenarios

# Getting list of skills from scenarios
def get_skills(scenarios):
    skills = set()
    for scenario in scenarios:
        skills.add(scenario["skill"])
    return sorted(list(skills))

# Getting levels for selected skill
def get_levels_for_skill(scenarios, skill):
    levels = []
    for scenario in scenarios:
        if scenario["skill"] == skill:
            levels.append(str(scenario["level"]))
    return sorted(levels)

# Getting scenario by skill and level
def get_scenario(scenarios, skill, level):
    for scenario in scenarios:
        if scenario["skill"] == skill and str(scenario["level"]) == level:
            return scenario.copy()
    raise ValueError(f"Scenario for skill {skill} and level {level} not found")

# Format scenario with bot/user names
def format_scenario(scenario, username):
    # Используем поле botname из сценария
    botname = scenario["botname"]
    
    scenario = {
        k: v.replace('[botname]', botname).replace('[username]', username).format(botname=botname, username=username).strip()
        if isinstance(v, str) else v
        for k, v in scenario.items()
    }
    return scenario

# Format messages with roleplay actions for display only
def format_for_display(messages):
    display_messages = []
    
    for msg in messages:
        content = msg["content"]
        role = msg["role"]
        
        # Regular expression to match text within asterisks
        pattern = r'(\*[^*]+\*)'
        parts = re.split(pattern, content)
        
        formatted_parts = []
        for part in parts:
            if part.startswith('*') and part.endswith('*'):
                # Format roleplay text with italics and color
                formatted_parts.append(f"<i style='color:#6c757d'>{part}</i>")
            elif part.strip():
                # Regular text
                formatted_parts.append(part)
                
        # Join with line breaks
        formatted_content = "<br>".join([p for p in formatted_parts if p.strip()])
        display_messages.append({"role": role, "content": formatted_content})
    
    return display_messages

# Loading scenarios
SCENARIO_INFO_FORMAT = """
## 👤 Character Name 
{botname}

## ⚽️ Your Goal
{frontend_description_for_user}

## 🤖 Character You'll Talk With
{bot_personality}

## 💬 Starting Situation
{opening_setup}

## 🎯 Goal for Checker
{goal_for_goal_checker}

## 🔴 neg prompt
{neg_prompt}

## 🟢 pos prompt
{pos_prompt}
"""

SCENARIOS = load_scenarios()
SKILLS = get_skills(SCENARIOS)
INITIAL_LEVELS = get_levels_for_skill(SCENARIOS, SKILLS[0])
INITIAL_SKILL = SKILLS[0]
INITIAL_LEVEL = INITIAL_LEVELS[0]

# Function to update scenario information
def get_scenario_info(skill, level, username):
    scenario = get_scenario(SCENARIOS, skill, level)
    scenario = format_scenario(scenario, username)
    return SCENARIO_INFO_FORMAT.format(**scenario).strip()

# Function to update levels when selecting a skill
def update_levels(skill, username):
    levels = get_levels_for_skill(SCENARIOS, skill)
    scenario_info = get_scenario_info(skill, levels[0], username)
    return gr.Dropdown(choices=levels, value=levels[0]), scenario_info

def start_scenario(skill, level, chatbot, username):
    # Validate inputs
    if (not skill) or (not level):
        raw_messages = [{"role": "assistant", "content": "Please select both skill and level first."}]
        return format_for_display(raw_messages), raw_messages, None, None
    
    scenario = get_scenario(SCENARIOS, skill, level)
    scenario = format_scenario(scenario, username)
    
    first_message = scenario['opening_setup']
    raw_messages = [{"role": "assistant", "content": first_message}]
    display_messages = format_for_display(raw_messages)
    
    goalchecker = ""
    return display_messages, raw_messages, scenario, goalchecker

# Function to format checker result into HTML
def checker_result_to_html(checker_result, prompt_type=None):
    # Complete status badge
    completed = checker_result['isGoalComplete']
    if completed:
        status_badge = "<div style='display:inline-block; background-color:#28a745; color:white; font-weight:bold; padding:5px 10px; border-radius:4px;'>COMPLETED ✓</div>"
    else:
        status_badge = "<div style='display:inline-block; background-color:#dc3545; color:white; font-weight:bold; padding:5px 10px; border-radius:4px;'>NOT COMPLETED ✗</div>"
    
    # Progress indicator with colored background
    progress = checker_result['goalProgress']
    progress_percent = progress * 10
    progress_bar = f"""
    <div style='margin-top:10px; background-color:#343a40; border-radius:6px; padding:2px;'>
        <div style='width:{progress_percent}%; background-color:#007bff; height:24px; border-radius:4px; text-align:center;'>
            <span style='color:white; font-weight:bold; line-height:24px;'>{progress}/10</span>
        </div>
    </div>
    """
    
    # Hint box with dark background
    hint = checker_result['hintHowToAchieveGoal']
    hint_box = f"""
    <div style='margin-top:15px; background-color:#17a2b8; border-radius:6px; padding:12px; color:white;'>
        <div style='font-weight:bold; margin-bottom:5px; font-size:16px;'>💡 HINT</div>
        <div>{hint}</div>
    </div>
    """
    
    # Prompt type indicator
    if prompt_type:
        if prompt_type == "positive":
            prompt_badge = "<div style='display:inline-block; background-color:#28a745; color:white; font-weight:bold; padding:5px 10px; border-radius:4px; margin-top:15px;'>🟢 POSITIVE PROMPT</div>"
        else:
            prompt_badge = "<div style='display:inline-block; background-color:#dc3545; color:white; font-weight:bold; padding:5px 10px; border-radius:4px; margin-top:15px;'>🔴 NEGATIVE PROMPT</div>"
    else:
        prompt_badge = ""
    
    # Build the complete HTML
    return f"""
    <div style='margin-top:20px; border-radius:8px; padding:20px; background-color:#212529; color:white;'>
        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;'>
            <div style='font-size:18px; font-weight:bold;'>GOAL STATUS</div>
            {status_badge}
        </div>
        <div style='margin:10px 0; font-weight:bold;'>PROGRESS</div>
        {progress_bar}
        {hint_box}
        {prompt_badge}
    </div>
    """

def bot_response(user_message, chatbot, raw_messages, scenario, username, goalchecker, 
                 response_temperature, response_model, checker_temperature, checker_model,
                 neg_prompt_threshold, initial_difficulty, difficulty_decay):
    if not scenario:
        return chatbot, raw_messages, scenario, goalchecker
    
    # Add user message to raw messages
    raw_messages.append({"role": "user", "content": user_message})
    
    # Calculate number of user messages
    n_user_messages = len([msg for msg in raw_messages if msg["role"] == "user"])
    
    last_prompt_type = None
    
    if n_user_messages < neg_prompt_threshold:
        system_prompt = '\n\n'.join([
            scenario["bot_personality"], 
            ROLEPLAY_SYSTEM_PROMPT_ADDITION.strip(), 
            scenario["neg_prompt"]
        ])
        last_prompt_type = "negative"
    else:
        goal_difficulty_p = max(0.1, initial_difficulty - (difficulty_decay * (n_user_messages // 5)))
        
        if random.random() > goal_difficulty_p:
            system_prompt = '\n\n'.join([
                scenario["bot_personality"], 
                ROLEPLAY_SYSTEM_PROMPT_ADDITION.strip(), 
                scenario["pos_prompt"]
            ])
            last_prompt_type = "positive"
        else:
            system_prompt = '\n\n'.join([
                scenario["bot_personality"], 
                ROLEPLAY_SYSTEM_PROMPT_ADDITION.strip(), 
                scenario["neg_prompt"]
            ])
            last_prompt_type = "negative"
    
    # Build messages for API call
    api_messages = [{"role": "system", "content": system_prompt}] + raw_messages
    
    # Call LLM API
    response = litellmapi.run(
        model=response_model,
        messages=api_messages,
        temperature=response_temperature,
        max_tokens=300,
        n_retries=3
    )
    bot_message = response["content"]

    # Add bot message to raw messages
    raw_messages.append({"role": "assistant", "content": bot_message})
    
    # Format for display
    display_messages = format_for_display(raw_messages)
    
    # Run goal checker if we have at least one user message
    if n_user_messages > 0:
        checker_result = checker.checker(
            chat_context=raw_messages,
            goal=scenario["goal_for_goal_checker"],
            username=username,
            botname=scenario["botname"],
            model=checker_model,
            bracket='quotation',
            temperature=checker_temperature,
        )
        goalchecker = checker_result_to_html(checker_result, last_prompt_type)
    
    return display_messages, raw_messages, scenario, goalchecker


with gr.Blocks(title="PosNeg Mode") as demo:
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Accordion("Settings", open=False):
                with gr.Tab("Response"):
                    response_temperature = gr.Slider(
                        minimum=0.1, 
                        maximum=1.0, 
                        value=0.7, 
                        step=0.1, 
                        label="Response Temperature", 
                        info="Controls randomness of bot responses (higher = more random)"
                    )
                    response_model = gr.Dropdown(
                        choices=AVAILABLE_MODELS,
                        label="Response Model",
                        info="Choose AI model for responses",
                        value=AVAILABLE_MODELS[0]
                    )
                with gr.Tab("Checker"):
                    checker_temperature = gr.Slider(
                        minimum=0.1, 
                        maximum=1.0, 
                        value=0.5, 
                        step=0.1, 
                        label="Checker Temperature", 
                        info="Controls randomness of checker responses (higher = more random)"
                    )
                    checker_model = gr.Dropdown(
                        choices=AVAILABLE_MODELS,
                        label="Checker Model",
                        info="Choose AI model for the checker",
                        value=AVAILABLE_MODELS[0]
                    )
                with gr.Tab("User"):
                    username = gr.Textbox(
                        label="Your name",
                        placeholder="Enter your name",
                        value="Vlad"
                    )
                with gr.Tab("Scenario"):
                    neg_prompt_threshold = gr.Slider(
                        minimum=1, 
                        maximum=10, 
                        value=5, 
                        step=1, 
                        label="Negative Prompt Threshold", 
                        info="Number of initial messages that always use negative prompts"
                    )
                    initial_difficulty = gr.Slider(
                        minimum=0.1, 
                        maximum=1.0, 
                        value=0.8, 
                        step=0.1, 
                        label="Initial Difficulty", 
                        info="Initial difficulty level (higher = harder to complete goal)"
                    )
                    difficulty_decay = gr.Slider(
                        minimum=0.0, 
                        maximum=0.2, 
                        value=0.1, 
                        step=0.01, 
                        label="Difficulty Decay Rate", 
                        info="How quickly difficulty decreases per 5 messages"
                    )
                
            skill_dropdown = gr.Dropdown(
                choices=SKILLS,
                label="Choose skill",
                info="The skill you want to train",
                value=None,
            )
            level_dropdown = gr.Dropdown(
                choices=INITIAL_LEVELS,
                label="Choose level",
                info="Difficulty level",
                value=None,
            )
            
            start_button = gr.Button("Start scenario")
            scenario_info = gr.Markdown(value="Choose skill and level")
        
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Chat",
                height=450,
                show_copy_button=True,
                render_markdown=True,
                type="messages"
            )
            msg = gr.Textbox(
                label="Your message",
                placeholder="Enter your message here...",
                show_label=False,
            )
            goalchecker = gr.HTML(value="")
    
    with gr.Row():
        clear = gr.Button("Clear chat", variant="stop")
    
    # STATES
    raw_messages = gr.State([])
    chosen_scenario = gr.State(None)
    
    # FUNCTIONS
    skill_dropdown.change(
        fn=update_levels,
        inputs=[skill_dropdown, username],
        outputs=[level_dropdown, scenario_info]
    )
    level_dropdown.change(
        fn=get_scenario_info,
        inputs=[skill_dropdown, level_dropdown, username],
        outputs=[scenario_info]
    )
    start_button.click(
        fn=start_scenario,
        inputs=[skill_dropdown, level_dropdown, chatbot, username],
        outputs=[chatbot, raw_messages, chosen_scenario, goalchecker]
    )
    msg.submit(
        fn=bot_response,
        inputs=[
            msg, chatbot, raw_messages, chosen_scenario, username, 
            goalchecker, response_temperature, response_model, 
            checker_temperature, checker_model,
            neg_prompt_threshold, initial_difficulty, difficulty_decay
        ],
        outputs=[chatbot, raw_messages, chosen_scenario, goalchecker],
    ).then(
        fn=lambda: "",
        inputs=None,
        outputs=msg,
    )
    clear.click(
        fn=lambda: ([], [], None, ""),
        inputs=None,
        outputs=[chatbot, raw_messages, chosen_scenario, goalchecker], 
        queue=False
    )

if __name__ == "__main__":
    demo.launch()
