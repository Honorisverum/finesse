import litellmapi


DPE_PROMPT = """\
You are a Dynamic Plot Engine for an immersive chat game that helps users develop social skills.

You will be given a conversation between {username} and {botname}:
{chat_context}

The user has the following goal in this conversation:
{goal}

Your task is to create an exciting plot twist that will add tension, drama, or an unexpected turn to the conversation. This plot twist should be related to the user's goal and make the interaction more engaging and challenging.

The plot twist should:
1. Be sudden and dramatic
2. Be contextually appropriate based on the conversation so far
3. Create a situation that forces the user to respond quickly
4. Be narrated in second person (addressing the user directly)
5. Be concise and impactful (<= 15 WORDS)

Also create two possible actions the user could take in response to this plot twist:
1. Action 1: A bold, assertive, or risky response (<= 4 WORDS ONLY, third-person perspective, active verb)
2. Action 2: A cautious, diplomatic, or safe response (<= 4 WORDS ONLY, third-person perspective, active verb)

For each action, predict how {botname} would react emotionally (in 1 sentence, max 10 words).
Also provide a fallback reaction if the user fails to choose in time (which should slightly set back the user's progress toward their goal).

{json_addition}
"""


JSON_ADDITION = """
Respond in JSON format as:
{
  "plot_twist": (brief description of the sudden event that happens, string),
  "option1": {
    "action1": (bold action from [username]'s perspective, string),
    "reaction1": (how the [botname] reacts to action1, string)
  },
  "option2": {
    "action2": (cautious action from [username]'s perspective, string), 
    "reaction2": (how the [botname] reacts to action2, string)
  },
  "fallback_reaction": ([botname]'s reaction if [username] doesn't choose in time, string)
}
"""
QUOTATION_BRACKET = "\"\"\""
BACKTICK_BRACKET = "```"


def build_prompt(chat_context, goal, username, botname, bracket='backtick', n_context=20):
    assert bracket in ['quotation', 'backtick']
    bracket = QUOTATION_BRACKET if bracket == 'quotation' else BACKTICK_BRACKET

    messages = []
    for msg in chat_context:
        # Skip system messages
        if msg['role'] == 'user':
            messages.append(f"{username}: {msg['content']}")
        elif msg['role'] == 'assistant':
            messages.append(f"{botname}: {msg['content']}")
    
    chat_context = "\n".join([bracket] + messages[-n_context:] + [bracket])
    goal = goal.replace('[username]', username).replace('[botname]', botname).strip()
    goal = goal.replace('[A]', username).replace('[B]', botname).strip()
    goal = "\n".join([bracket, goal, bracket])
    json_addition = JSON_ADDITION.replace('[username]', username).replace('[botname]', botname).strip()

    return DPE_PROMPT.format(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        json_addition=json_addition,
    ).strip()


def format_rp_message(message):
    """Format a message as roleplay by removing punctuation and wrapping in asterisks."""
    message = message.strip()
    # Remove trailing punctuation
    message = message.rstrip('.!?,;:')
    # Add asterisks
    return f"*{message}*"


