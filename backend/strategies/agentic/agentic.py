import gradio as gr
import json
import re
import litellmapi
import hint
import transition
from pathlib import Path


# ROLEPLAY_SYSTEM_PROMPT_ADDITION = """
# Keep your responses concise - no more than 1 short sentences <= 10 words.
# Use expressive actions and emotions in *asterisks* to describe your actions.
# Stay in your role no matter what. Never break character or deviate from the personality.
# """

ROLEPLAY_SYSTEM_PROMPT_ADDITION = """
Keep your responses concise: no more than 1 short sentences <= 10 words.
Stay in your role no matter what. Never break character or deviate from the personality.
Respond only with the character's direct speech text, don't use *roleplay*.
Use life-like conversation patterns:
- Use natural speech fillers like "um", "well", "hmm", "you know" occasionally
- Leave thoughts unfinished sometimes or trail off with "..."
- Occasionally correct yourself mid-sentence as humans do
- Vary your response length and complexity based on emotional state (5-15 words)
- Sometimes answer questions with questions when feeling defensive or uncertain
- Don't always reply directly - occasionally change topics abruptly
- Use informal contractions and colloquialisms appropriate to your character
- Respond with surprise or confusion when appropriate instead of perfect knowledge
- Let your character's mood affect their communication style and engagement level

The user has the following ultimate goal in this conversation:
```
{frontend}
```
- Never directly mention this goal in your responses, but always keep it in mind.
- You should resist immediately fulfilling this goal.
- Don't outright refuse, but create meaningful resistance that requires user persistence and problem-solving.
- Maintain character authenticity while resisting - your resistance must align with your personality.
- Use emotional barriers (reluctance, hesitation, distrust) rather than logical refusals when possible.
"""


def load_scenarios():
    scenarios = []
    script_dir = Path(__file__).parent
    for file_path in script_dir.glob('*.json'):
        with open(file_path, "r") as f:
            scenario_data = json.load(f)
            scenarios.append(scenario_data)
    return scenarios


def get_scenario_by_skill_level(scenarios, skill, level):
    for scenario in scenarios:
        if (scenario["skill"] == skill) and (str(scenario["level"]) == level):
            return scenario.copy()
    raise ValueError(f"Scenario for skill {skill} and level {level} not found")


def generate_mermaid_diagram(states, current_state="START", visited_states=None):
    if visited_states is None:
        visited_states = [current_state]
        
    mermaid = ["```mermaid", "graph TD"]
    # nodes
    for state_name in states:
        if state_name in ["SUCCESS", "FAIL"]:
            shape = "([SUCCESS])" if state_name == "SUCCESS" else "([FAIL])"
            if state_name in visited_states:
                # Highlight visited terminal state in orange
                mermaid.append(f"    {state_name}{shape}:::visited")
            else:
                mermaid.append(f"    {state_name}{shape}")
        elif state_name in visited_states:
            # Highlight visited state in orange
            mermaid.append(f"    {state_name}[{state_name}]:::visited")
        else:
            mermaid.append(f"    {state_name}[{state_name}]")
    # transitions
    for state_name, state_data in states.items():
        if state_name in ["SUCCESS", "FAIL"]:
            # other states have transitions
            continue
        for target, target_data in state_data["transitions"].items():
            short_desc = target_data["shortDesc"]
            is_positive = target_data["isPositive"]
            arrow_style = "-->|🟢" if is_positive else "-.->|🔴"
            arrow_style += f" {short_desc}"
            arrow_style += "|"
            mermaid.append(f"    {state_name} {arrow_style} {target}")
    mermaid.append("    classDef visited fill:#FF9900,stroke:#FF6600,stroke-width:2px;")
    mermaid.append("```")
    return "\n".join(mermaid)


def format_scenario(scenario_or_item, username, botname):
    """Recursively formats all string fields in the scenario, replacing {username} and {botname} placeholders."""
    if isinstance(scenario_or_item, dict):
        return {k: format_scenario(v, username, botname) for k, v in scenario_or_item.items()}
    elif isinstance(scenario_or_item, list):
        return [format_scenario(item, username, botname) for item in scenario_or_item]
    elif isinstance(scenario_or_item, str):
        return scenario_or_item.format(botname=botname, username=username).strip()
    else:
        return scenario_or_item


SCENARIO_INFO_FORMAT = """
## 👤 Character Name 
{botname}

## ⚽️ Your Goal
{frontend}

## 🤖 Character You'll Talk With
{character}

## 💬 Starting Situation
{opening}
"""

AVAILABLE_MODELS = [
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "gemini/gemini-2.0-flash",
    "deepseek/deepseek-chat",
    "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
]

