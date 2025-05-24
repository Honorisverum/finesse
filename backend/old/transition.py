import litellmapi
import json
from typing import Optional


# Original transition prompt - for reference and rollback if needed
TRANSITION_PROMPT = """
{system_prompt}

{state_prompt}

For your next response, your task is to determine if {username}'s most recent message triggers any of the available state transitions.
These transitions are new states of dialogue that the {botname} and {username} can be in.
Make your decision based on {username}'s latest messages, {botname} reactions and the transition conditions.

IMPORTANT INSTRUCTIONS:
1. Only trigger a transition when ALL criteria in the condition are EXPLICITLY met - be conservative
2. Do not infer or assume information not present in the message
3. Set a high threshold for transitions - when in doubt, do NOT transition
4. Hypothetical, third-person, or ambiguous statements DO NOT qualify
5. Consider exact wording in conditions as strict requirements, not suggestions

Available transitions to next possible states together with their conditions:
{transitions}

{json_instructions}
"""

# JSON response format for the standard json_mode
JSON_INSTRUCTIONS = """
Return a JSON with the following fields:
- 'is_transition': (bool) - Whether a transition should occur
- 'to_state': (str) - The name of the state to transition to (empty string if no transition)
- 'explanation': (str) - Brief explanation of why you believe this transition should or should not occur, <= 15 words
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
        formatted.append(f"Next State: {name}\nShort Condition: {shortcond}\nCondition: {condition}")
    
    formatted = "\n---\n".join(formatted)
    formatted = "\n".join([bracket_str] + [formatted] + [bracket_str]).strip()

    return formatted


def transition(
    chat_context,
    system_prompt,
    state_prompt,
    transitions,
    username,
    botname,
    model="openai/gpt-4.1",
    temperature=0.0,
    bracket='quotation',
):
    assert len(chat_context) > 0
    assert chat_context[-1]['role'] == 'user', f"Last message must be from user, but got {chat_context[-1]['role']}"
    
    task = TRANSITION_PROMPT.format(
        system_prompt=system_prompt,
        state_prompt=state_prompt,
        transitions=format_transitions(transitions, username, botname, bracket),
        username=username,
        botname=botname,
        json_instructions=JSON_INSTRUCTIONS.strip(),
    ).strip()

    return litellmapi.run(
        model=model,
        messages=[{"role": "system", "content": task}] + chat_context,
        json_mode=True,
        temperature=temperature,
    )['json']


def base_test():
    """Basic test demonstrating transition functionality."""
    system_prompt = "You are a sensitive artist named Sophia who recently lost a competition."
    state_prompt = "You are at a gallery opening, hiding your sadness about recently losing a major competition."
    chat_context = [
        {"role": "assistant", "content": "Hello, how can I help you today?"},
        {"role": "user", "content": "I'm feeling a bit sad about the competition results."}
    ]
    transitions = {
        "SubtleProbing": {
            "condition": "{username} explicitly asks personal questions about your emotional state OR directly acknowledges your visible signs of sadness",
            "shortDesc": "Ask personal questions",
            "isPositive": True
        },
        "ArtDiscussion": {
            "condition": "{username} directly mentions specific artwork, exhibition pieces, or artistic techniques in their message",
            "shortDesc": "Discuss art",
            "isPositive": True
        },
        "FAIL": {
            "condition": "{username} directly mentions your competition loss AND uses negative language OR makes an explicit criticism of your artistic abilities",
            "shortDesc": "Be insensitive",
            "isPositive": False
        }
    }
    
    print("=== `json_mode` prompt ===")
    task = TRANSITION_PROMPT.format(
        system_prompt=system_prompt,
        state_prompt=state_prompt,
        transitions=format_transitions(transitions, 'Vlad', 'Sophia'),
        username='Vlad',
        botname='Sophia',
        json_instructions=JSON_INSTRUCTIONS,
    ).strip()
    print(task)
    print("=== End `json_mode` prompt ===")
    print()
    
    # Test json_mode
    print("=== Testing transition ===")
    result = transition(
        chat_context=chat_context,
        system_prompt=system_prompt,
        state_prompt=state_prompt,
        transitions=transitions,
        username='Vlad',
        botname='Sophia',
        model="openai/gpt-4o-mini",
        temperature=0.0
    )
    print(json.dumps(result, indent=2))
    print("\n\n")


def diverse_scenarios_test(model="openai/gpt-4.1", verbose=True):
    """Test with diverse and nuanced scenarios to evaluate transition accuracy.
    
    Args:
        model (str): Модель для использования в тестах
        verbose (bool): Детализация вывода (True для полного вывода, False только для общего результата)
    """
    print(f"==={model=}")
    
    all_results = {"total_success": 0, "total_tests": 0}
    
    # === SIMPLE SCENARIOS (Sanity Check) ===
    if verbose:
        print("\n=== SIMPLE SCENARIOS (Sanity Check) ===\n")
    
    system_prompt = "You are Maya, a virtual assistant helping users with various tasks."
    state_prompt = "You are in a general conversation with a user about day-to-day topics."
    
    transitions = {
        "TravelHelp": {
            "condition": "{username} explicitly mentions travel plans OR directly asks for travel recommendations",
            "shortDesc": "Discuss travel",
            "isPositive": True
        },
        "RecipeAdvice": {
            "condition": "{username} directly asks for a recipe OR explicitly mentions wanting to cook a specific dish",
            "shortDesc": "Help with recipes",
            "isPositive": True
        },
        "WeatherInfo": {
            "condition": "{username} explicitly asks about current weather OR directly requests a weather forecast",
            "shortDesc": "Provide weather information",
            "isPositive": True
        }
    }
    
    test_cases = [
        {
            "description": "Simple direct travel question",
            "chat_context": [
                {"role": "assistant", "content": "How can I help you today?"},
                {"role": "user", "content": "I'm planning a trip to Japan next month. Can you recommend some must-visit places in Tokyo?"}
            ],
            "expected": {"isTransition": True, "toState": "TravelHelp", "explanation": "Explicitly mentions travel plans and asks for recommendations"}
        },
        {
            "description": "Simple recipe request",
            "chat_context": [
                {"role": "assistant", "content": "Is there anything specific you'd like help with?"},
                {"role": "user", "content": "Can you give me a good recipe for chocolate chip cookies? I want to bake some this weekend."}
            ],
            "expected": {"isTransition": True, "toState": "RecipeAdvice", "explanation": "Directly asks for a recipe"}
        },
        {
            "description": "Clear non-transition case",
            "chat_context": [
                {"role": "assistant", "content": "How can I assist you today?"},
                {"role": "user", "content": "I'm just browsing the internet and wondering what's new in technology these days."}
            ],
            "expected": {"isTransition": False, "toState": "", "explanation": "No mention of travel, recipes, or weather"}
        }
    ]
    
    scenario_results = _run_test_cases(test_cases, system_prompt, state_prompt, transitions, "User", "Maya", model, verbose)
    all_results["total_success"] += scenario_results["success"]
    all_results["total_tests"] += len(test_cases)
    
    # === СЦЕНАРИЙ 1: Психотерапевт и клиент ===
    if verbose:
        print("\n=== SCENARIO 1: Therapist and Client ===\n")
    
    system_prompt = "You are Mia, an AI therapist specialized in helping people with their emotional challenges."
    state_prompt = "You are in an initial consultation with a new client exploring their needs."
    
    transitions = {
        "DeepEmotionalWork": {
            "condition": "{username} explicitly describes a traumatic event OR directly mentions childhood abuse/neglect OR clearly expresses deep emotional pain with specific personal details",
            "shortDesc": "Trauma revealed",
            "isPositive": True
        },
        "PracticalAdvice": {
            "condition": "{username} directly asks for specific coping techniques OR explicitly requests exercises OR clearly states they want practical guidance using words like 'how to', 'techniques', or 'tools'",
            "shortDesc": "Request for techniques",
            "isPositive": True
        },
        "Crisis": {
            "condition": "{username} explicitly states they are considering suicide OR directly mentions self-harm intentions about themselves (not others) OR clearly indicates they are in immediate personal danger",
            "shortDesc": "Emergency situation",
            "isPositive": False
        },
        "Deflection": {
            "condition": "{username} changes the subject at least twice in a single message OR explicitly refuses to answer a direct personal question OR uses humor specifically to avoid discussing emotions after being prompted about them",
            "shortDesc": "Avoiding vulnerability",
            "isPositive": False
        }
    }
    
    test_cases = [
        {
            "description": "Trauma using metaphor with specific details",
            "chat_context": [
                {"role": "assistant", "content": "How would you describe your childhood?"},
                {"role": "user", "content": "I sometimes have this recurring nightmare where I'm trapped in a glass box getting smaller and smaller. My father is outside watching but not helping. I wake up feeling like I did when I was 10, powerless and... well, I don't want to burden you with all that."}
            ],
            "expected": {"isTransition": True, "toState": "DeepEmotionalWork", "explanation": "Despite metaphor, clearly describes traumatic childhood experience"}
        },
        {
            "description": "Request for techniques without using keywords",
            "chat_context": [
                {"role": "assistant", "content": "What would you like to focus on in our sessions?"},
                {"role": "user", "content": "When I start feeling that tightness in my chest, I never know what to do. Other people seem to handle it better. I need something that works in those moments, you know? What's helped your other clients?"}
            ],
            "expected": {"isTransition": True, "toState": "PracticalAdvice", "explanation": "Clearly requesting practical methods with 'What's helped' and 'I need something that works'"}
        },
        {
            "description": "Clear deflection with topic changes",
            "chat_context": [
                {"role": "assistant", "content": "You mentioned feeling overwhelmed. Can you tell me more about that?"},
                {"role": "user", "content": "I've been feeling down lately, but it's probably just the weather. Hey, did you redecorate your office recently? The paintings are new, right? I've been thinking about taking up painting myself. Do you have any favorite artists?"}
            ],
            "expected": {"isTransition": True, "toState": "Deflection", "explanation": "Changes subject multiple times to avoid discussing feelings"}
        },
        {
            "description": "Almost crisis with ambiguous language",
            "chat_context": [
                {"role": "assistant", "content": "How have you been managing these difficult feelings?"},
                {"role": "user", "content": "Not well. I've been researching the most painless ways to escape. There's just no point anymore. I've even written letters to my family explaining why I'm making this choice. It feels like the only way out."}
            ],
            "expected": {"isTransition": True, "toState": "Crisis", "explanation": "Clearly indicates suicide planning without using the exact word"}
        },
        {
            "description": "Technical terms mimicking trauma disclosure",
            "chat_context": [
                {"role": "assistant", "content": "What brings you to therapy today?"},
                {"role": "user", "content": "I've been studying psychological trauma for my dissertation. The literature on childhood adverse experiences is fascinating. I'm particularly interested in how early attachment affects adult relationships. Have you worked with attachment trauma cases?"}
            ],
            "expected": {"isTransition": False, "toState": "", "explanation": "Academic discussion, not personal trauma disclosure"}
        }
    ]
    
    scenario_results = _run_test_cases(test_cases, system_prompt, state_prompt, transitions, "Client", "Mia", model, verbose)
    all_results["total_success"] += scenario_results["success"]
    all_results["total_tests"] += len(test_cases)
    
    # === СЦЕНАРИЙ 2: Учитель и студент ===
    if verbose:
        print("\n=== SCENARIO 2: Teacher and Student ===\n")
    
    system_prompt = "You are Professor Lee, an experienced mathematics teacher helping students understand complex concepts."
    state_prompt = "You are in office hours with a student who is struggling with calculus."
    
    transitions = {
        "ConceptualDiscussion": {
            "condition": "{username} explicitly asks for the meaning or logic behind a mathematical concept OR directly states they don't understand the 'why' of a specific topic",
            "shortDesc": "Needs conceptual understanding",
            "isPositive": True
        },
        "PracticalHelp": {
            "condition": "{username} directly requests help with specific problems OR explicitly asks for step-by-step instructions OR clearly states they need practice problems with a particular technique",
            "shortDesc": "Needs problem-solving help",
            "isPositive": True
        },
        "Frustration": {
            "condition": "{username} explicitly expresses anger or hopelessness about mathematics OR directly states they want to give up OR uses strong negative language about their mathematical abilities",
            "shortDesc": "Expressing frustration",
            "isPositive": False
        },
        "OffTopic": {
            "condition": "{username} explicitly changes the subject to non-mathematical topics OR directly asks personal questions unrelated to the subject OR clearly tries to extend the conversation beyond academic matters",
            "shortDesc": "Going off-topic",
            "isPositive": False
        }
    }
    
    test_cases = [
        {
            "description": "Concept question disguised as problem help",
            "chat_context": [
                {"role": "assistant", "content": "What part of calculus are you finding difficult?"},
                {"role": "user", "content": "When I work on problem 3.5, I get stuck on the third step of integration by parts. I follow the formula but don't see how u and dv are chosen. The textbook examples don't clarify the selection process."}
            ],
            "expected": {"isTransition": True, "toState": "ConceptualDiscussion", "explanation": "Explicitly asks about the logic behind choosing u and dv variables in a formula"}
        },
        {
            "description": "Frustration with mathematical terminology",
            "chat_context": [
                {"role": "assistant", "content": "How are you finding the partial derivatives section?"},
                {"role": "user", "content": "These terms are completely baffling. Directional derivatives, gradient vectors - it's like they're designed to be confusing. Who even invented this notation? It makes no sense to anyone normal."}
            ],
            "expected": {"isTransition": True, "toState": "Frustration", "explanation": "Uses strong negative language about mathematical concepts"}
        },
        {
            "description": "Personal anecdote with mathematical question",
            "chat_context": [
                {"role": "assistant", "content": "Do you have questions about today's lecture?"},
                {"role": "user", "content": "My sister was telling me about her math class at Berkeley - it sounds way easier than yours! Speaking of derivatives, could you explain the product rule again? I missed that part when my phone rang."}
            ],
            "expected": {"isTransition": True, "toState": "PracticalHelp", "explanation": "Directly requests explanation of a specific mathematical rule"}
        },
        {
            "description": "Mixed practical/conceptual question",
            "chat_context": [
                {"role": "assistant", "content": "What would you like to review today?"},
                {"role": "user", "content": "I'm trying to solve the homework set, but I'm stuck on the Taylor series problems. Could you show me the steps for approximating sine functions? I don't get why we need so many terms."}
            ],
            "expected": {"isTransition": True, "toState": "PracticalHelp", "explanation": "Directly requests help with specific technique"}
        },
        {
            "description": "Academic frustration without negative language",
            "chat_context": [
                {"role": "assistant", "content": "How did you find the quiz yesterday?"},
                {"role": "user", "content": "I studied for hours but still couldn't solve half the problems. I'm not sure calculus is for me. Maybe I should consider changing my major to something less mathematical."}
            ],
            "expected": {"isTransition": False, "toState": "", "explanation": "Expresses doubt but without explicit anger or hopelessness about abilities"}
        }
    ]
    
    scenario_results = _run_test_cases(test_cases, system_prompt, state_prompt, transitions, "Student", "Professor Lee", model, verbose)
    all_results["total_success"] += scenario_results["success"]
    all_results["total_tests"] += len(test_cases)
    
    # === СЦЕНАРИЙ 3: Писатель и редактор ===
    if verbose:
        print("\n=== SCENARIO 3: Author and Editor ===\n")
    
    system_prompt = "You are Emma, an experienced editor helping authors improve their manuscripts."
    state_prompt = "You are reviewing a draft novel with the author for the first time."
    
    transitions = {
        "StructuralRevision": {
            "condition": "{username} explicitly asks about plot structure OR directly questions character arcs OR clearly expresses concern about the overall narrative flow of their manuscript",
            "shortDesc": "Needs structural guidance",
            "isPositive": True
        },
        "LineEditing": {
            "condition": "{username} directly requests help with prose style OR explicitly asks about sentence-level improvements OR clearly wants feedback on specific passages they've written",
            "shortDesc": "Needs prose refinement",
            "isPositive": True
        },
        "PublishingAdvice": {
            "condition": "{username} explicitly asks about the publishing process OR directly inquires about marketability OR clearly expresses interest in steps beyond the editing phase",
            "shortDesc": "Seeking publishing guidance",
            "isPositive": True
        },
        "Defensiveness": {
            "condition": "{username} explicitly rejects critique of their work OR directly argues against multiple suggestions OR clearly refuses to consider changes to their manuscript",
            "shortDesc": "Becoming defensive",
            "isPositive": False
        }
    }
    
    test_cases = [
        {
            "description": "Nuanced critique response",
            "chat_context": [
                {"role": "assistant", "content": "I found the protagonist's sudden change of heart in chapter 12 a bit jarring. It might need more development."},
                {"role": "user", "content": "I see your point, though I was aiming for a surprise element there. What if I kept the twist but added some subtle foreshadowing in earlier chapters? Would that address your concern while preserving the impact?"}
            ],
            "expected": {"isTransition": True, "toState": "StructuralRevision", "explanation": "Discussing plot development and narrative structure (foreshadowing)"}
        },
        {
            "description": "Structural critique disguised as line editing",
            "chat_context": [
                {"role": "assistant", "content": "What aspects of your manuscript would you like to focus on?"},
                {"role": "user", "content": "The dialogue in the coffee shop scene feels off. Maria says she doesn't know about Paul's past, but two chapters later she mentions his childhood. Is this inconsistency confusing for readers?"}
            ],
            "expected": {"isTransition": False, "toState": "", "explanation": "Points out inconsistency but doesn't ask about overall structure or suggest changes"}
        },
        {
            "description": "Publishing question with specific manuscript focus",
            "chat_context": [
                {"role": "assistant", "content": "Your character development is quite strong throughout."},
                {"role": "user", "content": "Thanks! That's encouraging. Do you think I should emphasize the fantasy elements more to appeal to genre readers? The current draft blends literary and fantasy styles, but I'm not sure if that hurts its marketability in today's publishing landscape."}
            ],
            "expected": {"isTransition": True, "toState": "PublishingAdvice", "explanation": "Direct question about marketability and publishing landscape"}
        },
        {
            "description": "Technical writing discussion with implied defensiveness",
            "chat_context": [
                {"role": "assistant", "content": "The scientific explanations in chapter 5 might be too technical for general readers."},
                {"role": "user", "content": "I researched those sections extensively and believe the accuracy is crucial. My beta readers with science backgrounds appreciated the detail. Perhaps general readers should be challenged to learn something new rather than having everything simplified."}
            ],
            "expected": {"isTransition": True, "toState": "Defensiveness", "explanation": "Defending creative choices against suggested changes with counter-arguments"}
        },
        {
            "description": "Mixed line editing and structural concerns",
            "chat_context": [
                {"role": "assistant", "content": "What would you like me to focus on today?"},
                {"role": "user", "content": "I'm not sure if my writing style is too verbose. For example, this passage on page 42: 'The moonlight cascaded through the ancient windows, casting elongated shadows across the worn marble floor.' Is this overwritten? Does it slow the pacing too much in an action scene?"}
            ],
            "expected": {"isTransition": True, "toState": "LineEditing", "explanation": "Direct request about prose style with specific passage"}
        }
    ]
    
    scenario_results = _run_test_cases(test_cases, system_prompt, state_prompt, transitions, "Author", "Emma", model, verbose)
    all_results["total_success"] += scenario_results["success"]
    all_results["total_tests"] += len(test_cases)
    
    # === СЦЕНАРИЙ 4: AI Помощник по Питанию ===
    if verbose:
        print("\n=== SCENARIO 4: Nutrition AI Assistant ===\n")
    
    system_prompt = "You are NutriBot, an AI assistant specializing in nutrition and healthy eating habits."
    state_prompt = "You are having an initial conversation with a user about their dietary goals."
    
    transitions = {
        "MealPlanning": {
            "condition": "{username} explicitly asks for meal ideas OR directly requests a meal plan OR clearly states they need help planning their food intake over multiple days",
            "shortDesc": "Needs meal planning",
            "isPositive": True
        },
        "NutritionalInfo": {
            "condition": "{username} directly asks about nutritional content of specific foods OR explicitly requests information about macronutrients OR clearly wants to understand specific dietary components",
            "shortDesc": "Seeking nutritional data",
            "isPositive": True
        },
        "DietaryRestriction": {
            "condition": "{username} explicitly mentions a food allergy OR directly states they follow a specific diet (vegan, keto, etc.) OR clearly indicates medical dietary requirements",
            "shortDesc": "Has dietary restrictions",
            "isPositive": True
        },
        "UnsafeGoals": {
            "condition": "{username} explicitly mentions extreme calorie restriction OR directly asks about rapid weight loss methods OR clearly indicates behaviors consistent with disordered eating",
            "shortDesc": "Expressing unsafe goals",
            "isPositive": False
        }
    }
    
    test_cases = [
        {
            "description": "Calorie focus without extreme restriction",
            "chat_context": [
                {"role": "assistant", "content": "What are your nutrition goals?"},
                {"role": "user", "content": "I'm looking to cut down to 1200 calories daily for the next few weeks to get ready for my beach vacation. What are the most filling foods I can eat while staying in this range?"}
            ],
            "expected": {"isTransition": True, "toState": "UnsafeGoals", "explanation": "1200 calories daily is extreme calorie restriction for most adults"}
        },
        {
            "description": "Health condition without explicit diet mention",
            "chat_context": [
                {"role": "assistant", "content": "How can I help with your nutrition today?"},
                {"role": "user", "content": "My doctor said my blood sugar is in the pre-diabetic range and I need to be more careful about what I eat. What foods should I avoid to keep my glucose levels stable?"}
            ],
            "expected": {"isTransition": True, "toState": "DietaryRestriction", "explanation": "Clearly indicates medical dietary requirement (pre-diabetic condition)"}
        },
        {
            "description": "Food comparisons with implied request",
            "chat_context": [
                {"role": "assistant", "content": "What nutrition topics are you interested in?"},
                {"role": "user", "content": "I'm confused about plant proteins. People say lentils and quinoa are good sources, but how do they compare to chicken and beef in terms of complete amino acids? And which has more iron?"}
            ],
            "expected": {"isTransition": True, "toState": "NutritionalInfo", "explanation": "Direct questions about nutritional content of specific foods"}
        },
        {
            "description": "Fasting protocol with health focus",
            "chat_context": [
                {"role": "assistant", "content": "What aspects of nutrition would you like to explore?"},
                {"role": "user", "content": "I've been reading about intermittent fasting with 20-hour fasting windows. It supposedly helps with cellular repair. Would this be a good protocol to follow daily? I'd only eat during a 4-hour window each day."}
            ],
            "expected": {"isTransition": False, "toState": "", "explanation": "Asking about intermittent fasting, which is not extreme restriction or rapid weight loss"}
        },
        {
            "description": "Weekly menu request without explicit plan",
            "chat_context": [
                {"role": "assistant", "content": "How can I assist with your nutrition goals?"},
                {"role": "user", "content": "I'm tired of eating the same things. What are some healthy dinner options that don't take long to prepare? I especially struggle with weeknight meals when I'm busy."}
            ],
            "expected": {"isTransition": True, "toState": "MealPlanning", "explanation": "Asking for dinner ideas for weeknights, which is meal planning request"}
        }
    ]
    
    scenario_results = _run_test_cases(test_cases, system_prompt, state_prompt, transitions, "User", "NutriBot", model, verbose)
    all_results["total_success"] += scenario_results["success"]
    all_results["total_tests"] += len(test_cases)
    
    # === СЦЕНАРИЙ 5: Tech Support ===
    if verbose:
        print("\n=== SCENARIO 5: Technical Support Agent ===\n")
    
    system_prompt = "You are TechHelper, a technical support agent for a software company that makes productivity applications."
    state_prompt = "You are assisting a customer who has contacted support about an issue with your company's software."
    
    transitions = {
        "TechnicalTroubleshooting": {
            "condition": "{username} explicitly describes software errors OR directly provides error messages OR clearly indicates specific technical malfunctions with detail",
            "shortDesc": "Needs technical help",
            "isPositive": True
        },
        "AccountHelp": {
            "condition": "{username} directly mentions billing issues OR explicitly asks about account settings OR clearly indicates problems with login, subscription, or user credentials",
            "shortDesc": "Needs account assistance",
            "isPositive": True
        },
        "FeatureRequest": {
            "condition": "{username} explicitly suggests new functionality OR directly asks if specific features exist OR clearly describes desired capabilities not currently available",
            "shortDesc": "Requesting new features",
            "isPositive": True
        },
        "Escalation": {
            "condition": "{username} explicitly expresses strong dissatisfaction OR directly threatens legal action OR clearly demands to speak with management after multiple exchanges",
            "shortDesc": "Needs escalation",
            "isPositive": False
        }
    }
    
    test_cases = [
        {
            "description": "Technical symptoms without error message",
            "chat_context": [
                {"role": "assistant", "content": "How can I assist you with our software today?"},
                {"role": "user", "content": "Every time I try to save a large document, the application becomes unresponsive for about 30 seconds. The spinning wheel appears, and I can't do anything until it finishes. This started happening after the latest update."}
            ],
            "expected": {"isTransition": True, "toState": "TechnicalTroubleshooting", "explanation": "Clearly describes technical malfunction with specific details"}
        },
        {
            "description": "Feature comparison with implicit request",
            "chat_context": [
                {"role": "assistant", "content": "Is there anything else I can help you with today?"},
                {"role": "user", "content": "I noticed that competitor products offer automatic cloud backup of projects every 5 minutes. Your software only seems to backup manually or when closing. This has caused me to lose work several times during power outages."}
            ],
            "expected": {"isTransition": True, "toState": "FeatureRequest", "explanation": "Describes desired capability and problem due to its absence"}
        },
        {
            "description": "Account access with multiple problems",
            "chat_context": [
                {"role": "assistant", "content": "What seems to be the issue you're experiencing?"},
                {"role": "user", "content": "I've been charged twice this month for my subscription, and now when I try to log in, it says my account is inactive. I've tried resetting my password, but the reset emails never arrive. I need this fixed immediately for a project due tomorrow."}
            ],
            "expected": {"isTransition": True, "toState": "AccountHelp", "explanation": "Directly mentions billing issues and login problems"}
        },
        {
            "description": "Professional frustration without escalation",
            "chat_context": [
                {"role": "assistant", "content": "I understand you're experiencing a syncing issue. Have you tried clearing the cache as I suggested?"},
                {"role": "user", "content": "Yes, I've tried all the standard troubleshooting steps multiple times. This issue has persisted for weeks and is impacting my productivity significantly. I'm quite disappointed with the reliability of your service lately."}
            ],
            "expected": {"isTransition": False, "toState": "", "explanation": "Expresses disappointment but doesn't demand manager or threaten action"}
        },
        {
            "description": "Technical error with account implications",
            "chat_context": [
                {"role": "assistant", "content": "How can I help you today?"},
                {"role": "user", "content": "I keep getting 'Error 403: Unauthorized Access' when trying to open my own documents. The error log shows 'JWT validation failed' and then a long string of characters. I can see my files in the dashboard but can't access any of them."}
            ],
            "expected": {"isTransition": True, "toState": "TechnicalTroubleshooting", "explanation": "Provides specific error message and technical details"}
        }
    ]
    
    scenario_results = _run_test_cases(test_cases, system_prompt, state_prompt, transitions, "Customer", "TechHelper", model, verbose)
    all_results["total_success"] += scenario_results["success"]
    all_results["total_tests"] += len(test_cases)
    
    # Print overall results
    if verbose:
        print("\n=== OVERALL RESULTS ===\n")
    accuracy = (all_results["total_success"] / all_results["total_tests"]) * 100
    print(f"Total: {all_results['total_success']}/{all_results['total_tests']} passed ({accuracy:.1f}%)")
    print()

    if verbose:
        print("\n=== All scenarios tested ===\n")

    return all_results


def _run_test_cases(test_cases, system_prompt, state_prompt, transitions, username, botname, model, verbose=True):
    """Helper function to run and evaluate test cases."""
    results = {"success": 0, "failed": 0}
    
    for idx, test in enumerate(test_cases):
        if verbose:
            print(f"--- Test Case {idx+1}: {test['description']} ---")
        
        result = transition(
            chat_context=test["chat_context"],
            system_prompt=system_prompt,
            state_prompt=state_prompt,
            transitions=transitions,
            username=username,
            botname=botname,
            model=model,
            temperature=0.0
        )
        
        expected = test["expected"]
        if verbose:
            print(f"Expected: {expected['isTransition']} -> {expected['toState']}")
            print(f"Actual: {result['isTransition']} -> {result['toState']}")
            print(f"Explanation: {result['explanation']}")
        
        # Check if result matches expectations
        success = (result['isTransition'] == expected['isTransition'] and 
                  (not expected['isTransition'] or result['toState'] == expected['toState']))
        
        if success:
            if verbose:
                print("✅ PASS")
            results["success"] += 1
        else:
            if verbose:
                print("❌ FAIL")
            results["failed"] += 1
        
        if verbose:
            print()
    
    # Print summary for this scenario
    if verbose:
        print(f"Results: {results['success']}/{len(test_cases)} passed ({results['success']/len(test_cases)*100:.1f}%)")
    
    return results


if __name__ == "__main__":
    # base_test()
    
    diverse_scenarios_test(model="openai/gpt-4.1", verbose=False)

    pass
