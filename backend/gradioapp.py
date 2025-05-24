import os
import sys
import re
import gradio as gr
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import litellmapi
import utils as futils
import hint as fhint
import checker as fchecker

AVAILABLE_MODELS = [
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "gemini/gemini-2.0-flash",
    "deepseek/deepseek-chat",
    "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
]
ALL_SCENARIOS = futils.load_scenarios(futils.SKILLS)

SCENARIO_INFO_FORMAT = """
## 👤 Bot Character Name
{botname} ({botgender})

## 📝 Scenario Description for User
{description}

## 🎯 Your Goal in this Dialogue
{goal}

## 💬 Bot's Opening Line
{opening}

## 🤖 Bot Personality You Will Talk With
{character_points}

## ⚠️ Bot's Negative Reactions / Resistance (Hint for You)
{negprompt_points}
"""

def get_scenario_names(skill):
    if skill in ALL_SCENARIOS:
        return sorted(list(ALL_SCENARIOS[skill].keys()))
    return []

def format_hint_html(hint_data):
    items = [f"<li><b>{key.replace('_', ' ').title()}:</b> {value}</li>" for key, value in hint_data.items() if value]
    return "<h3>💡 Hint</h3><ul>" + "".join(items) + "</ul>"

def format_checker_html(checker_data):
    is_complete = checker_data['is_goal_complete']
    explanation = checker_data['explain_your_decision']
    progress = checker_data['progress_towards_goal']
    status = "✅ COMPLETED" if is_complete else "❌ NOT COMPLETED"
    progress_percent = int(progress) * 10
    html_parts = [
        f"<h3>🎯 Goal Status: {status}</h3>",
        f"<p><b>Explanation:</b> {explanation}</p>",
        "<div style='background-color:#e9ecef; border-radius:5px; padding:2px; margin-top:5px;'>",
        f"<div style='width:{progress_percent}%; background-color:#007bff; height:20px; border-radius:4px; text-align:center; color:white; line-height:20px;'>{progress}/10</div>",
        "</div>"
    ]
    return "".join(html_parts)

def get_scenario_info(skill, scenario_name):
    scenario_data = ALL_SCENARIOS[skill][scenario_name]
    character_pts = "\n".join([f"- {item}" for item in scenario_data['character']])
    negprompt_pts = "\n".join([f"- {item}" for item in scenario_data['negprompt']])
    return SCENARIO_INFO_FORMAT.format(
        botname=scenario_data['botname'],
        botgender=scenario_data['botgender'],
        description=scenario_data['description'],
        goal=scenario_data['goal'],
        character_points=character_pts,
        opening=scenario_data['opening'],
        negprompt_points=negprompt_pts,
    ).strip()

def split_roleplay_message(message):
    message_parts = []
    pattern = r'(\*[^*]+\*)'
    parts = re.split(pattern, message)
    for part in parts:
        if part.strip():
            if part.startswith('*') and part.endswith('*'):
                message_parts.append({"type": "roleplay", "content": part.strip()})
            else:
                message_parts.append({"type": "speech", "content": part.strip()})
    return message_parts

def bot_response(
    user_message, raw_messages, scenario_data, 
    response_model, response_temperature, 
    checker_model, checker_temperature
):
    # prompt and user message
    prompt = futils.assemble_prompt(
        scenario=scenario_data,
        username=scenario_data['username'],
        usergender=scenario_data['usergender']
    )
    raw_messages = raw_messages + [{"role": "user", "content": user_message}]
    messages_for_llm = [{"role": "system", "content": prompt}] + raw_messages
    
    # bot response
    bot_reply = litellmapi.run(
        model=response_model,
        messages=messages_for_llm,
        temperature=response_temperature
    )['content']
    raw_messages = raw_messages + [{"role": "assistant", "content": bot_reply}]
    
    # checker
    checker_result = fchecker.checker(
        chat_context=raw_messages,
        goal=scenario_data['goal'],
        botname=scenario_data['botname'],
        username=scenario_data['username'],
        model=checker_model,
        temperature=checker_temperature
    )
    checker_html_out = format_checker_html(checker_result)
    
    return raw_messages, gr.update(value=raw_messages), checker_html_out, ""

def get_hint(
    raw_messages, scenario_data, 
    hint_model, hint_temperature
):
    hint_result = fhint.hint(
        chat_context=raw_messages,
        botname=scenario_data['botname'],
        goal=scenario_data['goal'],
        character=scenario_data['character'],
        negprompt=scenario_data['negprompt'],
        username=scenario_data['username'],
        model=hint_model,
        temperature=hint_temperature
    )
    hint_html_out = format_hint_html(hint_result)
    return hint_html_out

