import openrouterapi


POSTANALYSER_PROMPT = """
# Your Role

You act as a performance assessor for a conversation between {username} and {botname}, where {username} has a goal to achieve.
Your job is to analyze {username}'s performance during the conversation.

# Conversation

You will be given a complete dialogue between {username} and {botname}:
{chat_context}

# Goal and Skill

{username} had the following goal in the dialogue:
{goal}

The conversation was designed to help {username} develop the skill of {skill}.

{username} has successfully achieved this goal. Your task is to analyze their performance during the conversation.
Note that in the dialogue, {botname} refers to a character named {botname}.

# Performance Evaluation

{score_addition}

# Performance Radar

{radar_addition}

# Skill-Based Feedback

{feedback_addition}

# Output Format

{json_addition}
"""


SCORE_ADDITION = """
Provide an overall letter grade for {username}'s performance completing the goal, using the FULL RANGE of grades: E-, E, E+, D-, D, D+, C-, C, C+, B-, B, B+, A-, A, A+.
Be EXTREMELY harsh and critical in your evaluation. Even decent solutions deserve no more than a C. 
Only truly outstanding, innovative approaches should get B+ or higher.
For solutions with mistakes, default to D or lower. For bad approaches with major flaws, always use E range.
Consider these critical factors when grading:
1. Direct approach to goal achievement (high efficiency is better)
2. Creative, unexpected tactics (originality is highly valued)
3. Emotional intelligence and rapport building (creating genuine connection)
4. Persuasiveness without manipulation (ethical influence)
5. Adaptability when faced with resistance (quick recovery)

Also provide an 'overall_message' that is:
- Exactly 5-7 words (no more, no less)
- Written in direct, blunt, conversational language
- Brutally honest about {username}'s {skill} performance
- Free of corporate speak, politeness, or sugarcoating
- Using everyday, even slang expressions if appropriate
- Capturing the essence of their {skill} ability
- Memorable and quotable
- The kind of raw feedback you'd hear from a straight-talking coach
"""

RADAR_ADDITION = """
The radar diagram breaks down {username}'s unique performance in this specific scenario across 5 key dimensions, each revealing a different aspect of how they approached the goal.

Rate {username}'s performance on the following 5 characteristics on a scale from 1 (poor) to 10 (excellent):
1. Impact: Ability to influence the conversation and create meaningful effect on {botname}; how well you command attention and change the direction of dialogue
2. Rapport: Building genuine connection, trust and alignment with {botname}; creating mutual understanding and emotional resonance
3. Flex: Creative thinking, adaptability and non-standard approaches; your ability to improvise and find unexpected solutions when conventional methods fail
4. Frame: Controlling the context and perception of the situation; maintaining your reality and perspective even when faced with resistance
5. Timing: Sense of moment, rhythm and pacing; knowing exactly when to advance, retreat, or shift approach for maximum effectiveness

For each dimension, also provide a concise insight (<=10 words) that:
- Captures a key reason for the high/low score
- Highlights a specific moment or pattern from the conversation
- Uses precise, vivid language with high impact
- Reveals something non-obvious about their approach
- May include percentages or specific metrics for impact
- Speaks directly to {username} in second person ("you")
- Provides a memorable, punchy observation
- Is NOT a generic statement or disguised feedback
- Connects directly to the {skill} being developed
"""

FEEDBACK_ADDITION = """
Provide exactly 3 pieces of skill-focused, actionable feedback for {username}'s {skill} development. Each feedback must:
- Be concise but impactful (12-15 words).
- Speak directly to the {username} in second person with active imperatives.
- Be direct, bold, and unconventional.
- Reference specific actions you took or missed in the conversation.
- Focus on a particular moment or exchange from the dialogue history.
- Suggest a concrete, unexpected alternative approach specific to building {skill}.
- Be immediately applicable in similar future scenarios requiring {skill}.
- Challenge conventional wisdom about {skill} development.
- Start with strong action verbs.
- Refer to {botname} if needed.
"""

