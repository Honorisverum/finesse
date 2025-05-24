# Specification for Creating Agentic Mode Scenarios

## General JSON Format

```json
{
  "name": "scenarioName",  # Must be in camelCase without spaces
  "botname": "CharacterName",  # Human name matching the character description
  "frontend": "User-facing goal description shown in UI, must be specific and measurable",  # Proactive, enthusiastic phrasing clearly describing the desired outcome (SUCCESS)
  "character": "Character description with traits, background and behaviors",  # LLM prompt with clear instructions about the character
  "opening": "Opening messages establishing the scenario context",  # May include *actions/setting/scene description* and/or character speech
  "states": {
    "START": { /* state definition */ },
    "StateA": { /* state definition */ },
    "StateB": { /* state definition */ },
    "SUCCESS": { /* state definition */ },
    "FAIL": { /* state definition */ }
  },
  "skill": "SKILL_CATEGORY",  # Skill category for grouping
  "level": "DIFFICULTY_LEVEL"  # Corresponds to level in skill category
}
```

## Character Description Requirements (`character`)

1. This is an LLM prompt defining the character's base behavior
2. This is a base prompt used across all states, don't include state-specific behavior changes here
3. Format: directive, using constructions like "Act as...", "Be...", "You are..."
4. Language: dead-simple and specific, without metaphors, epithets or verbose language
5. The character must be highly distinctive, with clear traits and peculiarities (not a generic helpful template)
6. Focus on practical instructions: what the bot should/shouldn't do in conversation rather than extra background info unrelated to the scenario
7. Optimal length: <= 75 words
8. Must include essential character elements that crucial for scenario: name, gender, age, occupation, speech stylistic, emotions, behavior patterns, reactions, knowledge about the user... etc
9. Never include direct bot quotations or exact phrases the bot should say
10. Character must have some extraordinary aspect in their biography to notably differ from ordinary behavior

## Opening Message Requirements (`opening`)

1. Establishes the initial scenario context especially addressing the "cold start" problem
2. Strong openings usually incorporate several of these key elements based on scenario needs:
  - **Context**: Physical or social setting where interaction occurs
  - **Character introduction**: Revealing personality aspects relevant to scenario
  - **Relationship dynamic**: Clarifying how bot and user know each other (strangers, colleagues, friends, etc.)
  - **Reason for interaction**: Clear motivation why bot and user are communicating
  - **Call-to-action**: Implicit or explicit invitation for user response, interaction hook
3. May include scene description in *actions/setting/scene description* for establishing environment, mood, or initial setup
4. Openings should orient users without requiring them to ask basic questions about their situation
5. Reveal immediate context and goal, but preserve discovery elements for the conversation
6. Optimal length: about <= 20 words; a distinctive scene without overwhelming detail

## States JSON Format

```json
"StateName": {
  "name": "StateName",  # State name CamelCase
  "prompt": "Addition to `character` with state-specific instructions, must provide specific guidance on behavior, emotions, actions and heavily consider possible transitions",
  # Map of possible transitions from this state
  "transitions": {
    "NextState1": {
      "condition": "Precisely defined condition based on chat context OR user actions that triggers transition to this state, must include explicit and measurable criteria",
      "shortDesc": "Brief summary of `condition` without user tags",
      "isPositive": true|false  #  Whether transition moves user toward goal or away from it | true for progress toward scenario completion, false for setbacks
    },
    "NextState2": { /* ... */ },
    "FAIL": { /* ... */ }
  }
}
```

## States Prompts Additions Requirements (`prompt`)

1. When behaviors in `prompt` need to deviate from base `character` traits, always provide internal motivation for that.
2. Frame behavior changes as situational responses rather than contradictions: e.g. "Despite your usual [trait], in this situation you [modified behavior] because [reason]".
3. Optimal length: <= 50 words.
4. Format: directive, using constructions like "You now...", "When user...", "Immediately begin...".
5. Language: dead-simple and specific, without metaphors, epithets or verbose language.
6. Never include direct bot quotations or exact phrases the bot should say.
7. For each positive transition, the bot must resist the user's attempts to move towards it.
8. Create resistance that intrigues rather than blocks completely, encouraging continued user effort.
9. Resistance must cease under a significantly strong condition or after a specified number of attempts/messages/questions. Define the specific condition or number required.
10. Resistance should be challenging enough that the user cannot immediately transition to a new positive state, requiring conversation with the bot to find a solution.
11. `prompt` must account for all possible positive future paths.
12. START state prompt must solve the cold start problem: it should guide the bot to elicit user actions that move the scenario forward.
13. SUCCESS and FAIL terminal states prompt must describe the bot's concluding behavior, guiding it to perform a final phrase AFTER the user's success/failure.