with gr.Blocks(title="Chatbot Scenario Trainer") as demo:
    raw_messages_state = gr.State([])
    scenario_data_state = gr.State({})
    
    with gr.Row():
        with gr.Column(scale=1):
            skill_dropdown = gr.Dropdown(label="Skill", choices=futils.SKILLS, value=None)
            scenario_name_dropdown = gr.Dropdown(label="Scenario", choices=[], value=None)
            start_button = gr.Button("Start Scenario")
            scenario_info_display = gr.Markdown("Select a skill and scenario to see details.")

        with gr.Column(scale=2):
            chatbot_component = gr.Chatbot(label="Chat", height=500, type="messages")
            with gr.Row():
                msg_input = gr.Textbox(label="Your Message", placeholder="Type here...", show_label=False, scale=4)
                submit_button = gr.Button("Send", scale=1)

            with gr.Row():
                hint_button = gr.Button("Get Hint")
                hint_html_display = gr.HTML()
            goalchecker_html_display = gr.HTML()
    
    clear_button = gr.Button("Clear All")
    
    with gr.Accordion("User Settings & Advanced Options", open=False):
        with gr.Row():
            with gr.Column(scale=1):
                username_input = gr.Textbox(label="Your Name", value="Vlad")
                user_gender_input = gr.Radio(label="Your Gender", choices=["male", "female", "other"], value="male")
            
            with gr.Column(scale=1):
                response_model_dropdown = gr.Dropdown(label="Response Model", choices=AVAILABLE_MODELS, value=AVAILABLE_MODELS[0])
                response_temp_slider = gr.Slider(label="Response Temperature", minimum=0.0, maximum=1.0, step=0.1, value=0.7)
                
            with gr.Column(scale=1):
                hint_model_dropdown = gr.Dropdown(label="Hint Model", choices=AVAILABLE_MODELS, value=AVAILABLE_MODELS[0])
                hint_temp_slider = gr.Slider(label="Hint Temperature", minimum=0.0, maximum=1.0, step=0.1, value=0.5)
                
            with gr.Column(scale=1):
                checker_model_dropdown = gr.Dropdown(label="Checker Model", choices=AVAILABLE_MODELS, value=AVAILABLE_MODELS[0])
                checker_temp_slider = gr.Slider(label="Checker Temperature", minimum=0.0, maximum=1.0, step=0.1, value=0.1)

    def handle_skill_change(skill_value):
        names = get_scenario_names(skill_value)
        selected_scenario_name = names[0] if names else None
        scenario_info_md = get_scenario_info(skill_value, selected_scenario_name)
        return gr.Dropdown(choices=names, value=selected_scenario_name), scenario_info_md

    skill_dropdown.change(fn=handle_skill_change, inputs=[skill_dropdown], outputs=[scenario_name_dropdown, scenario_info_display])
    scenario_name_dropdown.change(fn=get_scenario_info, inputs=[skill_dropdown, scenario_name_dropdown], outputs=[scenario_info_display])

    def initialize_chat_session(username, usergender, skill, scenario_name):
        scenario_data = ALL_SCENARIOS[skill][scenario_name]
        details_for_state = {**scenario_data, 'username': username, 'usergender': usergender}

        opening_message = scenario_data['opening']
        message_parts = split_roleplay_message(opening_message)
        raw_messages = []
        for msg in message_parts:
            if msg["type"] == "roleplay":
                raw_messages.append({
                    "role": "user",
                    "content": msg["content"],
                })
            else:
                raw_messages.append({
                    "role": "assistant",
                    "content": msg["content"],
                })
        
        return raw_messages, details_for_state, gr.update(value=raw_messages), "", ""

    start_button.click(
        fn=initialize_chat_session,
        inputs=[username_input, user_gender_input, skill_dropdown, scenario_name_dropdown],
        outputs=[
            raw_messages_state, scenario_data_state, 
            chatbot_component, hint_html_display, goalchecker_html_display
        ]
    )

    message_submission_inputs = [
        msg_input, raw_messages_state, scenario_data_state, 
        response_model_dropdown, response_temp_slider, 
        checker_model_dropdown, checker_temp_slider
    ]
    message_submission_outputs = [
        raw_messages_state, chatbot_component, goalchecker_html_display, msg_input
    ]

    msg_input.submit(fn=bot_response, inputs=message_submission_inputs, outputs=message_submission_outputs)
    submit_button.click(fn=bot_response, inputs=message_submission_inputs, outputs=message_submission_outputs)

    hint_button.click(
        fn=get_hint,
        inputs=[
            raw_messages_state, scenario_data_state,
            hint_model_dropdown, hint_temp_slider
        ],
        outputs=[hint_html_display]
    )

    def clear_all_outputs():
        initial_md = "Select a skill and scenario to see details."
        return [], {}, gr.update(value=[]), "", "", initial_md, "Vlad", "male", None, [], ""
    
    clear_button.click(
        fn=clear_all_outputs,
        inputs=[],
        outputs=[
            raw_messages_state, scenario_data_state, 
            chatbot_component, hint_html_display, goalchecker_html_display, scenario_info_display,
            username_input, user_gender_input, skill_dropdown, scenario_name_dropdown, msg_input
        ]
    )

if __name__ == "__main__":
    demo.launch()
