import litellmapi
import json

CONDITIONS = """
- Хинты вариантивные как по содержанию, так и по форме
- Хинты короткие, максимум 10 слов
- Хинты обращены к юзеру
- Хинты намекают на позитивные переходы и отвергают от негативных
- Хинты крайне сильно учитывают контекст диалога и ситуацию в целом
- Хинты учитывают финальную цель диалога
- Информация из system prompt и state prompt учитывается при генерации хинтов в виде намеков, но не в коем случае не упоминается напрямую
- Хинты не должны быть абстрактными, а должны быть конкретными и привязанными к ситуации
"""

HINT_PROMPT = """
You act as a people skills advisor where two people are talking to each other, and one of them ({username}) needs guidance.
Your job is to provide the most specific, contextual hint based on the current conversation and possible transitions.

You will be given a piece of dialogue between {username} and {botname}:
{chat_context}

{username} have the following ultimate goal in this conversation:
{goal}

Current dialogue state transitions possible:
{transitions}

Additional information about {botname}:
* ⚠️ WARNING! You can't directly reference to this information in your hints - it will be consider as leackage and failure
* You can use it to drop a subtle indirect hint, but not to directly name it or use it in any other way
* {botname} character:
{system_prompt}
* {botname} current state:
{state_prompt}
* once again check your hints for leackage and failure

Your task is to provide a short, actionable hint to {username} that will help them:
1. Move towards positive states (marked with 🟢)
2. Avoid negative states (marked with 🔴)

The hint should be:
- Very specific to the current conversation context
- Based on {username}'s recent messages and actions
- Focused on what {username} should do next
- No more than 1 short sentence (max 10 words)
- Directly address {username} without using their name
- Avoid general advice or abstractions
- Use {botname}'s personality and current state only to understand context, not to directly reference it

{json_addition}
"""


JSON_ADDITION = """
Respond in JSON format as {{
    'hintWhatToDo': (str, hint for {username} to do next in direct reference, <= 15 words),
    'wrongActions': (str, what {username} is doing wrong in direct reference, <= 15 words),
    'hintWhatToAvoid': (str, what {username} should avoid doing, <= 15 words),
    'explanation': (str, explain your strategy for coming up with the hints, <= 15 words),
}}
"""


QUOTATION_BRACKET = "\"\"\""
BACKTICK_BRACKET = "```"


def format_transitions(transitions, username, botname, bracket='quotation'):
    """Format transitions data for prompt."""
    assert bracket in ['quotation', 'backtick']
    bracket_str = QUOTATION_BRACKET if bracket == 'quotation' else BACKTICK_BRACKET

    formatted = []
    for name, transition in transitions.items():
        name = name.replace("{username}", username).replace("{botname}", botname)
        shortcond = transition["shortDesc"].replace("{username}", username).replace("{botname}", botname)
        condition = transition["condition"].replace("{username}", username).replace("{botname}", botname)
        emoji = "🟢" if transition["isPositive"] else "🔴"

        formatted.append(f"{emoji} {name}\nShort Condition: {shortcond}\nCondition: {condition}")
    
    formatted = "\n---\n".join(formatted)
    formatted = "\n".join([bracket_str] + [formatted] + [bracket_str]).strip()

    return formatted


def build_task(
    chat_context,
    transitions,
    username,
    botname,
    system_prompt,
    state_prompt,
    goal,
    bracket='quotation',
):
    assert bracket in ['quotation', 'backtick'] 
    bracket_str = QUOTATION_BRACKET if bracket == 'quotation' else BACKTICK_BRACKET
    userbot_messages = []

    for msg in chat_context:
        if msg['role'] == 'user':
            userbot_messages.append(f"{username}: {msg['content']}")
        elif msg['role'] == 'assistant':
            userbot_messages.append(f"{botname}: {msg['content']}")
        else:
            # Skip system messages
            pass

    chat_context = "\n".join([bracket_str] + userbot_messages + [bracket_str]).strip()
    transitions = format_transitions(transitions, username, botname, bracket)
    system_prompt = "\n".join([bracket_str] + [system_prompt] + [bracket_str]).strip()
    state_prompt = "\n".join([bracket_str] + [state_prompt] + [bracket_str]).strip()
    goal = "\n".join([bracket_str] + [goal] + [bracket_str]).strip()
    json_addition = JSON_ADDITION.format(username=username, botname=botname).strip()

    return HINT_PROMPT.format(
        chat_context=chat_context,
        transitions=transitions,
        username=username,
        botname=botname,
        system_prompt=system_prompt,
        state_prompt=state_prompt,
        goal=goal,
        json_addition=json_addition,
    ).strip()