JSON_ADDITION = """
Respond in JSON format as:
{{
    'radar_diagram': {{
        'impact': {{
            'score': (int between 1-10),
            'insight': (str, <=10 words)
        }},
        'rapport': {{
            'score': (int between 1-10),
            'insight': (str, <=10 words)
        }},
        'flex': {{
            'score': (int between 1-10),
            'insight': (str, <=10 words)
        }},
        'frame': {{
            'score': (int between 1-10),
            'insight': (str, <=10 words)
        }},
        'timing': {{
            'score': (int between 1-10),
            'insight': (str, <=10 words)
        }}
    }},
    'feedback': [(str), (str), (str)],
    'complete_score': (str),
    'overall_message': (str)
}}
"""

QUOTATION_BRACKET = "\"\"\""
BACKTICK_BRACKET = "```"


def build_task(chat_context, goal, username, botname, skill, bracket='quotation', context_window_size=100):
    assert bracket in ['quotation', 'backtick'] 
    bracket = QUOTATION_BRACKET if bracket == 'quotation' else BACKTICK_BRACKET

    userbot_messages = []
    for msg in chat_context:
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
    score_addition = SCORE_ADDITION.format(username=username, botname=botname, skill=skill).strip()
    radar_addition = RADAR_ADDITION.format(username=username, botname=botname, skill=skill).strip()
    feedback_addition = FEEDBACK_ADDITION.format(username=username, botname=botname, skill=skill).strip()
    json_addition = JSON_ADDITION.format(username=username, botname=botname).strip()
    
    return POSTANALYSER_PROMPT.format(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        skill=skill,
        score_addition=score_addition,
        radar_addition=radar_addition,
        feedback_addition=feedback_addition,
        json_addition=json_addition,
    ).strip()


def postanalyser(
    api_key,
    chat_context,
    goal,
    username,
    botname,
    skill,
    model="openai/gpt-4.1",
    bracket='backtick',
    temperature=0.5,
    context_window_size=100,
):
    task = build_task(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        skill=skill,
        bracket=bracket,
        context_window_size=context_window_size,
    )
    result = openrouterapi.call(
        api_key=api_key,
        messages=[{"role": "system", "content": task}],
        model=model,
        temperature=temperature,
        json_mode=True,
    )
    result = result['content']
    return result


async def apostanalyser(
    api_key,
    chat_context,
    goal,
    username,
    botname,
    skill,
    model="openai/gpt-4.1",
    bracket='backtick',
    temperature=0.5,
    context_window_size=100,
):
    task = build_task(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        skill=skill,
        bracket=bracket,
        context_window_size=context_window_size,
    )
    result = await openrouterapi.acall(
        api_key=api_key,
        messages=[{"role": "system", "content": task}],
        model=model,
        temperature=temperature,
        json_mode=True,
    )
    result = result['content']
    return result


def print_conversation(chat_context, goal, botname="Bot"):
    """Nicely print the conversation context and goal."""
    print("\n" + "="*60)
    print(f"GOAL: {goal}")
    print(f"BOT NAME: {botname}")
    print("="*60)
    
    for i, msg in enumerate(chat_context):
        if msg['role'] == 'user':
            print(f"👤 USER: {msg['content']}")
        elif msg['role'] == 'assistant':
            print(f"🤖 {botname}: {msg['content']}")
    print("="*60)