SCENARIOS = load_scenarios()
SCENARIO_NAMES = [scenario["name"] for scenario in SCENARIOS]
SKILLS = sorted(list(set([scenario["skill"] for scenario in SCENARIOS])))


def update_levels(skill):
    levels = sorted([scenario["level"] for scenario in SCENARIOS if scenario["skill"] == skill])
    return gr.Dropdown(choices=levels, value=None)


def update_scenario_info(skill, level, username):
    if (skill is None) or (level is None):
        return "", ""
    scenario = get_scenario_by_skill_level(SCENARIOS, skill, level)
    botname = scenario["botname"]
    scenario = format_scenario(scenario, username, botname)
    scenario_info = SCENARIO_INFO_FORMAT.format(**scenario).strip()
    mermaid_diagram = generate_mermaid_diagram(scenario["states"], "START")
    return scenario_info, mermaid_diagram


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
                formatted_parts.append(part)
        formatted_content = "<br>".join([p for p in formatted_parts if p.strip()])
        display_messages.append({"role": role, "content": formatted_content})
    return display_messages


def calculate_progress(states, current_state):
    # BFS
    def find_shortest_path(start_state) -> float:
        # Terminal states
        if start_state == "SUCCESS":
            return 0
        if start_state == "FAIL":
            return float('inf')
        queue, visited = [(start_state, 0)], {start_state}
        while queue:
            state, distance = queue.pop(0)   
            # Skip terminal states that don't have transitions
            if state in ["SUCCESS", "FAIL"]:
                continue
            transitions = states[state]["transitions"]
            for target_state in transitions:
                if target_state == "SUCCESS":
                    return distance + 1
                if target_state not in visited:
                    visited.add(target_state)
                    queue.append((target_state, distance + 1))
        raise ValueError(f"No path to SUCCESS from {start_state}")
    
    if current_state == "SUCCESS":
        return 10
    if current_state == "FAIL":
        return 1
    if current_state == "START":
        return 1
    
    current_to_success = find_shortest_path(current_state)
    start_to_success = find_shortest_path("START")
    print(f"current_to_success: {current_to_success}, start_to_success: {start_to_success}")
    assert current_to_success <= start_to_success, "Error: current_to_success > start_to_success"

    MAX_PROGRESS, MIN_PROGRESS = 10, 1
    progress = MIN_PROGRESS + (MAX_PROGRESS - MIN_PROGRESS) * (1 - current_to_success / start_to_success)
    return progress


def progress_to_html(states, current_state):
    progress = calculate_progress(states, current_state)
    progress_percent = progress * 10
    return f"""
    <div style='margin-top:20px; border-radius:8px; padding:20px; background-color:#212529; color:white;'>
        <div style='display:flex; justify-content:space-between; margin-bottom:5px;'>
            <div style='color:#ff3333; font-weight:bold;'>Not even close</div>
            <div style='color:#33cc33; font-weight:bold;'>Almost there!</div>
        </div>
        <div style='background-color:#343a40; border-radius:6px; padding:2px; position:relative;'>
            <div style='background:linear-gradient(to right, #ff3333, #ffcc00, #33cc33); height:24px; border-radius:4px; width:100%;'></div>
            <div style='position:absolute; top:0; left:{progress_percent}%; transform:translateX(-50%); width:10px; height:28px; background-color:white; border-radius:3px;'></div>
        </div>
    </div>
    """

