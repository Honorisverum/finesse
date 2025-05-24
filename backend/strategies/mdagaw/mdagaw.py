import gradio as gr
import json
import re
import litellmapi
import hint
import transition
import checker
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


def generate_mermaid_diagram(scenario, visited_states=None):
    """Generate Mermaid diagram based on scenario structure"""
    if visited_states is None:
        visited_states = []
        
    mermaid = ["```mermaid", "graph TD"]
    
    # Process states from all branches
    branch_states = {}
    
    # Add states from branches
    for branch_name, branch_states_dict in scenario["states"].items():
        if branch_name not in branch_states:
            branch_states[branch_name] = []
            
        for state_name, state_data in branch_states_dict.items():
            branch_states[branch_name].append(state_name)
            
            # Node style based on state
            if state_name in visited_states:
                mermaid.append(f"    {state_name}[{state_name}]:::visited")
            else:
                mermaid.append(f"    {state_name}[{state_name}]")
    
    # Add terminal states
    for state_name, state_data in scenario["tstates"].items():
        shape = "([SUCCESS])" if state_name == "SUCCESS" else "([FAIL])"
        
        if state_name in visited_states:
            mermaid.append(f"    {state_name}{shape}:::visited")
        else:
            mermaid.append(f"    {state_name}{shape}")
    
    # Add START state
    if "START" in visited_states:
        mermaid.append(f"    START[START]:::visited")
    else:
        mermaid.append(f"    START[START]")
    
    # Add subgraphs for branches
    for branch_name, states in branch_states.items():
        mermaid.append(f"    subgraph {branch_name}")
        for state in states:
            mermaid.append(f"        {state}")
        mermaid.append("    end")
    
    # Process transitions from branches
    for branch_name, branch_states_dict in scenario["states"].items():
        for state_name, state_data in branch_states_dict.items():
            if "transitions" not in state_data:
                continue
                
            for target, transition_data in state_data["transitions"].items():
                # Skip blocked transitions
                if "isBlocked" in transition_data and transition_data["isBlocked"]:
                    continue
                
                # Arrow style based on transition type
                transition_type = transition_data["type"]
                arrow_style = "-->" if transition_type == "parallel" else "==>"
                
                # Arrow label - transition condition
                condition = transition_data["condition"]
                arrow_label = f"|{condition}|"
                mermaid.append(f"    {state_name} {arrow_style}{arrow_label} {target}")
    
    # Add implicit transitions from START to initial states in each branch
    for branch_name, branch_states_dict in scenario["states"].items():
        for state_name, state_data in branch_states_dict.items():
            if "condition" in state_data:
                has_incoming = False
                
                # Check if state has any incoming transitions
                for _, other_states in scenario["states"].items():
                    for _, other_state_data in other_states.items():
                        if "transitions" in other_state_data:
                            if state_name in other_state_data["transitions"]:
                                has_incoming = True
                                break
                
                if not has_incoming:
                    condition = state_data["condition"]
                    mermaid.append(f"    START -->|{condition}| {state_name}")
    
    # Add implicit transitions to terminal states
    for state_name, state_data in scenario["tstates"].items():
        if "condition" in state_data:
            mermaid.append(f"    GLOBAL -->|{state_data['condition']}| {state_name}")
    
    # Add styling classes
    mermaid.append("    classDef visited fill:#90EE90,stroke:#228B22,stroke-width:1px;")
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
{goal}

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
    mermaid_diagram = generate_mermaid_diagram(scenario, ["START"])
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


def progress_to_html(progress, is_terminal=False, is_success=False):
    """Format progress information as HTML"""
    progress = round(progress, 2)
    progress_text = f"{progress * 100:.1f}%"
    
    # Determine progress bar color based on state
    if is_terminal:
        color = "#4CAF50" if is_success else "#F44336"
    else:
        color = "#2196F3"
    
    # Apply styling based on progress
    if progress >= 1.0:
        width = "100%"
    else:
        width = f"{progress * 100:.1f}%"
    
    html = f"""
    <div style="width: 100%; background-color: #ddd; border-radius: 5px; margin: 10px 0;">
        <div style="width: {width}; height: 20px; background-color: {color}; border-radius: 5px; text-align: center; color: white; line-height: 20px; font-weight: bold;">
            {progress_text}
        </div>
    </div>
    """
    
    return html


