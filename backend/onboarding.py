import chainlit as cl
import json
import os
from dotenv import load_dotenv
from openrouterapi import acall

load_dotenv(override=True)

# Load all scenarios
def load_scenarios():
    scenarios = {}
    scenario_files = [
        'smalltalk.json',
        'attraction.json', 
        'conflictresolution.json',
        'decodingemotions.json',
        'manipulationdefense.json',
        'negotiation.json',
        'artofpersuasion.json'
    ]
    
    for filename in scenario_files:
        filepath = os.path.join('../scenarios', filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                skill_name = filename.replace('.json', '')
                scenarios[skill_name] = json.load(f)
    
    return scenarios

SCENARIOS = load_scenarios()

SYSTEM_PROMPT = """You are an expert communication coach specializing in personalized learning paths. Your role is to understand the user's communication goals and challenges, then recommend the perfect practice scenarios.

Available skills and scenarios:
{scenarios_info}

Your conversation flow:
1. Welcome warmly, ask about their communication goals
2. Dig deeper: what specific situations they struggle with
3. Ask about their experience level
4. Based on their needs, recommend 2-3 specific scenarios
5. Explain why each scenario fits their goals

Be conversational, empathetic, and insightful. Keep responses concise (2-3 sentences max per response).
"""

def format_scenarios_info():
    info = []
    for skill, scenarios in SCENARIOS.items():
        info.append(f"\n{skill.upper()}:")
        for scenario_id, scenario_data in scenarios.items():
            desc = scenario_data.get('description', '')
            info.append(f"  - {scenario_id}: {desc}")
    return '\n'.join(info)


@cl.on_chat_start
async def start():
    cl.user_session.set("messages", [])
    
    await cl.Message(
        content="Hey! I'm here to help you level up your communication skills. What brings you here today? Any specific situations you want to handle better?"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    messages = cl.user_session.get("messages")
    
    # Add user message
    messages.append({
        "role": "user",
        "content": message.content
    })
    
    # Prepare context
    system_message = {
        "role": "system",
        "content": SYSTEM_PROMPT.format(scenarios_info=format_scenarios_info())
    }
    
    full_messages = [system_message] + messages
    
    # Get response from LLM
    msg = cl.Message(content="")
    await msg.send()
    
    try:
        response = await acall(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            messages=full_messages,
            model="anthropic/claude-sonnet-4.5",
            temperature=0.7,
            max_tokens=300,
        )
        
        content = response["content"]
        
        # Add assistant message
        messages.append({
            "role": "assistant", 
            "content": content
        })
        
        msg.content = content
        await msg.update()
        
        # Check if we should show scenario recommendations
        if any(word in message.content.lower() for word in ['ready', 'start', 'yes', 'practice', 'go']):
            actions = [
                cl.Action(
                    name="start_voice",
                    value="start",
                    label="🎙️ Start Voice Practice",
                    description="Go to voice practice with recommended scenario"
                )
            ]
            await cl.Message(
                content="When you're ready, click below to start your voice practice session!",
                actions=actions
            ).send()
        
    except Exception as e:
        msg.content = f"Sorry, encountered an error: {str(e)}"
        await msg.update()


@cl.action_callback("start_voice")
async def on_action(action: cl.Action):
    await cl.Message(content="Redirecting to voice practice... (integration with main app pending)").send()

