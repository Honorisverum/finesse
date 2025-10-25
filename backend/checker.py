import openrouterapi


GOAL_CHECKER_PROMPT = """
# Your Role

You act as chat context assessor where two people are talking to each other, and one of them has a goal to achieve.
Your job is to assess whether the goal has been achieved in the dialogue and provide information about this assessment.

# Conversation

You will be given a piece of dialogue between {username} and {botname}:
{chat_context}

# Goal Assessment Task

{username} has the following goal in the dialogue:
{goal}

{botname} may resist and refuse to fulfill the {username}'s goal, but may also agree. 
Your task is to check whether {username}'s goal has already been achieved in the dialogue or not. 
Make your decision based solely on {botname}'s responses and {username}'s goal statement, and be flexible with wording of goal statement. 

# Assessment Guidelines

Consider the following:
- If {botname} want to fullfil {username}'s goal, but minor circumstances interfere, then respond with True.
- If {botname} want to fullfil {username}'s goal, but {botname} hesitates only becaues {botname} is shy, then respond True.
- If the dialogue is not related to {username}'s goal at all, then respond with False. 

{goal_progress_addition}

{bad_ending_addition}

{cta_motivational_addition}

{json_addition}
"""


GOAL_PROGRESS_ADDITION = """
Additionally, return the goal progress as a number between 0 (indicating that {username} hasn't started working toward the goal) and 10 (indicating that {username} has fully achieved the goal), which reflects how close {username} is to completing the goal. Consider the following:
- 0: No discussion related to the goal has occurred.
- 1-3: Initial steps taken, {username} has broached the subject or made a very indirect attempt.
- 4-6: {username} is actively working towards the goal, some obstacles may have been overcome, but {botname} is still resistant or non-committal.
- 7-9: {username} is very close. {botname} shows clear signs of agreeing or fulfilling the goal, minor details might be pending.
- 10: The goal is explicitly and clearly achieved based on {botname}'s response.
- The progress should be calculated based on the context of the conversation, especially the latest phrases from both {username} and {botname}.
- Be conservative in your assessment of the progress. If in doubt between two scores, pick the lower one.
- Base the score on {botname}'s willingness and actions towards fulfilling the goal, not just {username}'s efforts.
"""


BAD_ENDING_ADDITION = """
Also, determine if a "bad ending" has been triggered where further progress toward the goal is now impossible. Mark is_bad_ending_triggered as True if any of these situations apply:
- The moment or opportunity has been missed and cannot be recovered
- Connection between {username} and {botname} has been lost (e.g., extreme hostility, complete breakdown in communication)
- {username} is behaving inappropriately, offensive, or in a way that has permanently alienated {botname}
- {botname} has firmly and absolutely rejected the goal with no chance of reversal
- The conversation has derailed completely away from the goal with no path to return
- {botname} has explicitly ended the conversation or indicated they will not continue engaging
Be conservative when determining a bad ending - only mark True when it's clear that the goal has become truly impossible to achieve through continued conversation.
"""


CTA_MOTIVATIONAL_ADDITION = """
You should generate a motivational message (CTA) when there has been a significant change in progress compared to the previous progress value of {previous_progress}.

When generating the CTA message, follow these guidelines:
- If current progress is better than previous progress {previous_progress}, provide a brief, encouraging message celebrating the improvement
- If current progress is worse than previous progress {previous_progress}, express that it was a bad move - be honest but non-banal and dynamic
- Do not give hints or suggestions, just motivate or vividly report failures
- CTA message must be extremely concise (2-4 words maximum) and end with exclamation or question mark
- Address {username} directly without using their name
- Messages should be contextual to the specific conversation and progress situation
"""


JSON_ADDITION = """
Respond in JSON format as {{
    'is_goal_complete': (bool),
    'progress_towards_goal': (int),
    'is_bad_ending_triggered': (bool),
    {cta_motivational_addition}
}}
"""


QUOTATION_BRACKET = "\"\"\""
BACKTICK_BRACKET = "```"