def check_progress(messages, scenario, username, model="openai/gpt-4o-mini", temperature=0.0):
    """Check progress toward goal using checker.py"""
    checker_result = checker.checker(
        chat_context=messages,
        goal=scenario["goal"],
        username=username,
        botname=scenario["botname"],
        model=model,
        temperature=temperature
    )
    
    return checker_result["goalProgress"]


def hint_to_html(messages, scenario, username, model, temperature):
    """Generate hint HTML using hint.py"""
    if not messages:
        return ""
        
    goal = scenario["goal"]
        
    hint_result = hint.hint(
        chat_context=messages,
        goal=goal,
        username=username,
        botname=scenario["botname"],
        model=model,
        temperature=temperature
    )
    
    hint_text = hint_result["hintHowToAchieveGoal"]
    explanation = hint_result["LLMexplainDecision"]
    progress = hint_result.get("goalProgress", 0.5)  # Default to mid-progress if not provided
    
    html = f"""
    <div style='background-color:#fff3cd; border-left:5px solid #ffc107; padding:15px; border-radius:6px; margin-top:15px;'>
        <div style='display:flex; align-items:center; margin-bottom:10px;'>
            <div style='background-color:#ffc107; padding:8px; border-radius:50%; margin-right:12px;'>
                <span style='font-size:1.2em;'>💡</span>
            </div>
            <h3 style='margin:0; color:#856404;'>Hint (Progress: {progress}/10)</h3>
        </div>
        <div style='margin-bottom:15px;'>
            <div style='font-size:1.1em; font-weight:bold; margin-bottom:8px; color:#533f03;'>
                <span style='color:#28a745;'>✅ Try this:</span> {hint_text}
            </div>
        </div>
        <div style='font-size:0.9em; color:#6c757d; font-style:italic; border-top:1px solid #ffeeba; padding-top:8px;'>
            {explanation}
        </div>
    </div>
    """
    return html