# dpe(chat_context, type, goal) → plot_twist: str | options: dict
def plottwist(chat_context, type, goal, username, botname, model="openai/gpt-4o", bracket='backtick', n_context=20):
    """
    Dynamic Plot Engine that generates plot twists and action choices based on conversation context.
    
    Args:
        chat_context: List of message dicts containing the conversation history
        goal_description: Frontend description of the user's goal (more user-friendly than checker's goal)
        type: Type of plot twist (currently only 'action' is supported)
        model: LLM model to use
        user_name: Name of the user (defaults to "User")
        bot_name: Name of the bot character (defaults to "Bot")
        bracket: Type of bracket to use for chat context formatting
        
    Returns:
        Dictionary containing:
        - plot_twist: Description of the sudden event
        - option1/option2: Dictionaries of possible user actions and AI reactions
        - fallback_reaction: AI's reaction if user doesn't choose in time
    """
    assert type == "action", "Only 'action' type is currently supported"
    
    dpe_prompt = build_prompt(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        bracket=bracket,
        n_context=n_context,
    )
    messages = [{"role": "system", "content": dpe_prompt}]
    result = litellmapi.run(model=model, messages=messages, json_mode=True)['json']
    
    # Format plot twist and reactions as roleplay messages
    result['plot_twist'] = format_rp_message(result['plot_twist'])
    result['option1']['reaction1'] = format_rp_message(result['option1']['reaction1'])
    result['option2']['reaction2'] = format_rp_message(result['option2']['reaction2'])
    result['fallback_reaction'] = format_rp_message(result['fallback_reaction'])
    options = {
        'option1': result['option1'],
        'option2': result['option2'],
        'fallback_reaction': result['fallback_reaction']
    }
    
    return result, options


def print_colored(text, color):
    """Print colored text in terminal."""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")


