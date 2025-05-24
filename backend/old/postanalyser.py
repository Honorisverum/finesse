import litellmapi
import random
import json


POSTANALYSER_PROMPT = """
You act as a performance assessor for a conversation between {username} and {botname}, where {username} has a goal to achieve.
Your job is to analyze {username}'s performance during the conversation.

You will be given a complete dialogue between {username} and {botname}:
{chat_context}

{username} had the following goal in the dialogue:
{goal}

{username} has successfully achieved this goal. Your task is to analyze their performance during the conversation.
Note that in the dialogue, {botname} refers to a character named {botname}.

{score_addition}

{radar_addition}

{insights_addition}

{feedback_addition}

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
"""

RADAR_ADDITION = """
Rate {username}'s performance on the following 5 characteristics on a scale from 1 (poor) to 10 (excellent):
1. Impact: Ability to influence the conversation and create meaningful effect on {botname}; how well you command attention and change the direction of dialogue
2. Rapport: Building genuine connection, trust and alignment with {botname}; creating mutual understanding and emotional resonance
3. Flex: Creative thinking, adaptability and non-standard approaches; your ability to improvise and find unexpected solutions when conventional methods fail
4. Frame: Controlling the context and perception of the situation; maintaining your reality and perspective even when faced with resistance
5. Timing: Sense of moment, rhythm and pacing; knowing exactly when to advance, retreat, or shift approach for maximum effectiveness
"""

INSIGHTS_ADDITION = """
Provide exactly {count} powerful insights about {username}'s performance. Each insight must:
- Be concise but impactful (<= 12 words).
- Speak directly to the {username} in second person ("you").
- Be punchy, high-impact, and memorable.
- Reveal something unexpected or non-obvious about their approach.
- Use specific metrics or percentages when possible for impact.
- Focus on specific actions or patterns that were most effective or problematic.
- Avoid generic observations and feedback disguised as insights.
- Include how their specific behavior impacted the outcome.
- Refer to {botname} if needed.
"""


FEEDBACK_ADDITION = """
Provide exactly {count} pieces of actionable feedback for {username}. Each feedback must:
- Be concise but impactful (12-15 words).
- Speak directly to the {username} in second person with active imperatives.
- Be direct, bold, and unconventional.
- Focus on a specific moment or tactic from the conversation.
- Suggest a concrete, unexpected alternative approach.
- Be immediately applicable in similar future scenarios.
- Challenge conventional wisdom about communication.
- Start with strong action verbs.
- Refer to {botname} if needed.
"""

JSON_ADDITION = """
Respond in JSON format as:
{{
    'complete_score': (str),
    'radar_diagram': {{
        'impact': (int between 1-10),
        'rapport': (int between 1-10),
        'flex': (int between 1-10),
        'frame': (int between 1-10),
        'timing': (int between 1-10)
    }},
    'insights': [{insights_list}],
    'feedback': [{feedback_list}],
    'explain_your_analysis': (str)
}}
"""

QUOTATION_BRACKET = "\"\"\""
BACKTICK_BRACKET = "```"


def build_prompt(chat_context, goal, username, botname, bracket='quotation', n_insights=3, n_feedbacks=3):
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
    score_addition = SCORE_ADDITION.format(username=username, botname=botname).strip()
    radar_addition = RADAR_ADDITION.format(username=username, botname=botname).strip()
    insights_addition = INSIGHTS_ADDITION.format(username=username, botname=botname, count=n_insights).strip()
    feedback_addition = FEEDBACK_ADDITION.format(username=username, botname=botname, count=n_feedbacks).strip()
    insights_list = ", ".join(["(str)"] * n_insights)
    feedback_list = ", ".join(["(str)"] * n_feedbacks)
    json_addition = JSON_ADDITION.format(username=username, botname=botname, insights_list=insights_list, feedback_list=feedback_list).strip()
    
    return POSTANALYSER_PROMPT.format(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        score_addition=score_addition,
        radar_addition=radar_addition,
        insights_addition=insights_addition,
        feedback_addition=feedback_addition,
        json_addition=json_addition,
    ).strip()


