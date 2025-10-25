import random
import openrouterapi
import json

HINT_PROMPT = """
# Your Role

You act as a people skills advisor and professional psychologist where two people are talking to each other, and one of them ({username}) needs guidance.
Your job is to provide the most specific, contextual hint based on the current conversation.

# Conversation

You will be given a piece of dialogue between {username} and {botname}:
{chat_context}

# Goal for {username} and target skill to improve

{username} have the following ultimate goal in this conversation:
{goal}

The ultimate purpose of these hints is to teach {username} how to improve the skill of {skill}, though it's not necessary to do this explicitly.

# Additional information about {botname}

* ⚠️ WARNING! You can't directly reference to this information in your hints - it will be considered as leakage and failure.
* You can use it to drop a subtle indirect hint, but not to directly name it or use it in any other way.
* {botname}'s personality:
{character_points}
* How {botname} should resist the goal and react to the user's responses:
{negprompt_points}
* Once again check your hints for leakage and failure.

# Your Task

Your task is to provide a short, actionable hint to {username} that will help them achieve their goal.

The hint should be:
- Very specific to the current conversation context
- Based on extremely precise formulations about specific things {username} said or did
- Focused on what {username} should do next
- No more than 1 short sentence (max 10 words)
- Directly address {username} without using their name
- Avoid general advice or abstractions
- Use {botname}'s personality and how they resist/react only to understand context, not to directly reference it

# Text Stylistic and Hint Delivery

- Use active, compelling language that drives toward action
- Create tension and forward momentum in your phrasing
- Balance directness with subtle psychological insight
- Use linguistic patterns that provoke immediate response
- Write hints that feel like a challenge or opportunity
- Aim for language that creates a "now or never" sense of urgency

{previous_hints}

{json_addition}
"""


JSON_ADDITION = """
# Output format

Respond in JSON format as {{
    'hintWhatToDo': (str, hint for {username} to do next in direct reference, <= 15 words),
    'wrongActions': (str, what {username} is doing wrong in direct reference, <= 15 words),
    'hintWhatToAvoid': (str, what {username} should avoid doing, <= 15 words),
    'decideBestHintCategory': (str, one from ['hintWhatToDo', 'wrongActions', 'hintWhatToAvoid'], select the most contextually and criteria-wise appropriate hint that differs from previous ones, both in content and in category),
}}
"""


QUOTATION_BRACKET = "\"\"\""
BACKTICK_BRACKET = "```"


PREVIOUS_HINTS_TEMPLATE = """
# Previous Hints to avoid

STRICTLY AVOID HINTS LIKE THESE:
{formatted_hints}

Do not generate hints similar to these as the user has already seen them. Create something distinctly different.
"""


def build_task(
    chat_context,
    username,
    botname,
    goal,
    skill,
    character,
    negprompt,
    bracket='quotation',
    context_window_size=20,
    previous_hints=[],
):
    assert bracket in ['quotation', 'backtick']
    bracket_str = QUOTATION_BRACKET if bracket == 'quotation' else BACKTICK_BRACKET
    userbot_messages = []

    for msg in chat_context:
        if msg.type != 'message':
            continue
        msg = dict(msg)
        if msg['role'] == 'user':
            userbot_messages.append(f"{username}: {msg['content']}")
        elif msg['role'] == 'assistant':
            userbot_messages.append(f"{botname}: {msg['content']}")
        else:
            raise ValueError(f"Unknown message role: {msg['role']}")
    userbot_messages = userbot_messages[-context_window_size:] if context_window_size > 0 else userbot_messages

    chat_context = "\n".join([bracket_str] + userbot_messages + [bracket_str]).strip()
    goal = "\n".join([bracket_str] + [goal] + [bracket_str]).strip()
    character_points = "\n".join([f"- {item}" for item in character])
    negprompt_points = "\n".join([f"- {item}" for item in negprompt])
    json_addition = JSON_ADDITION.format(username=username, botname=botname, skill=skill).strip()
    previous_hints = PREVIOUS_HINTS_TEMPLATE.format(
        username=username,
        formatted_hints="\n".join([f"🚫 {hint['category']}: {hint['hint']}" for hint in previous_hints[-5:]])
    ).strip() if previous_hints else ""

    return HINT_PROMPT.format(
        chat_context=chat_context,
        username=username,
        botname=botname,
        goal=goal,
        skill=skill,
        character_points=character_points,
        negprompt_points=negprompt_points,
        json_addition=json_addition,
        previous_hints=previous_hints,
    ).strip()