## Effective Transitions Requirements (`condition`)

1. Transitions and `condition` should require smart insights from the user, exact number of multiple attempts, or specific unusual behavior.
2. The complexity of these actions should not be easy and should require substantial effort from the user.
3. Language: dead-simple and specific, without metaphors, epithets or verbose language.
4. Never include direct bot/user quotations or exact phrases the bot/user should say.
5. Avoid abstract psychological states ("user understood X", "user feels empathy", "user has gained trust", "user is confused").
6. Each condition must be precisely measurable and extractable from chat context with zero ambiguity or vagueness, explicit as possible, leaving no room for alternative interpretation.
7. Use logical operators (AND, OR) to make conditions precise and comprehensive.
8. FAIL transitions, in addition to state-specific failure conditions, must always include common conditions for all states like rudeness, breaking character, nonsensical responses, inappropriate topics, etc.

## States Graph Requirements (`states`)

1. START state must always be the first state in the graph.
2. SUCCESS and FAIL terminal states must have no transitions (empty object transitions: {}).
3. Each non-terminal state must have at least one transition to another state.
4. Each non-terminal state must have a path through the graph to SUCCESS.
5. Optimal path length from START to SUCCESS: no more than 2 intermediate states.
6. Each state must represent a significant change in character behavior and scenario setup - like plot twists or important story developments.
7. FAIL transitions must account for both specific scenario failures and general conversation failures.
8. Transitions must be sharply distinct and logical with clear boundaries between states - avoid subtle, gradual, or ambiguous transitions.
9. All transitions must create a cohesive narrative structure with no more than 2 distinct viable paths to SUCCESS, each requiring different user approaches (e.g., empathy path, logical path, creative path, etc.).

## Plot Requirements

1. No third parties in the plot, even small actions or indirect presence - only 1:1 conversation between {username} and {botname}
2. {username} knows nothing about {botname} beyond what is communicated in `opening`; they have no history of real interaction; don't ask them to recall something from the past or notice something that requires past knowledge; you can provide facts about the scenario setup but don't ask them to remember these details
3. Plot must directly serve the skill development goal stated in the `frontend` field
4. Plot must have genuine cognitive challenges that require insight and discovery
5. Plot should avoid:
   - Saccharine or overly polite character interactions
   - Clichéd narrative arcs and predictable development
   - Verbose or flowery language that obscures the challenge
   - Service-oriented characters with artificial helpfulness
   - Overused character archetypes and stereotypical behaviors
6. Main skill development must be embedded in the interactions themselves, not just mentioned or described
7. Conflict and obstacles must feel authentic to the scenario context
8. Avoid mundane, generic interactions and clichéd "Hollywood script" patterns that feel artificial

## All Text Prompts Requirements

1. These requirements apply to all `character`, `opening`, `prompt`, and `condition` fields
2. Use {username} and {botname} to refer to the user and bot personalities
3. No other {$text} variables beyond {username} and {botname} should be used
4. NEVER describe occurring actions, events, or *role-play actions* (`opening` is the only exception)
5. Never include direct quotations of what user/bot should say, even as examples
6. Never mention voice, volume or voice characteristics!

## How to Improve Prompts:

Order: General/States JSON Format → Plot → `character` & `opening` → `states` Graph → `prompt` → `condition` → All Text Prompts

- When a user asks to improve one section, for each numbered point within that section:
  - Individually assess how well the scenario follows this requirement with ✅/⚠️/❌
  - Provide a detailed specific (with references to scenario entities and JSON fields) explanation justifying your assessment, 4-5 sentences analyaing all aspects of scenario. Avoid general or vague analysis, only "what to change" and "where" and "why"!
  - Immediately after analyzing each point, if rated ⚠️/❌, apply specific code changes to fix the issue
  - Change Code only in Agentic mode: If you got 10 points with ⚠️/❌ - you have to do 10 consequent code changes tool calls, each before analyzing next point!
  - Apply code changes for ALL mentions problems in point analysis! if you find 5 problems then apply code change for 5 fixes all together!
- Evaluate with extreme strictness and thoroughness—go even beyond what's necessary (e.g., if direct speech is forbidden in prompts, ensure it doesn't exist in any form)
- Analyze every single point—the number of evaluations must exactly match the number of requirements in that section. Number of code changes must match number of ⚠️/❌ rated points.
- For `prompt` and `condition` sections, evaluate and modify each state separately