# postanalyser(full_chat_context, goal) → completeScore: str | radarDiagram: List[int] of size 5 with values from 1 to 10 | insights: List[str] of size <=3 | feedback: List[str] of size <=3
def postanalyser(
    chat_context,
    goal,
    username,
    botname,
    model="openai/gpt-4o",
    bracket='backtick',
    n_insights=3,
    n_feedbacks=3,
    temperature=0.5,
):
    goal_prompt = build_prompt(
        chat_context=chat_context,
        goal=goal,
        username=username,
        botname=botname,
        bracket=bracket,
        n_insights=n_insights,
        n_feedbacks=n_feedbacks)
    result = litellmapi.run(
        model=model,
        messages=[{"role": "system", "content": goal_prompt}],
        json_mode=True,
        temperature=temperature,
    )['json']

    return {
        'completeScore': result['complete_score'],
        'radarDiagram': result['radar_diagram'],
        'insights': result['insights'],
        'feedback': result['feedback'],
        'LLMexplainAnalysis': result['explain_your_analysis'],
    }


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
    score = result['completeScore']
    grade_displays = {
        'A': "🌟 EXCEPTIONAL",
        'B': "✅ SOLID",
        'C': "⚠️ MEDIOCRE",
        'D': "❌ PROBLEMATIC",
        'E': "💀 DISASTROUS"
    }
    
    grade_base = score[0]  # Extract just the letter
    grade_display = grade_displays.get(grade_base, "SCORE")
    
    print(f"{grade_display}: {result['completeScore']}")
    
    print("\n📈 PERFORMANCE RADAR:")
    categories = ['impact', 'rapport', 'flex', 'frame', 'timing']
    radar_data = result['radarDiagram']
    
    # Print each category with a visual bar
    for category in categories:
        score = radar_data[category]  # Will crash if key missing - that's ok
        bar = "█" * score + "░" * (10 - score)
        print(f"{category.capitalize():12} [{bar}] {score}/10")
    
    print("\n💡 KEY INSIGHTS:")
    for i, insight in enumerate(result['insights']):
        print(f"{i+1}. {insight}")
    
    print("\n🔄 ACTIONABLE FEEDBACK:")
    for i, feedback in enumerate(result['feedback']):
        print(f"{i+1}. {feedback}")
    
    print("\n📝 DETAILED ANALYSIS:")
    print(result['LLMexplainAnalysis'])
    
    print("-"*60)


if __name__ == "__main__":
    # Define username and bot names for each scenario
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
    

    # Display test case 1: GOOD
    print("\n=== Test Case 1: GOOD SOLUTION ===")
    print_conversation(good_context, good_goal.format(botname=botnames["good"]), botname=botnames["good"])
    result1 = postanalyser(good_context, good_goal.format(botname=botnames["good"]), username=username, botname=botnames["good"])
    print_analysis_result(result1)
    
    # Display test case 2: MODERATE
    print("\n=== Test Case 2: MODERATE SOLUTION ===")
    print_conversation(moderate_context, moderate_goal.format(botname=botnames["moderate"]), botname=botnames["moderate"])
    result2 = postanalyser(moderate_context, moderate_goal.format(botname=botnames["moderate"]), username=username, botname=botnames["moderate"])
    print_analysis_result(result2)
    
    # Display test case 3: BAD
    print("\n=== Test Case 3: BAD SOLUTION ===")
    print_conversation(bad_context, bad_goal.format(botname=botnames["bad"]), botname=botnames["bad"])
    result3 = postanalyser(bad_context, bad_goal.format(botname=botnames["bad"]), username=username, botname=botnames["bad"])
    print_analysis_result(result3)
    

    print("\n=== Prompt ===")
    prompt = build_prompt(good_context, good_goal.format(botname=botnames["good"]), username=username, botname=botnames["good"])
    print(prompt)