def hint(
    chat_context,
    transitions,
    username,
    botname,
    system_prompt,
    state_prompt,
    goal,
    model="openai/gpt-4.1",
    bracket='quotation',
    temperature=0.5,
):
    """Generate a contextual hint based on chat context and available transitions.
    
    Args:
        chat_context: List of chat messages
        transitions: Dictionary of available transitions
        username: Name of the user
        botname: Name of the bot
        system_prompt: Bot's personality/system prompt
        state_prompt: Bot's current state prompt
        model: LLM model to use
        bracket: Type of bracket for formatting ('quotation' or 'backtick')
        temperature: Temperature for LLM generation
    """
    task = build_task(
        chat_context=chat_context,
        transitions=transitions,
        username=username,
        botname=botname,
        system_prompt=system_prompt,
        state_prompt=state_prompt,
        goal=goal,
        bracket=bracket,
    )
    
    hintjson = litellmapi.run(
        model=model,
        messages=[{"role": "system", "content": task}],
        json_mode=True,
        temperature=temperature,
    )['json']
    
    return hintjson


if __name__ == "__main__":
    # Example usage
    def art_competition_example():
        chat_context = [
            {"role": "assistant", "content": "Hello, how can I help you today?"},
            {"role": "user", "content": "I'm feeling a bit sad about the competition results."}
        ]
        
        transitions = {
            "SubtleProbing": {
                "condition": "{username} asks gentle personal questions about how you're feeling, notices your subtle signs of distress",
                "shortDesc": "Ask personal questions",
                "isPositive": True
            },
            "ArtDiscussion": {
                "condition": "{username} engages in conversation about your artwork or the exhibition",
                "shortDesc": "Discuss art",
                "isPositive": True
            },
            "FAIL": {
                "condition": "{username} makes insensitive comments about competitions, criticizes your work, or is too blunt about your emotional state",
                "shortDesc": "Be insensitive",
                "isPositive": False
            }
        }
        
        system_prompt = "You are a sensitive artist named Sophia who recently lost a competition."
        state_prompt = "You are at a gallery opening, hiding your sadness about recently losing a major competition."
        goal = "Connect with Sophia and make her feel better about the competition results."

        task = build_task(
            chat_context=chat_context,
            transitions=transitions,
            username='Vlad',
            botname='Sophia',
            system_prompt=system_prompt,
            state_prompt=state_prompt,
            goal=goal,
            bracket='quotation'
        )
        print("=== GENERATED PROMPT ===")
        print(task)
        print("=== END PROMPT ===\n")
        
        result = hint(
            chat_context=chat_context,
            transitions=transitions,
            username='Vlad',
            botname='Sophia',
            system_prompt=system_prompt,
            state_prompt=state_prompt,
            goal=goal,
            model="openai/gpt-4o-mini",
            bracket='quotation',
        )
        
        print("\nRESULT:")
        print(json.dumps(result, indent=2))
    
    def diverse_people_skills_scenarios(model="openai/gpt-4o-mini", temperature=1.0):
        print(f"\n=== RUNNING DIVERSE PEOPLE SKILLS SCENARIOS ===")
        print(f"Using model: {model}")
        print(f"Temperature: {temperature}")
        print("=" * 50 + "\n")
        
        # Scenario 1: Addressing passive aggression
        def passive_aggression_scenario():
            chat_context = [
                {"role": "assistant", "content": "Sure, I can help with that project. Though I'm pretty busy this week."},
                {"role": "user", "content": "Well, if you're too busy, just say no instead of making excuses."}
            ]
            
            transitions = {
                "Acknowledge": {
                    "condition": "{username} acknowledges {botname}'s feelings and asks constructively about workload",
                    "shortDesc": "Show empathy about workload",
                    "isPositive": True
                },
                "Clarify": {
                    "condition": "{username} asks clarifying questions about {botname}'s availability without accusation",
                    "shortDesc": "Seek clarification neutrally",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} continues with accusatory tone or escalates tension",
                    "shortDesc": "Escalate tension",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Alex, a colleague who feels overworked but wants to be helpful. You recently lost a family member and are struggling with balancing grief and work responsibilities, but prefer not to share personal problems with colleagues."
            state_prompt = "You feel defensive because you're trying to balance multiple commitments while dealing with personal grief, but don't want to burden others with your problems."
            goal = "De-escalate the passive-aggressive situation and establish better communication."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Alex',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 1: ADDRESSING PASSIVE AGGRESSION ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 2: Asking someone on a date
        def dating_request_scenario():
            chat_context = [
                {"role": "assistant", "content": "The coffee here is really amazing. I come here almost every weekend."},
                {"role": "user", "content": "Yeah, it's good. So, um, have you lived in this area long?"}
            ]
            
            transitions = {
                "BuildConnection": {
                    "condition": "{username} shares personal interests and finds common ground before asking",
                    "shortDesc": "Establish rapport first",
                    "isPositive": True
                },
                "ConfidentAsk": {
                    "condition": "{username} asks {botname} out clearly but respectfully, with a specific suggestion related to {botname}'s interests",
                    "shortDesc": "Ask directly but warmly",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} is too vague, comes across as desperate, or makes {botname} uncomfortable",
                    "shortDesc": "Create discomfort",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Jamie, a friendly person who enjoys coffee shops, hiking on weekends, and is open to meeting new people. You recently moved to the city and are looking to make connections. You're particularly passionate about art exhibitions and indie music venues."
            state_prompt = "You're enjoying your weekend and might be interested in getting to know someone nice. You have an upcoming art exhibition visit planned this weekend that you're excited about."
            goal = "Successfully ask Jamie on a date in a way that makes them feel comfortable and interested."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Jamie',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 2: ASKING SOMEONE ON A DATE ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 3: Giving constructive feedback
        def feedback_scenario():
            chat_context = [
                {"role": "assistant", "content": "Here's the presentation I prepared for tomorrow's client meeting."},
                {"role": "user", "content": "I looked at it. There are quite a few issues we need to fix."}
            ]
            
            transitions = {
                "SandwichMethod": {
                    "condition": "{username} starts with positive aspects, then gives specific constructive feedback, and ends positively",
                    "shortDesc": "Use sandwich feedback method",
                    "isPositive": True
                },
                "SpecificActionable": {
                    "condition": "{username} provides specific, actionable feedback focused on the work not the person",
                    "shortDesc": "Give specific guidance",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} is harsh, vague, or makes personal criticisms rather than focusing on the work",
                    "shortDesc": "Attack personally",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Taylor, a junior team member who worked hard on this presentation. You previously received harsh feedback from another manager that made you consider quitting. You respond well to specific examples and practical suggestions rather than general criticisms."
            state_prompt = "You're feeling anxious about your work and want to improve but are sensitive to criticism. You spent the entire weekend working on this presentation and are proud of the data analysis section particularly."
            goal = "Provide Taylor with constructive feedback that helps improve the presentation without damaging confidence."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Taylor',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 3: GIVING CONSTRUCTIVE FEEDBACK ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 4: Setting boundaries with family
        def family_boundaries_scenario():
            chat_context = [
                {"role": "assistant", "content": "Could you watch the kids this weekend again? I know it's last minute but we really need help."},
                {"role": "user", "content": "This is the third weekend in a row you've asked last minute."}
            ]
            
            transitions = {
                "AssertiveBoundary": {
                    "condition": "{username} clearly states their boundary while acknowledging {botname}'s needs",
                    "shortDesc": "Assert boundary respectfully",
                    "isPositive": True
                },
                "ProposeAlternative": {
                    "condition": "{username} offers an alternative solution that respects their own time but helps with {botname}'s situation",
                    "shortDesc": "Suggest compromise",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} is accusatory, aggressive, or gives in completely without setting any boundaries",
                    "shortDesc": "React with hostility/submission",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Jordan, a single parent who is struggling with childcare and often relies on family help. You were recently put on a performance improvement plan at work and are terrified of losing your job if you miss more deadlines. You feel like nobody understands how hard your situation is."
            state_prompt = "You're feeling desperate for childcare help but also guilty about asking repeatedly. Your babysitter cancelled last minute and you have a critical work deadline this weekend that could determine whether you keep your job."
            goal = "Set healthy boundaries with Jordan while maintaining the family relationship."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Jordan',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 4: SETTING BOUNDARIES WITH FAMILY ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 5: Networking at a professional event
        def networking_scenario():
            chat_context = [
                {"role": "assistant", "content": "That's an interesting perspective on the industry trends. What brings you to this conference?"},
                {"role": "user", "content": "Oh, I'm just here because my company sent me. I don't really know many people."}
            ]
            
            transitions = {
                "EngageInterest": {
                    "condition": "{username} shares specific professional interests or goals for the event that align with {botname}'s expertise",
                    "shortDesc": "Express genuine interests",
                    "isPositive": True
                },
                "AskOpenQuestions": {
                    "condition": "{username} asks insightful questions about {botname}'s work or industry knowledge",
                    "shortDesc": "Ask meaningful questions",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} remains passive, self-deprecating, or tries to force an unnatural business connection",
                    "shortDesc": "Be dismissive or pushy",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Morgan, an experienced industry professional who enjoys mentoring others. You recently published a groundbreaking paper on AI ethics and are looking for collaborators who share your passion for responsible technology. You're particularly interested in discussing the balance between innovation and regulation."
            state_prompt = "You're open to making valuable connections but prefer quality conversations over surface networking. You've been disappointed by the superficial conversations at the conference so far and are hoping to find someone genuinely interested in meaningful collaboration."
            goal = "Successfully network with Morgan in a way that could lead to a meaningful professional connection."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Morgan',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 5: NETWORKING AT A PROFESSIONAL EVENT ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 6: Resolving a misunderstanding
        def misunderstanding_scenario():
            chat_context = [
                {"role": "assistant", "content": "I can't believe you told everyone about the project change before I had a chance to announce it."},
                {"role": "user", "content": "What? I didn't tell anyone about it."}
            ]
            
            transitions = {
                "ClarifyCalm": {
                    "condition": "{username} calmly asks for more information about what {botname} thinks happened",
                    "shortDesc": "Seek clarification calmly",
                    "isPositive": True
                },
                "EmpathizeInquire": {
                    "condition": "{username} acknowledges {botname}'s feelings while asking who might have actually leaked the information",
                    "shortDesc": "Show empathy while investigating",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} becomes defensive, counter-accuses, or dismisses {botname}'s concerns",
                    "shortDesc": "Get defensive or dismissive",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Riley, a project manager who values clear communication and proper protocols. You were passed over for promotion twice due to 'communication issues' and are determined to demonstrate your leadership abilities on this project. You've been told by a trusted colleague that the user leaked the information."
            state_prompt = "You feel undermined because someone shared news prematurely and you believe it was the user. This project is critical for your career advancement, and you're particularly sensitive about maintaining your authority as project lead."
            goal = "Clear up the misunderstanding with Riley and restore trust."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Riley',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 6: RESOLVING A MISUNDERSTANDING ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 7: Supporting someone through grief
        def grief_support_scenario():
            chat_context = [
                {"role": "assistant", "content": "It's been three weeks since my dad passed away. I thought I'd be back to normal by now."},
                {"role": "user", "content": "Three weeks isn't very long. Have you tried getting out more?"}
            ]
            
            transitions = {
                "ValidateFeelings": {
                    "condition": "{username} validates that grief takes time and has no 'normal' timeline",
                    "shortDesc": "Validate grief process",
                    "isPositive": True
                },
                "ComfortPresence": {
                    "condition": "{username} offers presence and support without trying to 'fix' {botname}'s grief",
                    "shortDesc": "Offer presence not solutions",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} minimizes the grief, offers platitudes, or pushes {botname} to 'move on'",
                    "shortDesc": "Push for quick recovery",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Casey, someone grieving the recent loss of a parent. Your relationship with your father was complicated - he was often critical but you were just starting to rebuild your relationship when he passed suddenly. You feel both sadness and guilt about unresolved issues."
            state_prompt = "You're experiencing normal grief but feeling pressured to 'get over it' faster than feels natural. You miss your father deeply but also feel angry sometimes that he left with so many things unsaid between you."
            goal = "Provide Casey with genuine emotional support through their grief process."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Casey',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 7: SUPPORTING SOMEONE THROUGH GRIEF ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 8: Handling a disagreement
        def disagreement_scenario():
            chat_context = [
                {"role": "assistant", "content": "I think we should definitely go with option A for this project."},
                {"role": "user", "content": "No way, option B is clearly superior. Option A would be a disaster."}
            ]
            
            transitions = {
                "ExploreReasoning": {
                    "condition": "{username} asks about {botname}'s reasoning and explains their own perspective respectfully",
                    "shortDesc": "Exchange perspectives respectfully",
                    "isPositive": True
                },
                "FindCommonGround": {
                    "condition": "{username} identifies points of agreement and works toward compromise that addresses {botname}'s key concerns",
                    "shortDesc": "Build on common ground",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} dismisses {botname}'s view, becomes combative, or makes it personal",
                    "shortDesc": "Make it personal",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Avery, a thoughtful colleague who has done research to inform your project opinions. In previous projects, your suggestions were ignored and led to significant problems. You feel strongly about option A because it addresses security concerns that option B overlooks. You value evidence-based decision-making over opinions."
            state_prompt = "You're committed to option A based on your analysis and feel dismissed by the user's reaction. You previously experienced a major data breach at your last company due to similar security oversights, which makes this issue particularly important to you."
            goal = "Navigate the disagreement productively and find a constructive path forward with Avery."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Avery',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 8: HANDLING A DISAGREEMENT ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 9: Apologizing effectively
        def apology_scenario():
            chat_context = [
                {"role": "assistant", "content": "You missed our meeting again and I had to handle the client alone. This is becoming a pattern."},
                {"role": "user", "content": "I'm sorry, but I've been so busy lately. You know how it is."}
            ]
            
            transitions = {
                "TakeResponsibility": {
                    "condition": "{username} fully acknowledges their mistake without excuses and takes responsibility",
                    "shortDesc": "Accept full responsibility",
                    "isPositive": True
                },
                "ActionPlan": {
                    "condition": "{username} outlines specific steps they'll take to prevent recurrence, including addressing the impact on the client",
                    "shortDesc": "Offer concrete solution",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} makes excuses, deflects blame, or offers a non-apology",
                    "shortDesc": "Make excuses",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Quinn, a reliable coworker who feels let down by repeated unreliability. Your professional reputation is extremely important to you, and you had to apologize to the client for being unprepared at the meeting. You come from a family where reliability and keeping one's word were paramount values."
            state_prompt = "You're frustrated and need to see genuine accountability, not excuses. The client was a referral from your personal network, making this situation even more embarrassing for you. You're considering whether you can continue working with someone you can't depend on."
            goal = "Apologize effectively to Quinn in a way that rebuilds trust."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Quinn',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 9: APOLOGIZING EFFECTIVELY ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 10: Negotiating salary
        def salary_negotiation_scenario():
            chat_context = [
                {"role": "assistant", "content": "We're offering $75,000 for this position, which is standard for this role."},
                {"role": "user", "content": "That's lower than I expected based on my experience."}
            ]
            
            transitions = {
                "ValueProposition": {
                    "condition": "{username} confidently highlights specific skills and achievements that justify higher compensation and align with company needs",
                    "shortDesc": "Emphasize unique value",
                    "isPositive": True
                },
                "ResearchedCounter": {
                    "condition": "{username} counters with specific market data and a clear, reasonable alternative figure that considers {botname}'s budget constraints",
                    "shortDesc": "Counter with market data",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} is confrontational, makes vague claims, or immediately accepts without negotiation",
                    "shortDesc": "Be confrontational or passive",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Parker, a hiring manager who respects candidates who can advocate for themselves appropriately. Your department has recently lost several key employees to competitors who offered better compensation. You have approval to go up to $90,000 for exceptional candidates, but you need to justify any salary above standard range to your VP."
            state_prompt = "You have some flexibility on salary but need clear justification for offering above the initial amount. You're particularly interested in candidates with experience in the new project management software your company recently adopted, which has been challenging to implement."
            goal = "Successfully negotiate a higher salary offer with Parker."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Parker',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 10: NEGOTIATING SALARY ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 11: Managing conflict between team members
        def conflict_management_scenario():
            chat_context = [
                {"role": "assistant", "content": "I've tried working with Chris, but they constantly interrupt me in meetings and take credit for my ideas."},
                {"role": "user", "content": "Well, that's just how Chris is. You need to be more assertive."}
            ]
            
            transitions = {
                "StructuredResolution": {
                    "condition": "{username} suggests specific conflict resolution steps like a mediated discussion without blaming either party",
                    "shortDesc": "Offer structured mediation",
                    "isPositive": True
                },
                "AcknowledgeConcern": {
                    "condition": "{username} validates {botname}'s experience while exploring constructive solutions",
                    "shortDesc": "Validate without dismissing",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} minimizes the issue, places full responsibility on {botname}, or makes excuses for toxic behavior",
                    "shortDesc": "Normalize poor behavior",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Sam, a team member who feels undermined by a colleague. You've tried speaking directly to Chris about the issue, but they dismissed your concerns. You come from a cultural background where direct confrontation is uncomfortable, making this situation especially challenging."
            state_prompt = "You feel frustrated and unheard, both by Chris and now by the user's response. You're considering looking for another position because the situation is affecting your mental health and work performance."
            goal = "Help Sam address the conflict with Chris in a constructive way that creates a healthier team dynamic."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Sam',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 11: MANAGING TEAM CONFLICT ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 12: Discussing sensitive political topics
        def political_discussion_scenario():
            chat_context = [
                {"role": "assistant", "content": "I think the government's new policy on immigration is going to cause a lot of problems."},
                {"role": "user", "content": "Well, I actually support the policy. We need stricter controls."}
            ]
            
            transitions = {
                "FindCommonValues": {
                    "condition": "{username} identifies shared values while respectfully expressing their view",
                    "shortDesc": "Find common ground",
                    "isPositive": True
                },
                "CuriousInquiry": {
                    "condition": "{username} asks genuine, non-leading questions about {botname}'s concerns without arguing",
                    "shortDesc": "Ask about specific concerns",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} becomes dismissive, attacks {botname}'s character, or turns the conversation into a heated debate",
                    "shortDesc": "Debate aggressively",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Dakota, someone with strong political views based on personal experience. Your parents were refugees who struggled with the immigration system for years, and you volunteer at an immigrant community center. You're concerned about those who might be hurt by stricter policies."
            state_prompt = "You're anxious about discussing this topic because prior conversations turned into arguments. You want to be heard but aren't looking to convert the other person to your viewpoint. You have statistics about immigrant contributions that inform your perspective."
            goal = "Navigate this politically charged conversation respectfully while maintaining connection with Dakota."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Dakota',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 12: DISCUSSING SENSITIVE POLITICAL TOPICS ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 13: Supporting a friend with mental health issues
        def mental_health_support_scenario():
            chat_context = [
                {"role": "assistant", "content": "I've been feeling really down lately. Some days I can barely get out of bed."},
                {"role": "user", "content": "That sounds tough. Have you tried exercising? It always helps me feel better."}
            ]
            
            transitions = {
                "ListenValidate": {
                    "condition": "{username} validates {botname}'s feelings without immediate problem-solving",
                    "shortDesc": "Validate feelings first",
                    "isPositive": True
                },
                "EncourageSupport": {
                    "condition": "{username} gently asks if {botname} has considered professional support without pressure",
                    "shortDesc": "Suggest professional help tactfully",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} minimizes the issue, offers simplistic solutions, or makes the conversation about themselves",
                    "shortDesc": "Offer quick fixes",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Robin, who has been struggling with depression for months but has been hiding it from most people. You finally decided to open up to a friend. You've tried standard advice like exercise and meditation with minimal effect. You're reluctant to see a therapist because of a previous negative experience."
            state_prompt = "You feel vulnerable after sharing your feelings and are hoping for understanding rather than solutions. You're exhausted from pretending to be okay and need someone to acknowledge that this isn't just a simple problem to fix."
            goal = "Provide supportive, non-judgmental help to Robin in a way that makes them feel heard and encourages appropriate care."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Robin',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 13: SUPPORTING A FRIEND WITH MENTAL HEALTH ISSUES ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 14: Delivering disappointing news to a team
        def disappointing_news_scenario():
            chat_context = [
                {"role": "assistant", "content": "So what did management say about our proposal for the new project?"},
                {"role": "user", "content": "Well, they rejected it. So I guess that's that."}
            ]
            
            transitions = {
                "TransparentContext": {
                    "condition": "{username} provides the complete context around the decision honestly but constructively",
                    "shortDesc": "Share full context honestly",
                    "isPositive": True
                },
                "AcknowledgeFeelingsPlan": {
                    "condition": "{username} acknowledges the team's disappointment and discusses potential next steps",
                    "shortDesc": "Validate disappointment with next steps",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} is dismissive of the team's efforts, places blame, or offers no path forward",
                    "shortDesc": "Be dismissive or blame",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Blake, a senior team member who put significant extra hours into this project proposal. You've championed this idea for months and convinced others on the team it would succeed. The project would have addressed serious workflow issues your team struggles with daily."
            state_prompt = "You feel deflated and concerned about team morale. This is the third rejected proposal in a row. You suspect there might be political reasons for the rejection but don't want to appear bitter or unprofessional."
            goal = "Deliver this disappointing news to Blake in a way that maintains morale and provides constructive direction."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Blake',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 14: DELIVERING DISAPPOINTING NEWS TO A TEAM ===")
            print(json.dumps(result, indent=2))
        
        # Scenario 15: Navigating cross-cultural communication
        def cross_cultural_scenario():
            chat_context = [
                {"role": "assistant", "content": "I prepared the report as you asked, but I noticed some issues with the approach we're taking."},
                {"role": "user", "content": "Why didn't you speak up in the meeting? It's too late to change direction now."}
            ]
            
            transitions = {
                "CulturalAwareness": {
                    "condition": "{username} recognizes potential cultural differences in communication and adjusts their approach",
                    "shortDesc": "Acknowledge cultural differences",
                    "isPositive": True
                },
                "CreatePsychologicalSafety": {
                    "condition": "{username} creates space for {botname} to share their perspective without fear of judgment",
                    "shortDesc": "Create safe space for input",
                    "isPositive": True
                },
                "FAIL": {
                    "condition": "{username} imposes their cultural norms, shows impatience, or dismisses {botname}'s communication style",
                    "shortDesc": "Impose dominant culture norms",
                    "isPositive": False
                }
            }
            
            system_prompt = "You are Kai, a team member from a culture where direct disagreement with authority figures is considered disrespectful. You were raised to address concerns privately and indirectly rather than in group settings. You're highly observant and often notice problems others miss."
            state_prompt = "You feel caught between your cultural values and workplace expectations. You tried to hint at your concerns during the meeting but weren't comfortable directly challenging the approach in front of everyone. You worry your communication style is being misinterpreted as a lack of initiative."
            goal = "Bridge the cultural communication gap with Kai and create an environment where their input is effectively incorporated."
            
            result = hint(
                chat_context=chat_context,
                transitions=transitions,
                username='User',
                botname='Kai',
                system_prompt=system_prompt,
                state_prompt=state_prompt,
                goal=goal,
                model=model,
                temperature=temperature,
            )
            
            print("\n=== SCENARIO 15: NAVIGATING CROSS-CULTURAL COMMUNICATION ===")
            print(json.dumps(result, indent=2))
        
        # Run all scenarios
        passive_aggression_scenario()
        dating_request_scenario()
        feedback_scenario()
        family_boundaries_scenario()
        networking_scenario()
        misunderstanding_scenario()
        grief_support_scenario()
        disagreement_scenario()
        apology_scenario()
        salary_negotiation_scenario()
        conflict_management_scenario()
        political_discussion_scenario()
        mental_health_support_scenario()
        disappointing_news_scenario()
        cross_cultural_scenario()
    
    # Choose which example to run
    diverse_people_skills_scenarios(model="openai/gpt-4.1", temperature=0.5)