def state_to_html(state):
    is_terminal = state["name"] in ["SUCCESS", "FAIL"]
    if is_terminal:
        bg_color = "#28a745" if state["name"] == "SUCCESS" else "#dc3545"
        icon = "✅" if state["name"] == "SUCCESS" else "❌"
        header_style = f"background-color:{bg_color};"
        header_content = f"{icon} {state['name']}"
    else:
        header_style = "background-color:#17a2b8;"
        header_content = state["name"]
    html = f"""
    <div style='background-color:#343a40; color:white; padding:15px; border-radius:8px; margin-top:15px;'>
        <h3 style='margin-top:0; text-align:center; {header_style} padding:10px; border-radius:6px; font-size:1.3em;'>{header_content}</h3>
    """
    if "prompt" in state:
        html += f"""<div style='background-color:#212529; padding:15px; border-radius:4px; margin-top:10px; white-space:pre-wrap;'>{state["prompt"]}</div>"""
    if not is_terminal and "transitions" in state and state["transitions"]:
        html += """
        <div style='margin-top:15px;'>
            <h4 style='color:#17a2b8; border-bottom:1px solid #17a2b8; padding-bottom:5px;'>Possible Transitions:</h4>
            <table style='width:100%; border-collapse:collapse;'>
                <tr style='background-color:#212529;'>
                    <th style='padding:8px; text-align:left; border-bottom:1px solid #495057;'>Target State</th>
                    <th style='padding:8px; text-align:center; border-bottom:1px solid #495057;'>Type</th>
                    <th style='padding:8px; text-align:left; border-bottom:1px solid #495057;'>Condition</th>
                </tr>
        """
        for target, transition in state["transitions"].items():
            html += f"""
            <tr style='border-bottom:1px solid #495057;'>
                <td style='padding:8px;'><span style='display:inline-block; padding:4px 8px; border-radius:4px; {'background-color:#17a2b8; color:white;' if target == "SUCCESS" or transition["isPositive"] else 'background-color:#dc3545; color:white;'}'>{target}</span></td>
                <td style='padding:8px; text-align:center;'>{'🟢' if target == "SUCCESS" or transition["isPositive"] else '🔴'}<br><small>{'Positive' if target == "SUCCESS" or transition["isPositive"] else 'Negative'}</small></td>
                <td style='padding:8px;'>
                    <div style='font-weight:bold; margin-bottom:3px;'>{transition["shortDesc"]}</div>
                    <div style='font-size:0.9em; color:#adb5bd;'>{transition["condition"]}</div>
                </td>
            </tr>
            """
        html += """
            </table>
        </div>
        """
    if is_terminal:
        message = "Scenario completed successfully!" if state["name"] == "SUCCESS" else "Scenario failed!"
        icon = "✅" if state["name"] == "SUCCESS" else "❌"
        html += f"""
        <div style='text-align:center; font-size:1.2em; margin-top:15px;'>
            {icon} {message}
        </div>
        """
    html += "</div>"
    return html


def start(skill, level, username, hint_model, hint_temperature):   
    # initialize scenario
    scenario = get_scenario_by_skill_level(SCENARIOS, skill, level)
    scenario = format_scenario(scenario, username, scenario["botname"])
    scenario["current_state"] = "START"
    current_state = scenario["current_state"]
    # write opening message to messages
    messages = [{"role": "assistant", "content": scenario['opening']}]
    chatbot = format_for_display(messages)
    # state info, mermaid diagram, progress info, hint info
    state = scenario["states"][current_state]
    state_info_html = state_to_html(state)
    mermaid_diagram = generate_mermaid_diagram(scenario["states"], current_state)
    progress_info_html = progress_to_html(scenario["states"], current_state)
    hint_info_html = hint_to_html(messages, scenario, username, hint_model, hint_temperature)
    transition_info_html = ""

    return (
        chatbot, 
        messages, 
        scenario, 
        progress_info_html, 
        state_info_html, 
        gr.update(interactive=True, placeholder="Enter your message here..."), 
        gr.update(interactive=True), 
        hint_info_html,
        transition_info_html,
        mermaid_diagram
    )