def build_task(chat_context, goal, username, botname, bracket='quotation', context_window_size=20, previous_progress=None):
    assert bracket in ['quotation', 'backtick'] 
    bracket = QUOTATION_BRACKET if bracket == 'quotation' else BACKTICK_BRACKET
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

    chat_context = "\n".join([bracket] + userbot_messages + [bracket]).strip()
    goal = "\n".join([bracket] + [goal.format(username=username, botname=botname).strip()] + [bracket]).strip()
    goal_progress_addition = GOAL_PROGRESS_ADDITION.format(username=username, botname=botname).strip()
    bad_ending_addition = BAD_ENDING_ADDITION.format(username=username, botname=botname).strip()
    cta_motivational_addition = CTA_MOTIVATIONAL_ADDITION.format(
        previous_progress=previous_progress,
        username=username,
        botname=botname,
    ).strip() if previous_progress is not None else ""
    json_addition = JSON_ADDITION.format(
        username=username,
        botname=botname,
        cta_motivational_addition="'CTA': (str, <= 4 words)," if previous_progress is not None else "",
    ).strip()

    return GOAL_CHECKER_PROMPT.format(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        goal_progress_addition=goal_progress_addition,
        bad_ending_addition=bad_ending_addition,
        cta_motivational_addition=cta_motivational_addition,
        json_addition=json_addition,
    ).strip()


def checker(
    api_key,
    chat_context,
    goal,
    botname,
    username="user",
    model="openai/gpt-4.1",
    bracket='quotation',
    temperature=0.5,
    context_window_size=20,
    previous_progress=None,
):
    task = build_task(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        bracket=bracket,
        context_window_size=context_window_size,
        previous_progress=previous_progress,
    )
    result = openrouterapi.call(
        api_key=api_key,
        messages=[{"role": "system", "content": task}],
        model=model,
        temperature=temperature,
        json_mode=True,
    )
    result = result['content']
    result['previous_progress_towards_goal'] = previous_progress
    if ('CTA' not in result) or (result['CTA'] is None) or (result['CTA'].strip() == "") or (result['CTA'].lower().strip() in ["none", "null"]):
        result['CTA'] = None
    return result


async def achecker(
    api_key,
    chat_context,
    goal,
    botname,
    username="user",
    model="openai/gpt-4.1",
    bracket='quotation',
    temperature=0.5,
    context_window_size=20,
    previous_progress=None,
):
    task = build_task(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        bracket=bracket,
        context_window_size=context_window_size,
        previous_progress=previous_progress,
    )
    result = await openrouterapi.acall(
        api_key=api_key,
        messages=[{"role": "system", "content": task}],
        model=model,
        temperature=temperature,
        json_mode=True,
    )
    result = result['content']
    result['previous_progress_towards_goal'] = previous_progress
    if ('CTA' not in result) or (result['CTA'] is None) or (result['CTA'].strip() == "") or (result['CTA'].lower().strip() in ["none", "null"]):
        result['CTA'] = None
    return result


if __name__ == "__main__":
    import os

    chat_context = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm good, thank you!"},
        {"role": "user", "content": "What's your name?"},
        {"role": "assistant", "content": "My name is John Doe."},
        # {"role": "assistant", "content": "omg i want to date you"},
    ]
    goal = "Setup a date with {botname} and receive Yes"

    task = build_task(
        chat_context=chat_context,
        goal=goal,
        username='Vlad',
        botname='Hope',
        bracket='backtick',
        previous_progress=6,
    )
    print(f"---\n{task}\n---")

    result = checker(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        chat_context=chat_context,
        goal=goal,
        botname='Hope',
        username='Vlad',
        model="openai/gpt-4.1",
        bracket='backtick',
    )
    print(result)

    # Example with previous progress
    print("\n--- With previous progress ---")
    result_with_progress = checker(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        chat_context=chat_context,
        goal=goal,
        botname='Hope',
        username='Vlad',
        model="openai/gpt-4.1",
        bracket='backtick',
        previous_progress_towards_goal=6,
    )
    print(result_with_progress)