def hint(
    api_key,
    chat_context,
    botname,
    goal,
    skill,
    character,
    negprompt,
    username='user',
    model="openai/gpt-4.1",
    bracket='quotation',
    temperature=0.5,
    context_window_size=20,
    previous_hints=[]
):
    task = build_task(
        chat_context=chat_context,
        username=username,
        botname=botname,
        goal=goal,
        skill=skill,
        character=character,
        negprompt=negprompt,
        bracket=bracket,
        context_window_size=context_window_size,
        previous_hints=previous_hints
    )
    
    output = openrouterapi.call(
        api_key=api_key,
        messages=[{"role": "system", "content": task}],
        model=model,
        temperature=temperature,
        json_mode=True,
    )
    output = output['content']
    best_hint_category = output['decideBestHintCategory']
    if best_hint_category in output:
        output['category'] = best_hint_category
        output['hint'] = output[best_hint_category]
    else:
        output['category'] = random.choice(['hintWhatToDo','wrongActions','hintWhatToAvoid'])
        output['hint'] = output[output['category']]
    return output


async def ahint(
    api_key,
    chat_context,
    botname,
    goal,
    skill,
    character,
    negprompt,
    username='user',
    model="openai/gpt-4.1",
    bracket='quotation',
    temperature=1.0,
    context_window_size=20,
    previous_hints=[]
):
    task = build_task(
        chat_context=chat_context,
        username=username,
        botname=botname,
        goal=goal,
        skill=skill,
        character=character,
        negprompt=negprompt,
        bracket=bracket,
        context_window_size=context_window_size,
        previous_hints=previous_hints
    )
    
    output = await openrouterapi.acall(
        api_key=api_key,
        messages=[{"role": "system", "content": task}],
        model=model,
        temperature=temperature,
        json_mode=True,
    )
    output = output['content']
    best_hint_category = output['decideBestHintCategory']
    if best_hint_category in output:
        output['category'] = best_hint_category
        output['hint'] = output[best_hint_category]
    else:
        output['category'] = random.choice(['hintWhatToDo','wrongActions','hintWhatToAvoid'])
        output['hint'] = output[output['category']]
    return output


if __name__ == "__main__":
    import os

    def single_test_case():
        chat_context = [
            {"role": "assistant", "content": "The new project deadline is quite tight, isn't it?"},
            {"role": "user", "content": "Yes, it is. I'm a bit worried we might not make it."},
            {"role": "assistant", "content": "Well, I've had to pull all-nighters before to meet goals."},
            {"role": "user", "content": "I appreciate the dedication, but I hope it doesn't come to that for everyone."}
        ]
        
        username = 'Manager'
        botname = 'Alex'
        goal = "Understand Alex's capacity and concerns about the project deadline without causing stress."
        skill = "smalltalk"
        
        character = [
            "Dedicated and hardworking.",
            "Tends to overcommit and hide stress.",
            "Values directness but appreciates empathy."
        ]
        negprompt = [
            "Becomes withdrawn if feels pressured.",
            "Might agree to unrealistic demands to avoid conflict.",
            "Resists vague reassurances, prefers concrete solutions."
        ]
        previous_hints = [
            {
                'category': 'hintWhatToDo',
                'hint': "Ask Alex how they feel about the deadline pressure."
            }
        ]
        
        print(f"--- Running single test case for {botname} ---")
        
        task_prompt = build_task(
            chat_context=chat_context,
            username=username,
            botname=botname,
            goal=goal,
            skill=skill,
            character=character,
            negprompt=negprompt,
            bracket='backtick',
            context_window_size=10,
            previous_hints=previous_hints
        )
        print("=== GENERATED PROMPT (from build_task) ===")
        print(task_prompt)
        print("=== END PROMPT ===\n")
        
        result = hint(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            chat_context=chat_context,
            botname=botname,
            goal=goal,
            skill=skill,
            character=character,
            negprompt=negprompt,
            username=username,
            model="openai/gpt-4o-mini",
            bracket='backtick',
            temperature=0.7,
            context_window_size=10
        )
        
        print("\nRESULT (from hint function):")
        if isinstance(result, dict):
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result)

    single_test_case()