def response(
    user_message, messages, scenario, username, progress_info_html,
    response_model, response_temperature, transition_model,
    transition_temperature, hint_model, hint_temperature,
):
    messages.append({"role": "user", "content": user_message})

    # transition
    state = scenario["states"][scenario["current_state"]]  # can't be terminal state
    transitionjson = transition.transition(
        chat_context=messages,
        system_prompt=scenario["character"],
        state_prompt=state["prompt"],  # all non-terminal states have prompt
        transitions=state["transitions"],  # all non-terminal states have transitions
        username=username, 
        botname=scenario["botname"],
        model=transition_model,
        temperature=transition_temperature,
        bracket='quotation'
    )

    # if transition occurred
    if transitionjson['is_transition']:
        assert transitionjson['to_state'] in scenario["states"], "Error: transition to non-existent state"
        scenario["current_state"] = transitionjson['to_state']
        state = scenario["states"][scenario["current_state"]]
        transition_info_html = f"""
        <div style='background-color:#4CAF50; color:white; padding:12px; border-radius:6px; margin-top:10px;'>
            <strong>TRANSITION OCCURRED:</strong> {transitionjson['to_state']}
            <div style='margin-top:5px;'>{transitionjson['explanation']}</div>
        </div>
        """
    else:
        transition_info_html = ""
    
    # update state info and mermaid diagram
    state_info_html = state_to_html(state)
    mermaid_diagram = generate_mermaid_diagram(scenario["states"], scenario["current_state"])

    # LLM
    system_prompt = '\n\n'.join([
        scenario["character"],
        state["prompt"],  # all states have prompt
        ROLEPLAY_SYSTEM_PROMPT_ADDITION.strip(),
    ])
    bot_response = litellmapi.run(
        messages=[{"role": "system", "content": system_prompt}] + messages,
        model=response_model,
        temperature=response_temperature,
        max_tokens=300,
        n_retries=3
    )["content"]
    messages.append({"role": "assistant", "content": bot_response})
    chatbot = format_for_display(messages)

    # terminal state
    if scenario["current_state"] in ["SUCCESS", "FAIL"]:
        game_over_message = {
            "SUCCESS": f"🎉 Congratulations! You've successfully completed the scenario!",
            "FAIL": f"❌ Game over. You didn't complete the scenario."
        }[scenario["current_state"]]
        progress_info_html = f"""
        <div style='margin-top:20px; border-radius:8px; padding:20px; background-color:#212529; color:white;'>
            <div style='font-weight:bold; text-align:center; font-size:1.2em; margin-bottom:10px;'>{game_over_message}</div>
            <div style='background-color:#343a40; border-radius:6px; padding:2px; position:relative;'>
                <div style='background:linear-gradient(to right, #ff3333, #ffcc00, #33cc33); height:24px; border-radius:4px; width:100%;'></div>
                <div style='position:absolute; top:0; left:{100 if scenario["current_state"] == "SUCCESS" else 0}%; transform:translateX(-50%); width:10px; height:28px; background-color:white; border-radius:3px;'></div>
            </div>
        </div>
        """
        return (
            chatbot, 
            messages, 
            scenario, 
            progress_info_html, 
            state_info_html,
            mermaid_diagram,
            gr.update(interactive=False, placeholder="Scenario completed."), 
            gr.update(interactive=False), 
            "",
            "",
        )
    else:
        progress_info_html = progress_to_html(scenario["states"], scenario["current_state"])
        hint_info_html = hint_to_html(messages, scenario, username, hint_model, hint_temperature)
        return (
            chatbot, 
            messages, 
            scenario, 
            progress_info_html,
            state_info_html, 
            mermaid_diagram,
            gr.update(interactive=True),  # Text input remains active
            gr.update(interactive=True),  # Hint button remains active
            hint_info_html,
            transition_info_html,
        )


def hint_to_html(messages, scenario, username, model, temperature):
    current_state = scenario["current_state"]
    state = scenario["states"][current_state]
    hintjson = hint.hint(
        chat_context=messages,
        transitions=state["transitions"],
        username=username,
        botname=scenario["botname"],
        system_prompt=scenario["character"],
        state_prompt=state["prompt"],
        model=model,
        goal=scenario["frontend"],
        bracket='quotation',
        temperature=temperature
    )
    html = f"""
    <div style='background-color:#fff3cd; border-left:5px solid #ffc107; padding:15px; border-radius:6px; margin-top:15px;'>
        <div style='display:flex; align-items:center; margin-bottom:10px;'>
            <div style='background-color:#ffc107; padding:8px; border-radius:50%; margin-right:12px;'>
                <span style='font-size:1.2em;'>💡</span>
            </div>
            <h3 style='margin:0; color:#856404;'>Hint</h3>
        </div>
        <div style='margin-bottom:15px;'>
            <div style='font-size:1.1em; font-weight:bold; margin-bottom:8px; color:#533f03;'>
                <span style='color:#28a745;'>✅ Try this:</span> {hintjson['hintWhatToDo']}
            </div>
            <div style='font-size:1.1em; font-weight:bold; margin-bottom:8px; color:#533f03;'>
                <span style='color:#dc3545;'>❌ Avoid this:</span> {hintjson['hintWhatToAvoid']}
            </div>
            <div style='font-size:1.1em; font-weight:bold; margin-bottom:8px; color:#533f03;'>
                <span style='color:#dc3545;'>⚠️ Current issues:</span> {hintjson['wrongActions']}
            </div>
        </div>
        <div style='font-size:0.9em; color:#6c757d; font-style:italic; border-top:1px solid #ffeeba; padding-top:8px;'>
            {hintjson['explanation']}
        </div>
    </div>
    """
    return html

