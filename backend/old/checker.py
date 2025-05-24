import litellmapi


GOAL_CHECKER_PROMPT = """
You act as chat context assessor where two people are talking to each other, and one of them has a goal to achieve.
Your job is to assess whether the goal has been achieved in the dialogue and provide information about this assessment.

You will be given a piece of dialogue between {username} and {botname}:
{chat_context}

{username} has the following goal in the dialogue:
{goal}

{botname} may resist and refuse to fulfill the {username}'s goal, but may also agree. 
Your task is to check whether {username}'s goal has already been achieved in the dialogue or not. 
Make your decision based solely on {botname}'s responses and {username}'s goal statement, and be flexible with wording of goal statement. 
Additionally, consider the following:
- If {botname} want to fullfil {username}'s goal, but minor circumstances interfere, then respond with True.
- If {botname} want to fullfil {username}'s goal, but {botname} hesitates only becaues {botname} is shy, then respond True.
- If the dialogue is not related to {username}'s goal at all, then respond with False. 

{hint_addition}

{goal_progress_addition}

{json_addition}
"""


HINT_ADDITION = """
Additionally, provide a hint for {username} on how to complete the goal or what they are doing wrong, based on the context. Also, consider the following:
- This hint should be short (1 sentence) and informative, highly dependent on the context of the conversation, especially the latest phrases.
- The hint should be directed at {username}.
- Be highly specific and precise in your advice. If appropriate - point out to {username} what they are doing wrong, instead of just telling them what needs to be done.
- Avoid abstractions, avoid general words, avoid vague formulations, and avoid wordiness.
- Don't start a sentence by calling {username} by name.
"""

GOAL_PROGRESS_ADDITION = """
Additionally, return the goal progress as a number between 0 (indicating that {username} hasn't started working toward the goal) and 10 (indicating that {username} has fully achieved the goal), which reflects how close {username} is to completing the goal. Also, consider the following:
- The progress should be calculated based on the context of the conversation, especially the latest phrases.
- Be conservative in your assessment of the progress.
"""


# JSON_ADDITION = "Respond in JSON format as {'did_A_achieve_goal': (bool), 'progress': (int), 'hint_for_A': (str), 'explain_your_decision': (str)}"
JSON_ADDITION = """
Respond in JSON format as {{
    'is_goal_complete': (bool),
    'explain_your_decision': (str),
    'progress_towards_goal': (int),
    'hint_how_to_achieve_goal': (str),
}}
"""


QUOTATION_BRACKET = "\"\"\""
BACKTICK_BRACKET = "```"


def build_prompt(chat_context, goal, username, botname, bracket='quotation'):
    assert bracket in ['quotation', 'backtick'] 
    bracket = QUOTATION_BRACKET if bracket == 'quotation' else BACKTICK_BRACKET
    userbot_messages = []

    for msg in chat_context:
        if msg['role'] == 'user':
            userbot_messages.append(f"{username}: {msg['content']}")
        elif msg['role'] == 'assistant':
            userbot_messages.append(f"{botname}: {msg['content']}")
        else:
            # IMPORTANT we skip system messages here
            pass

    chat_context = "\n".join([bracket] + userbot_messages + [bracket]).strip()
    goal = "\n".join([bracket] + [goal.format(username=username, botname=botname).strip()] + [bracket]).strip()
    hint_addition = HINT_ADDITION.format(username=username, botname=botname).strip()
    goal_progress_addition = GOAL_PROGRESS_ADDITION.format(username=username, botname=botname).strip()
    json_addition = JSON_ADDITION.format(username=username, botname=botname).strip()

    return GOAL_CHECKER_PROMPT.format(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        hint_addition=hint_addition,
        goal_progress_addition=goal_progress_addition,
        json_addition=json_addition,
    ).strip()


# checker(chat_context, goal) → IsGoalComplete: bool | goalProgress: int (1 to 10) | hintHowToAchieveGoal: str
def checker(
    chat_context,
    goal,
    username,
    botname,
    model="openai/gpt-4o-mini",
    bracket='quotation',
    temperature=0.5,
):
    goal_prompt = build_prompt(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        bracket=bracket,
    )
    result = litellmapi.run(
        model=model,
        messages=[{"role": "system", "content": goal_prompt}],
        json_mode=True,
        temperature=temperature,
    )['json']
    output = {
        'isGoalComplete': result['is_goal_complete'],
        'goalProgress': result['progress_towards_goal'],
        'hintHowToAchieveGoal': result['hint_how_to_achieve_goal'],
        'LLMexplainDecision': result['explain_your_decision'],
    }
    return output


if __name__ == "__main__":
    chat_context = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm good, thank you!"},
        {"role": "user", "content": "What's your name?"},
        {"role": "assistant", "content": "My name is John Doe."},
    ]
    goal = "Setup a date with {botname} and receive Yes"

    goal_prompt = build_prompt(
        chat_context=chat_context,
        goal=goal,
        username='Vlad',
        botname='Hope',
        bracket='backtick',
    )
    print(f"---\n{goal_prompt}\n---")

    model = "openai/gpt-4o-mini"  # works
    # model = "together_ai/Qwen/Qwen2.5-7B-Instruct-Turbo"  # error since it doesn't support json_mode
    # model = "deepseek/deepseek-chat"  # works
    result = checker(
        chat_context=chat_context,
        goal=goal,
        username='Vlad',
        botname='Hope',
        model=model,
        bracket='backtick',
    )
    print(result)