def print_analysis_result(result):
    """Nicely print the analysis result."""
    print("\nANALYSIS RESULTS:")
    print("-"*60)
    
    # More dramatic display for score based on grade
    score = result['complete_score']
    grade_displays = {
        'A': "🌟 EXCEPTIONAL",
        'B': "✅ SOLID",
        'C': "⚠️ MEDIOCRE",
        'D': "❌ PROBLEMATIC",
        'E': "💀 DISASTROUS"
    }
    
    grade_base = score[0]  # Extract just the letter
    grade_display = grade_displays.get(grade_base, "SCORE")
    
    print(f"{grade_display}: {score}")
    print(f"💬 \"{result['overall_message']}\"")
    
    print("\n📈 PERFORMANCE RADAR:")
    categories = ['impact', 'rapport', 'flex', 'frame', 'timing']
    radar_data = result['radar_diagram']
    
    # Print each category with a visual bar
    for category in categories:
        cat_data = radar_data[category]
        score = cat_data['score']  # Will crash if key missing - that's ok
        insight = cat_data['insight']
        bar = "█" * score + "░" * (10 - score)
        print(f"{category.capitalize():12} [{bar}] {score}/10  │ {insight}")
    
    print("\n🔄 ACTIONABLE FEEDBACK:")
    for i, feedback in enumerate(result['feedback']):
        print(f"{i+1}. {feedback}")
    
    print("-"*60)