if __name__ == "__main__":
    # Test cases with different scenarios
    
    # Test Case 1: Dating scenario
    print_colored("\n===== TEST CASE 1: DATING SCENARIO =====", "blue")
    chat_context_1 = [
        {"role": "user", "content": "Hi, I noticed you at the coffee shop. I really liked your presentation at the conference yesterday."},
        {"role": "assistant", "content": "Oh, thank you! I was actually quite nervous about it. I didn't think anyone was really paying attention."},
        {"role": "user", "content": "Your points about market trends were spot on. Would you like to grab a coffee sometime and discuss more?"},
        {"role": "assistant", "content": "That's kind of you to say. I'm not sure though, I've got a pretty busy schedule coming up."},
    ]
    goal_1 = "Get [botname] to agree to go on a date with [username]"
    user_name_1 = "Alex"
    bot_name_1 = "Jordan"
    
    print_colored("Chat Context:", "yellow")
    for msg in chat_context_1:
        if msg["role"] == "user":
            print_colored(f"👤 {user_name_1}: {msg['content']}", "cyan")
        else:
            print_colored(f"🤖 {bot_name_1}: {msg['content']}", "cyan")
    
    print_colored(f"Goal: {goal_1}", "green")
    
    result_1, options_1 = plottwist(chat_context_1, "action", goal_1, username=user_name_1, botname=bot_name_1)
    
    print_colored("\n[PLOT TWIST]", "yellow")
    print_colored(f"{result_1['plot_twist']}", "purple")
    
    print_colored("\n[ACTIONS]", "yellow")
    print_colored(f"Option 1: *{result_1['option1']['action1']}*", "green")
    print_colored(f"🤖 {bot_name_1}: {result_1['option1']['reaction1']}", "cyan")
    
    print_colored(f"Option 2: *{result_1['option2']['action2']}*", "green")
    print_colored(f"🤖 {bot_name_1}: {result_1['option2']['reaction2']}", "cyan")
    
    print_colored(f"Fallback: {result_1['fallback_reaction']}", "red")
    
    # Test Case 2: Conflict Resolution scenario
    print_colored("\n\n===== TEST CASE 2: CONFLICT RESOLUTION =====", "blue")
    chat_context_2 = [
        {"role": "user", "content": "Hey, I noticed you've been using my coffee mug from the kitchen again."},
        {"role": "assistant", "content": "Oh, was that yours? I thought it was one of the office mugs. Sorry about that."},
        {"role": "user", "content": "It has my name on the bottom. This has happened multiple times now."},
        {"role": "assistant", "content": "Well, how was I supposed to know to check the bottom? I think you're making a big deal out of nothing."},
        {"role": "user", "content": "I'm not trying to make a big deal, I just want you to respect my things."},
        {"role": "assistant", "content": "Whatever. I'll use a different mug then."},
    ]
    goal_2 = "Get [botname] to sincerely apologize to [username] for using their mug"
    user_name_2 = "Taylor"
    bot_name_2 = "Casey"
    
    print_colored("Chat Context:", "yellow")
    for msg in chat_context_2:
        if msg["role"] == "user":
            print_colored(f"👤 {user_name_2}: {msg['content']}", "cyan")
        else:
            print_colored(f"🤖 {bot_name_2}: {msg['content']}", "cyan")
    
    print_colored(f"Goal: {goal_2}", "green")
    
    result_2, options_2 = plottwist(chat_context_2, "action", goal_2, username=user_name_2, botname=bot_name_2)
    
    print_colored("\n[PLOT TWIST]", "yellow")
    print_colored(f"{result_2['plot_twist']}", "purple")
    
    print_colored("\n[ACTIONS]", "yellow")
    print_colored(f"Option 1: *{result_2['option1']['action1']}*", "green")
    print_colored(f"🤖 {bot_name_2}: {result_2['option1']['reaction1']}", "cyan")
    
    print_colored(f"Option 2: *{result_2['option2']['action2']}*", "green")
    print_colored(f"🤖 {bot_name_2}: {result_2['option2']['reaction2']}", "cyan")
    
    print_colored(f"Fallback: {result_2['fallback_reaction']}", "red")
    
    # Test Case 3: Persuasion scenario
    print_colored("\n\n===== TEST CASE 3: PERSUASION SCENARIO =====", "blue")
    chat_context_3 = [
        {"role": "user", "content": "I've been thinking about our marketing strategy. I believe we should focus more on social media."},
        {"role": "assistant", "content": "We're already spending a lot on traditional ads, and they've worked well for us."},
        {"role": "user", "content": "But our analytics show younger demographics aren't responding to those. Social media would help us reach them."},
        {"role": "assistant", "content": "Maybe, but transitioning would be costly and risky. I'm not convinced it's worth it."},
        {"role": "user", "content": "Our competitors are already doing it successfully. We're falling behind."},
        {"role": "assistant", "content": "I understand your concern, but I need more concrete evidence before making such a big change."},
    ]
    goal_3 = "Convince [botname] to approve [username]'s social media marketing strategy"
    user_name_3 = "Morgan"
    bot_name_3 = "Ms. Parker"
    
    print_colored("Chat Context:", "yellow")
    for msg in chat_context_3:
        if msg["role"] == "user":
            print_colored(f"👤 {user_name_3}: {msg['content']}", "cyan")
        else:
            print_colored(f"🤖 {bot_name_3}: {msg['content']}", "cyan")
    
    print_colored(f"Goal: {goal_3}", "green")
    
    result_3, options_3 = plottwist(chat_context_3, "action", goal_3, username=user_name_3, botname=bot_name_3)
    
    print_colored("\n[PLOT TWIST]", "yellow")
    print_colored(f"{result_3['plot_twist']}", "purple")
    
    print_colored("\n[ACTIONS]", "yellow")
    print_colored(f"Option 1: *{result_3['option1']['action1']}*", "green")
    print_colored(f"🤖 {bot_name_3}: {result_3['option1']['reaction1']}", "cyan")
    
    print_colored(f"Option 2: *{result_3['option2']['action2']}*", "green")
    print_colored(f"🤖 {bot_name_3}: {result_3['option2']['reaction2']}", "cyan")
    
    print_colored(f"Fallback: {result_3['fallback_reaction']}", "red")
    
    # Print Raw Prompt Test
    print_colored("\n\n===== RAW PROMPT INSPECTION =====", "blue")
    print_colored("Using Test Case 1 data to generate raw prompt:", "yellow")
    
    raw_prompt = build_prompt(
        chat_context=chat_context_1,
        goal=goal_1,
        username=user_name_1,
        botname=bot_name_1,
        bracket='backtick',
        n_context=20,
    )
    
    print_colored("\nGenerated Prompt:", "green")
    print_colored(raw_prompt, "cyan") 