with gr.Blocks(title="Agentic Mode") as demo:
    with gr.Row():
        with gr.Column(scale=1):
            mermaid_diagram = gr.Markdown(value="Select a scenario to view its state diagram")
            state_info_html = gr.HTML(value="")
        
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(
                label="Chat",
                height=450,
                show_copy_button=True,
                render_markdown=True,
                type="messages"
            )
            msg = gr.Textbox(
                label="Your message",
                placeholder="Start a scenario first to begin chatting...",
                show_label=False,
                interactive=False
            )
            hint_button = gr.Button("Get Hint", variant="secondary", interactive=False)
            hint_info_html = gr.HTML(value="")
            transition_info_html = gr.HTML(value="")
            progress_info_html = gr.HTML(value="")

    # Scenario selection accordion
    scenario_accordion = gr.Accordion("Choose Scenario", open=True)
    with scenario_accordion:
        with gr.Row():
            # Left column for scenario selection
            with gr.Column(scale=1):
                skill_dropdown = gr.Dropdown(
                    choices=SKILLS,
                    label="Choose skill",
                    info="The skill you want to train",
                    value=None,
                )
                level_dropdown = gr.Dropdown(
                    choices=[],
                    label="Choose level",
                    info="Difficulty level",
                    value=None,
                )
                start_button = gr.Button("(Re) Start Scenario", interactive=False)
                
            # Right column for scenario info
            with gr.Column(scale=1):
                scenario_info = gr.Markdown(value="Choose skill and level")
    
    # Settings at the bottom
    with gr.Accordion("Settings", open=False):
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### Response Model")
                    response_model = gr.Dropdown(
                        choices=AVAILABLE_MODELS,
                        label="Model",
                        info="AI model for bot responses",
                        value=AVAILABLE_MODELS[0]
                    )
                    response_temperature = gr.Slider(
                        minimum=0.1, 
                        maximum=2.0, 
                        value=1.0, 
                        step=0.1, 
                        label="Temperature", 
                        info="Randomness (higher = more random)"
                    )
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### Transition Model")
                    transition_model = gr.Dropdown(
                        choices=AVAILABLE_MODELS,
                        label="Model",
                        info="AI model for state transitions",
                        value=AVAILABLE_MODELS[0]
                    )
                    transition_temperature = gr.Slider(
                        minimum=0.1, 
                        maximum=2.0, 
                        value=0.0, 
                        step=0.1, 
                        label="Temperature", 
                        info="Randomness (higher = more random)"
                    )
            with gr.Column(scale=1):
                with gr.Group():
                    gr.Markdown("### Hint Model")
                    hint_model = gr.Dropdown(
                        choices=AVAILABLE_MODELS,
                        label="Model",
                        info="AI model for hints",
                        value=AVAILABLE_MODELS[0]
                    )
                    hint_temperature = gr.Slider(
                        minimum=0.1, 
                        maximum=2.0, 
                        value=0.5, 
                        step=0.1, 
                        label="Temperature", 
                        info="Randomness (higher = more random)"
                    )
            with gr.Column(scale=1):
                username = gr.Textbox(
                    label="Your name",
                    placeholder="Enter your name",
                    value="Vlad"
                )
    
    # STATES
    raw_messages = gr.State([])
    chosen_scenario = gr.State(None)
    
    # FUNCTIONS
    skill_dropdown.change(
        fn=lambda skill, level: gr.update(interactive=bool(skill and level)),
        inputs=[skill_dropdown, level_dropdown],
        outputs=start_button
    )
    level_dropdown.change(
        fn=lambda skill, level: gr.update(interactive=bool(skill and level)),
        inputs=[skill_dropdown, level_dropdown],
        outputs=start_button
    )
    skill_dropdown.change(
        fn=update_levels,
        inputs=[skill_dropdown],
        outputs=[level_dropdown]
    )
    level_dropdown.change(
        fn=update_scenario_info,
        inputs=[skill_dropdown, level_dropdown, username],
        outputs=[scenario_info, mermaid_diagram]
    )
    start_button.click(
        fn=start,
        inputs=[skill_dropdown, level_dropdown, username, hint_model, hint_temperature],
        outputs=[chatbot, raw_messages, chosen_scenario, progress_info_html, state_info_html, msg, hint_button, hint_info_html, transition_info_html, mermaid_diagram],
    ).then(
        # After scenario starts, close the scenario accordion
        fn=lambda: gr.update(open=False),
        inputs=None,
        outputs=scenario_accordion
    )
    msg.submit(
        fn=response,
        inputs=[
            msg, raw_messages, chosen_scenario, username, 
            progress_info_html, response_model, response_temperature,
            transition_model, transition_temperature, hint_model, hint_temperature
        ],
        outputs=[
            chatbot, raw_messages, chosen_scenario, progress_info_html,
            state_info_html, mermaid_diagram, msg, hint_button, hint_info_html,
            transition_info_html
        ],
    ).then(
        fn=lambda: "",
        inputs=None,
        outputs=msg,
    )
    hint_button.click(
        fn=hint_to_html,
        inputs=[raw_messages, chosen_scenario, username, hint_model, hint_temperature],
        outputs=[hint_info_html]
    )

if __name__ == "__main__":
    demo.launch()