def active_states_to_html(scenario):
    """Generate HTML for displaying all active states and possible transitions from them."""
    active_states = scenario["visited_states"]
    
    # Start HTML container
    html = f"""
    <div style='background-color:#343a40; color:white; padding:15px; border-radius:8px; margin-top:15px;'>
        <h3 style='margin-top:0; text-align:center; background-color:#17a2b8; padding:10px; border-radius:6px; font-size:1.3em;'>Active States & Possible Transitions</h3>
    """
    
    # Find all active non-terminal states
    active_non_terminal_states = []
    for state_name in active_states:
        if state_name == "START":
            continue
        
        if state_name in ["SUCCESS", "FAIL"]:
            continue
            
        # Find state data in branches
        for branch_name, branch_states in scenario["states"].items():
            if state_name in branch_states:
                active_non_terminal_states.append({
                    "name": state_name,
                    "branch": branch_name,
                    "data": branch_states[state_name]
                })
                break
    
    # If no active states yet, show initial branch states
    if not active_non_terminal_states:
        html += """
        <div style='background-color:#212529; padding:15px; border-radius:4px; margin-top:10px;'>
            <p style='margin:0;'>No active states yet. The conversation can activate initial states based on conditions.</p>
        </div>
        """
        
        # Find initial states
        initial_states = []
        for branch_name, branch_states in scenario["states"].items():
            for state_name, state_data in branch_states.items():
                # Check if this is an initial state (no incoming transitions)
                has_incoming = False
                
                for _, other_branch_states in scenario["states"].items():
                    for _, other_state_data in other_branch_states.items():
                        if "transitions" in other_state_data:
                            if state_name in other_state_data["transitions"]:
                                has_incoming = True
                                break
                
                if not has_incoming and "condition" in state_data:
                    initial_states.append({
                        "name": state_name,
                        "branch": branch_name,
                        "condition": state_data["condition"]
                    })
        
        if initial_states:
            html += """
            <div style='margin-top:15px;'>
                <h4 style='color:#17a2b8; border-bottom:1px solid #17a2b8; padding-bottom:5px;'>Available Initial States:</h4>
                <table style='width:100%; border-collapse:collapse;'>
                    <tr style='background-color:#212529;'>
                        <th style='padding:8px; text-align:left; border-bottom:1px solid #495057;'>Branch</th>
                        <th style='padding:8px; text-align:left; border-bottom:1px solid #495057;'>State</th>
                        <th style='padding:8px; text-align:left; border-bottom:1px solid #495057;'>Activation Condition</th>
                    </tr>
            """
            
            for state in initial_states:
                html += f"""
                <tr style='border-bottom:1px solid #495057;'>
                    <td style='padding:8px;'>{state["branch"]}</td>
                    <td style='padding:8px;'><span style='display:inline-block; padding:4px 8px; border-radius:4px; background-color:#17a2b8; color:white;'>{state["name"]}</span></td>
                    <td style='padding:8px;'>{state["condition"]}</td>
                </tr>
                """
            
            html += """
                </table>
            </div>
            """
    
    # For each active state, show its info and transitions
    for state in active_non_terminal_states:
        state_name = state["name"]
        state_data = state["data"]
        branch_name = state["branch"]
        
        html += f"""
        <div style='margin-top:20px; border-top:1px solid #495057; padding-top:15px;'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
                <h4 style='margin:0; color:#17a2b8;'>{state_name}</h4>
                <span style='background-color:#212529; padding:3px 8px; border-radius:4px; font-size:0.8em;'>Branch: {branch_name}</span>
            </div>
        """
        
        # Add prompt information
        if "addprompt" in state_data:
            html += f"""<div style='background-color:#212529; padding:10px; border-radius:4px; margin-top:10px; font-size:0.9em;'><strong>Prompt:</strong> {state_data["addprompt"]}</div>"""
        
        # Add transitions
        if "transitions" in state_data and state_data["transitions"]:
            html += """
            <div style='margin-top:10px;'>
                <h5 style='color:#17a2b8; margin-bottom:5px;'>Possible Transitions:</h5>
                <table style='width:100%; border-collapse:collapse; font-size:0.9em;'>
                    <tr style='background-color:#212529;'>
                        <th style='padding:6px; text-align:left; border-bottom:1px solid #495057;'>Target</th>
                        <th style='padding:6px; text-align:center; border-bottom:1px solid #495057;'>Type</th>
                        <th style='padding:6px; text-align:left; border-bottom:1px solid #495057;'>Condition</th>
                    </tr>
            """
            
            for target, transition in state_data["transitions"].items():
                # Skip blocked transitions
                if transition.get("isBlocked", False):
                    continue
                
                # Determine transition type and style
                transition_type = transition.get("type", "parallel")
                is_positive = target == "SUCCESS" or transition.get("isPositive", True)
                
                html += f"""
                <tr style='border-bottom:1px solid #495057;'>
                    <td style='padding:6px;'><span style='display:inline-block; padding:3px 6px; border-radius:3px; {'background-color:#28a745; color:white;' if is_positive else 'background-color:#dc3545; color:white;'}'>{target}</span></td>
                    <td style='padding:6px; text-align:center;'>{transition_type.title()}</td>
                    <td style='padding:6px;'>{transition["condition"]}</td>
                </tr>
                """
            
            html += """
                </table>
            </div>
            """
        else:
            html += """<div style='margin-top:10px; font-style:italic; color:#6c757d;'>No outgoing transitions available.</div>"""
            
        html += "</div>"
    
    # Check for any terminal states
    terminal_states = [state for state in active_states if state in ["SUCCESS", "FAIL"]]
    if terminal_states:
        html += """
        <div style='margin-top:20px; border-top:1px solid #495057; padding-top:15px;'>
            <h4 style='color:#17a2b8; margin-bottom:10px;'>Terminal States Reached:</h4>
        """
        
        for terminal_state in terminal_states:
            is_success = terminal_state == "SUCCESS"
            color = "#28a745" if is_success else "#dc3545"
            icon = "✅" if is_success else "❌"
            
            # Get terminal state data
            state_data = None
            if "tstates" in scenario and terminal_state in scenario["tstates"]:
                state_data = scenario["tstates"][terminal_state]
            
            html += f"""
            <div style='background-color:{color}; color:white; padding:10px; border-radius:4px; margin-bottom:10px;'>
                <div style='font-weight:bold;'>{icon} {terminal_state}</div>
            """
            
            if state_data and "addprompt" in state_data:
                html += f"""<div style='margin-top:5px; font-size:0.9em;'>{state_data["addprompt"]}</div>"""
                
            html += "</div>"
            
        html += "</div>"
    
    # Add global transitions
    if "tstates" in scenario:
        available_terminal_states = []
        
        for terminal_state, state_data in scenario["tstates"].items():
            if terminal_state not in active_states and "condition" in state_data:
                available_terminal_states.append({
                    "name": terminal_state,
                    "condition": state_data["condition"],
                    "is_success": terminal_state == "SUCCESS"
                })
        
        if available_terminal_states:
            html += """
            <div style='margin-top:20px; border-top:1px solid #495057; padding-top:15px;'>
                <h4 style='color:#17a2b8; margin-bottom:10px;'>Global Terminal Conditions:</h4>
                <table style='width:100%; border-collapse:collapse; font-size:0.9em;'>
                    <tr style='background-color:#212529;'>
                        <th style='padding:6px; text-align:left; border-bottom:1px solid #495057;'>Terminal State</th>
                        <th style='padding:6px; text-align:left; border-bottom:1px solid #495057;'>Condition</th>
                    </tr>
            """
            
            for state in available_terminal_states:
                html += f"""
                <tr style='border-bottom:1px solid #495057;'>
                    <td style='padding:6px;'><span style='display:inline-block; padding:3px 6px; border-radius:3px; {'background-color:#28a745; color:white;' if state["is_success"] else 'background-color:#dc3545; color:white;'}'>{state["name"]}</span></td>
                    <td style='padding:6px;'>{state["condition"]}</td>
                </tr>
                """
            
            html += """
                </table>
            </div>
            """
    
    html += "</div>"
    return html


