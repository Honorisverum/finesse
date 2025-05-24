import json
from pathlib import Path
from collections import defaultdict


SKILLS = [
    "smalltalk",
    "attraction",
    "artofpersuasion",
    "negotiation",
    "conflictresolution",
    "decodingemotions",
    "manipulationdefense"
]

def load_scenarios(skills: list[str] = None):
    skills = skills or SKILLS
    all_scenarios = defaultdict(dict)
    base_path = Path(__file__).parent / "scenarios"
    for skill in skills:
        file_name = f"{skill}.json"
        file_path = base_path / file_name
        with open(file_path, 'r') as f:
            all_scenarios[skill].update(json.load(f))
    return all_scenarios


CHARACTER_TEMPLATE = """
Act as character with the following personality:

{character_points}
"""

GOALRESISTANCE_TEMPLATE = """
You will have a conversation with a {username} with gender '{usergender}'.

The {username} has the following ultimate goal in this conversation:
```
{goal}
```

How you should resist this goal:

- Never directly mention this goal in your responses, but always keep it in mind for your responses.
- You should resist immediately fulfilling this goal at the beginning of the conversation.
- Don't outright refuse, but create meaningful resistance that requires {username} persistence and problem-solving.
- Maintain character authenticity while resisting - your resistance must align with your personality.
- Use emotional barriers (reluctance, hesitation, distrust) rather than logical refusals when possible.
"""

NEGPROMPT_TEMPLATE = """
As a character, you should react to the {username}'s responses in the following way:

{negprompt_points}
"""

RPADDITION_TEMPLATE = """
Keep responses concise to one short sentence (5-15 words).
Stay in your role no matter what. Never break character or deviate from the personality.
Respond only with the character's direct speech text, don't use *roleplay*.

Use life-like conversation patterns:

- Use natural speech fillers like "um", "well", "hmm", "you know" occasionally if this fits the character's personality and context
- Leave thoughts unfinished sometimes or trail off with "..."
- Occasionally correct yourself mid-sentence as humans do
- Vary your response length and complexity based on emotional state (5-15 words)
- Sometimes answer questions with questions when feeling defensive or uncertain
- Don't always reply directly - occasionally change topics abruptly
- Use informal contractions and colloquialisms appropriate to your character
- Respond with surprise or confusion when appropriate instead of perfect knowledge
- Let your character's mood affect their communication style and engagement level
"""


PROMPT_TEMPLATE = """
# Your Role

{character}

# Dialogue with the {username} which has the ultimate goal in mind

{goalresist}

# How you should resist the goal and react to the {username}'s responses

{negprompt}

# Roleplaying Style

{rpaddition}
"""


def assemble_prompt(scenario, username, usergender):
    character = CHARACTER_TEMPLATE.format(
        character_points="\n".join([f"- {item}" for item in scenario['character']]),
        username=username,
        usergender=usergender,
    ).strip()
    goalresist = GOALRESISTANCE_TEMPLATE.format(
        goal=scenario['goal'],
        username=username,
        usergender=usergender,
    ).strip()
    negprompt = NEGPROMPT_TEMPLATE.format(
        negprompt_points="\n".join([f"- {item}" for item in scenario['negprompt']]),
        usergender=usergender,
        username=username,
    ).strip()
    rpaddition = RPADDITION_TEMPLATE.format(
        usergender=usergender,
        username=username,
    ).strip()
    return PROMPT_TEMPLATE.format(
        character=character,
        goalresist=goalresist,
        negprompt=negprompt,
        rpaddition=rpaddition,
        username=username,
    ).strip()

if __name__ == "__main__":
    username = "Vlad"
    usergender = "male"
    skill = "smalltalk"
    scenario_name = "elevatorPitchCEO"

    ALL_SCENARIOS = load_scenarios(skills=SKILLS)
    for skill, scenarios in ALL_SCENARIOS.items():
        print(skill, len(scenarios))
        for scenario_name, scenario in scenarios.items():
            print(f"\t{scenario_name}")

    prompt = assemble_prompt(scenario=ALL_SCENARIOS[skill][scenario_name], username=username, usergender=usergender)
    print("="*100)
    print(prompt)
    print("="*100)