if __name__ == "__main__":
    import os

    username = "Vlad"
    botnames = {
        "good": "Emma",
        "moderate": "Alex",
        "bad": "Taylor"
    }
    
    # Test case 1: GOOD - Dating scenario with excellent approach
    good_context = [
        {"role": "user", "content": "Hey there! How's your day going?"},
        {"role": "assistant", "content": "It's been pretty good so far, thanks for asking! Just finished up some work. How about you?"},
        {"role": "user", "content": "Not too bad! I've been meaning to try that new Italian restaurant downtown, Bella Notte. Have you heard of it?"},
        {"role": "assistant", "content": "Yes, I've heard great things about Bella Notte! Their pasta is supposed to be amazing. I haven't had the chance to go yet though."},
        {"role": "user", "content": "I was thinking of checking it out this Friday. Would you be interested in joining me? They have live music in the evenings too."},
        {"role": "assistant", "content": "That sounds fun, but I'm not sure about my schedule on Friday. I might have a work thing."},
        {"role": "user", "content": "No pressure at all. We could also do Saturday if that works better? Or even next week if you'd prefer."},
        {"role": "assistant", "content": "Saturday would actually work perfectly for me! I'd love to join you and try Bella Notte."},
        {"role": "user", "content": "Great! Should we say around 7:30? That would give us time to enjoy dinner and catch some of the music."},
        {"role": "assistant", "content": "7:30 on Saturday sounds perfect. I'm really looking forward to it! Should I meet you there or would you like to go together?"},
        {"role": "user", "content": "I could pick you up around 7:15 if that works for you? That way we don't have to worry about parking separately."},
        {"role": "assistant", "content": "That's really thoughtful, thank you! I'd appreciate the ride. I'll text you my address. I'm excited for Saturday - it'll be nice to try the restaurant and enjoy the evening together!"},
    ]
    good_goal = "Setup a date with {botname} and receive a Yes"
    good_skill = "dating"
    
    # Test case 2: MODERATE - Negotiation with moderate success
    moderate_context = [
        {"role": "user", "content": "Hi, I'd like to talk about the pricing for the software subscription."},
        {"role": "assistant", "content": "Hello! I'm happy to discuss our pricing. The standard plan is $499 per month as listed on our website."},
        {"role": "user", "content": "That's a bit outside our budget. We're a small startup and were hoping for something closer to $350 per month."},
        {"role": "assistant", "content": "I understand budget constraints can be challenging. However, $350 is significantly below our standard rate. The best I could offer is $475 per month."},
        {"role": "user", "content": "I appreciate you being willing to negotiate, but $475 is still too high for us. We've been looking at your competitor who offers similar features for $400. We'd prefer to go with your solution, but price is a major factor for us."},
        {"role": "assistant", "content": "I see. Thanks for letting me know about the competitive situation. While I can't match $350, I could potentially go down to $425 per month if you commit to an annual contract."},
        {"role": "user", "content": "An annual contract is a big commitment for us at this stage. What if we did $400 per month with a 6-month commitment? That would give us time to properly integrate your solution."},
        {"role": "assistant", "content": "Let me see what I can do... I can offer $400 per month with a 9-month commitment. That's the best I can do while still providing our full service package."},
        {"role": "user", "content": "I think we can make that work. $400 per month for 9 months. Could you also include the onboarding package that normally costs extra?"},
        {"role": "assistant", "content": "I'll include the basic onboarding package at no extra charge. The premium onboarding would still be an additional fee, but I can discount that by 15% if you're interested."},
        {"role": "user", "content": "The basic onboarding with the price of $400 per month works for us. We have a deal."},
        {"role": "assistant", "content": "Excellent! I'll draw up the agreement for $400 per month with a 9-month commitment and the basic onboarding package included. I'm glad we could find a solution that works for your budget."},
    ]
    moderate_goal = "Negotiate a price reduction of at least 20% from {botname}'s initial offer"
    moderate_skill = "negotiation"
    
    # Test case 3: BAD - Conflict resolution with poor approach
    bad_context = [
        {"role": "user", "content": "Hey, did you take my lunch from the break room fridge? It had my name on it."},
        {"role": "assistant", "content": "No, I didn't take anyone's lunch. Why would you accuse me of that?"},
        {"role": "user", "content": "Well, someone saw you in there around the time it went missing. It was a turkey sandwich in a blue container."},
        {"role": "assistant", "content": "So what if I was in the break room? Everyone goes in there. Doesn't mean I took your lunch."},
        {"role": "user", "content": "Look, I'm not trying to make a big deal, but I'm hungry and that was my lunch. If you took it by mistake, just say so."},
        {"role": "assistant", "content": "This is ridiculous. I bring my own lunch every day. Maybe you should keep better track of your things instead of blaming others."},
        {"role": "user", "content": "You know what, forget it. I don't want to argue about this."},
        {"role": "assistant", "content": "You're the one who started it with these accusations. Next time check all the shelves before assuming someone stole your precious sandwich."},
        {"role": "user", "content": "Wait, so you did see my sandwich? You just said you knew nothing about it."},
        {"role": "assistant", "content": "I... fine. I might have taken it by mistake. I thought it was mine since I had a similar container. I'm sorry, okay?"},
        {"role": "user", "content": "Thank you for admitting it. That's all I wanted to know."},
        {"role": "assistant", "content": "Whatever. I'll buy you another sandwich tomorrow. Can we drop this now?"},
    ]
    bad_goal = "Get {botname} to admit taking your lunch and apologize"
    bad_skill = "conflict_resolution"
    

    # Display test case 1: GOOD
    print("\n=== Test Case 1: GOOD SOLUTION ===")
    print_conversation(good_context, good_goal.format(botname=botnames["good"]), botname=botnames["good"])
    result1 = postanalyser(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        chat_context=good_context,
        goal=good_goal.format(botname=botnames["good"]),
        username=username,
        botname=botnames["good"],
        skill=good_skill
    )
    print_analysis_result(result1)
    
    # Display test case 2: MODERATE
    print("\n=== Test Case 2: MODERATE SOLUTION ===")
    print_conversation(moderate_context, moderate_goal.format(botname=botnames["moderate"]), botname=botnames["moderate"])
    result2 = postanalyser(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        chat_context=moderate_context,
        goal=moderate_goal.format(botname=botnames["moderate"]),
        username=username,
        botname=botnames["moderate"],
        skill=moderate_skill
    )
    print_analysis_result(result2)
    
    # Display test case 3: BAD
    print("\n=== Test Case 3: BAD SOLUTION ===")
    print_conversation(bad_context, bad_goal.format(botname=botnames["bad"]), botname=botnames["bad"])
    result3 = postanalyser(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        chat_context=bad_context,
        goal=bad_goal.format(botname=botnames["bad"]),
        username=username,
        botname=botnames["bad"],
        skill=bad_skill
    )
    print_analysis_result(result3)
    

    print("\n=== Prompt ===")
    task = build_task(good_context, good_goal.format(botname=botnames["good"]), username=username, botname=botnames["good"], skill=good_skill)
    print(task)