def start(skill, level, username):   
    # Initialize scenario
    scenario = get_scenario_by_skill_level(SCENARIOS, skill, level)
    scenario = format_scenario(scenario, username, scenario["botname"])
    scenario["visited_states"] = ["START"]
    
    # Create first assistant message
    messages = [{"role": "assistant", "content": scenario['opening']}]
    chatbot = format_for_display(messages)
    
    # Generate active states info
    states_info_html = active_states_to_html(scenario)
    mermaid_diagram = generate_mermaid_diagram(scenario, scenario["visited_states"])
    progress_info_html = ""
    msg = gr.update(interactive=True, placeholder="Enter your message here...")
    hint_info_html = ""
    transition_info_html = ""

    return (
        chatbot, 
        messages, 
        scenario, 
        progress_info_html, 
        states_info_html, 
        msg, 
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

    # Collect all potential transitions from active states
    active_states = scenario["visited_states"]
    
    all_transitions = {}
    transition_sources = {}
    
    # Collect transitions from regular states in branches
    for branch_name, branch_states in scenario["states"].items():
        for state_name, state_data in branch_states.items():
            if state_name not in active_states:
                # Check for initial states with activation conditions
                if "condition" in state_data:
                    has_incoming = False
                    
                    # Check if this state has any incoming transitions
                    for _, other_branch_states in scenario["states"].items():
                        for _, other_state_data in other_branch_states.items():
                            if "transitions" in other_state_data:
                                if state_name in other_state_data["transitions"]:
                                    has_incoming = True
                                    break
                    
                    if not has_incoming:
                        # This is an initial branch state
                        transition_key = f"INITIAL:{state_name}"
                        all_transitions[transition_key] = {
                            "condition": state_data["condition"],
                            "type": "parallel",
                            "shortDesc": f"Activate initial state {state_name}"
                        }
                        transition_sources[transition_key] = "INITIAL"
                
                continue  # Skip inactive states
                
            if "transitions" not in state_data:
                continue
                
            for target, transition_data in state_data["transitions"].items():
                # Skip blocked transitions
                if "isBlocked" in transition_data and transition_data["isBlocked"]:
                    continue
                
                # Add this potential transition
                transition_key = f"{state_name}:{target}"
                all_transitions[transition_key] = {
                    "condition": transition_data["condition"],
                    "isPositive": target == "SUCCESS" or transition_data.get("isPositive", True),
                    "type": transition_data["type"],
                    "shortDesc": transition_data.get("shortDesc", f"Transition to {target}")
                }
                transition_sources[transition_key] = state_name
    
    # Add terminal state conditions if not already visited
    if "tstates" in scenario:
        for terminal_state, terminal_data in scenario["tstates"].items():
            if terminal_state not in scenario["visited_states"] and "condition" in terminal_data:
                transition_key = f"GLOBAL:{terminal_state}"
                all_transitions[transition_key] = {
                    "condition": terminal_data["condition"],
                    "isPositive": terminal_state == "SUCCESS",
                    "shortDesc": f"Reach {terminal_state}"
                }
                transition_sources[transition_key] = "GLOBAL"
    
    # Make transition checks
    transitions_to_check = {}
    for transition_key, transition_data in all_transitions.items():
        target_state = transition_key.split(':')[1]
        transitions_to_check[target_state] = transition_data
    
    # Check for transitions
    transition_info_html = ""
    target_state = None
    from_state = None
    
    if transitions_to_check:
        # Get base system prompt
        character_prompt = scenario.get("character", "")
        state_prompt = ""
        
        # Get additional prompts from active states
        for active_state in active_states:
            if active_state == "START":
                continue
                
            for branch_name, branch_states in scenario["states"].items():
                if active_state in branch_states:
                    if "addprompt" in branch_states[active_state]:
                        state_prompt += "\n\n" + branch_states[active_state]["addprompt"]
        
        transitionjson = transition.transition(
            chat_context=messages,
            system_prompt=character_prompt,
            state_prompt=state_prompt,
            transitions=transitions_to_check,
            username=username, 
            botname=scenario["botname"],
            model=transition_model,
            temperature=transition_temperature,
            bracket='quotation'
        )
        
        # Process transition results
        if transitionjson['is_transition']:
            target_state = transitionjson['to_state']
            
            # Find the matching transition key
            for key in all_transitions:
                if key.endswith(f":{target_state}"):
                    from_state = transition_sources[key]
                    break
            
            # Add the target state to visited states
            if target_state not in scenario["visited_states"]:
                scenario["visited_states"].append(target_state)
            
            # Handle special case for initial state transitions
            if from_state == "INITIAL":
                transition_info_html = f"""
                <div style='background-color:#4CAF50; color:white; padding:12px; border-radius:6px; margin-top:10px;'>
                    <strong>INITIAL STATE ACTIVATED:</strong> {target_state}
                    <div style='margin-top:5px;'>{transitionjson['explanation']}</div>
                </div>
                """
            
            # Handle fork transitions
            elif from_state != "GLOBAL":
                for branch_name, branch_states in scenario["states"].items():
                    if from_state in branch_states:
                        source_state = branch_states[from_state]
                        if "transitions" in source_state and target_state in source_state["transitions"]:
                            if source_state["transitions"][target_state].get("type") == "fork":
                                # Block other transitions from this fork state
                                for other_target in source_state["transitions"]:
                                    if other_target != target_state:
                                        source_state["transitions"][other_target]["isBlocked"] = True
            
                # Create transition info HTML for regular transitions
                transition_info_html = f"""
                <div style='background-color:#4CAF50; color:white; padding:12px; border-radius:6px; margin-top:10px;'>
                    <strong>TRANSITION OCCURRED:</strong> {from_state} → {target_state}
                    <div style='margin-top:5px;'>{transitionjson['explanation']}</div>
                </div>
                """
            
            # Terminal state HTML
            if target_state in ["SUCCESS", "FAIL"]:                
                transition_info_html = f"""
                <div style='background-color:{"#28a745" if target_state == "SUCCESS" else "#dc3545"}; color:white; padding:12px; border-radius:6px; margin-top:10px;'>
                    <strong>TERMINAL STATE REACHED:</strong> {target_state}
                    <div style='margin-top:5px;'>{transitionjson['explanation']}</div>
                </div>
                """
    
    # Generate active states HTML
    states_info_html = active_states_to_html(scenario)
    
    # Calculate progress using checker.py
    progress = check_progress(messages, scenario, username, hint_model, hint_temperature)
    
    # Update state diagram
    mermaid_diagram = generate_mermaid_diagram(scenario, scenario["visited_states"])

    # Build accumulated system prompt
    accumulated_prompt = scenario["character"]
    if "negprompt" in scenario:
        accumulated_prompt += "\n\n" + scenario["negprompt"]
    
    # Add prompts from visited states
    for state_name in scenario["visited_states"]:
        if state_name == "START":
            continue
        
        state_prompt = None
        
        # Get prompt from terminal states
        if state_name in ["SUCCESS", "FAIL"] and "tstates" in scenario:
            if "addprompt" in scenario["tstates"][state_name]:
                state_prompt = scenario["tstates"][state_name]["addprompt"]
        
        # Or from branch states
        if not state_prompt:
            for branch_name, branch_states in scenario["states"].items():
                if state_name in branch_states and "addprompt" in branch_states[state_name]:
                    state_prompt = branch_states[state_name]["addprompt"]
                    break
        
        if state_prompt:
            accumulated_prompt += "\n\n" + state_prompt
    
    # Add roleplay system prompt
    system_prompt = accumulated_prompt + "\n\n" + ROLEPLAY_SYSTEM_PROMPT_ADDITION
    
    # Get bot response
    bot_response = litellmapi.run(
        messages=[{"role": "system", "content": system_prompt}] + messages,
        model=response_model,
        temperature=response_temperature,
        max_tokens=300,
        n_retries=3
    )["content"]
    
    messages.append({"role": "assistant", "content": bot_response})
    chatbot = format_for_display(messages)

    # Handle terminal state
    most_recent_state = scenario["visited_states"][-1] if scenario["visited_states"] else "START"
    if most_recent_state in ["SUCCESS", "FAIL"]:
        is_success = most_recent_state == "SUCCESS" 
        progress_info_html = progress_to_html(1.0, True, is_success)
        
        return (
            chatbot, 
            messages, 
            scenario, 
            progress_info_html, 
            states_info_html,
            mermaid_diagram,
            gr.update(interactive=False, placeholder="Scenario completed."), 
            "",
            transition_info_html,
        )
    else:
        progress_info_html = progress_to_html(progress, False, False)
        hint_info_html = hint_to_html(messages, scenario, username, hint_model, hint_temperature)
        
        return (
            chatbot, 
            messages, 
            scenario, 
            progress_info_html,
            states_info_html, 
            mermaid_diagram,
            gr.update(interactive=True),
            hint_info_html,
            transition_info_html,
        )


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
        inputs=[skill_dropdown, level_dropdown, username],
        outputs=[chatbot, raw_messages, chosen_scenario, progress_info_html, state_info_html, msg, hint_info_html, transition_info_html, mermaid_diagram],
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
            state_info_html, mermaid_diagram, msg, hint_info_html,
            transition_info_html
        ],
    ).then(
        fn=lambda: "",
        inputs=None,
        outputs=msg,
    )

if __name__ == "__main__":
    demo.launch()
