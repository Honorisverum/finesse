# **Multi-DAG Agentic Weakerer**

## Unstructured Description

- Initially, the bot has a strong negative prompt preventing the user from reaching SUCCESS, but states progressively weaken this resistance as the user advances through states
- Each state is a prompt addition with transition condition
- Prompt additions from all states the user has visited are sequentially summed into the system prompt
- Terminal states: SUCCESS and FAIL, both don't have incoming arrows making them always theoretically accessible to the user
- The states are organized in branches (mini-DAGs), typically not very deep, that don't lead directly to SUCCESS or FAIL, but rather develop the narrative and progressively help the user approach the goal through accumulating prompt additions
- These branches represent separate narrative/conversational/psychological... paths that the user can follow in parallel
- Initial states in each branch have their own activation conditions that are checked from the beginning
- There are 2 types of directed arrows between states: → and ⇢
- States within branches that don't have incoming arrows are considered initial states, and their conditions are checked from the start of conversation
- Each state can have at most 1 incoming arrow
- There can only be one of 3 situations:
  - A state has exactly one outgoing → arrow
  - A state has more than one outgoing → arrows. This means the user can traverse all these arrows. Even transitioning along one arrow doesn't block progression along the others.
  - A state has more than one outgoing ⇢ arrows. This is a fork state. During conversation, the user can only transition strictly along one of these arrows. When a transition occurs, the other arrows are blocked and can no longer be traversed.
- Which states are currently checking for possible transitions?
  - States not connected by arrows to any others, which always includes at least SUCCESS and FAIL
  - Initial states in each branch whose conditions are checked from the beginning
  - States that have → arrows leading to them from states you're already in
  - States that have unblocked ⇢ arrows leading to them from states you're already in
- The user can simultaneously be in multiple states at any given time, and their state collection grows as they progress through the conversation, accumulating more and more prompt additions
- State prompts should be designed to be cumulative - each sequential state within a branch adds new emotional effects or dialogue patterns without hard canceling previous ones, gradually changing the conversation
- Branches focus on indirect progress toward the goal through various communication dynamics (emotional connection, user conv actions, negotiation, argumentation, knowledge sharing, impression management, etc. - all sub-branches of conversation) rather than only directly addressing the objective, this gradually weakening the bot's initial negative prompt resistance to goal

# Specification for Creating MDAGAW Scenarios

## General JSON Format

```json
{
  "name": "scenarioName",         // Must be in camelCase without spaces
  "botname": "CharacterName",     // Human name matching the character description
  "goal": "User-facing goal description shown in UI, must be specific and measurable", // Proactive, enthusiastic phrasing clearly describing specific outcome (SUCCESS)
  "character": "Base character description: personality, traits, background, dialogue style", // LLM prompt defining the core character persona
  "negprompt": "Resistance description: specific instructions on how the bot resists the user goal", // LLM prompt defining the strong negative behavior to be weakened
  "opening": "*setting/scene description* + bot's first message establishing the scenario context",
  "states": {                     // Contains all states organized by branches (mini-DAGs)
    "BranchA": {                  // Key is the branch name
      "StateA1": { /* state definition */ },
      "StateA2": { /* state definition */ }
    },
    "BranchB": {
      "StateB1": { /* state definition */ },
      "StateB2": { /* state definition */ }
    }
    // ... other branches with their states ...
  },
  "tstates": {                    // Contains terminal states: SUCCESS and FAIL.
    "SUCCESS": {
      "name": "SUCCESS",
      "condition": "Global condition checked each turn; if true, scenario transits and ends in SUCCESS.",
      "addprompt": "Final reaction prompt describing concluding behavior after SUCCESS condition is met."
    },
    "FAIL": {
      "name": "FAIL",
      "condition": "Global condition checked each turn; if true, scenario transits and ends in FAIL.",
      "addprompt": "Final reaction prompt describing concluding behavior after FAIL condition is met."
    }
  },
  "skill": "Skill Category",      // Skill category for grouping
  "level": "Difficulty Level"     // Corresponds to level in skill category
}
```

## Character Prompt Requirements (`character`)

1.  This is an LLM prompt defining the character's *base personality*.
2.  Format: Directive, using constructions like "Act as...", "Be...", "You are...".
3.  Language: Dead-simple and specific, without metaphors, epithets or verbose language.
4.  The character must be highly distinctive, with clear traits and peculiarities relevant to the scenario goal.
5.  Include character elements relevant for creating a rich scenario with a high-stakes/exciting goal and clever interaction dynamics, e.g., name, gender, age, occupation, dialogue style, emotions, behavior patterns, etc.
6.  Exclude irrelevant-to-scenario details.
7.  Length: <= 50 words.
8.  Never include direct bot/user quotations or exact phrases.

## Character Resistance Requirements (`negprompt`)

1.  This is an LLM prompt for the bot defining the *strong resistance* preventing the user from easily reaching SUCCESS and potentially moving the user towards FAIL.
2.  This prompt defines the starting behavior that subsequent `addprompt` additions will gradually weaken.
3.  The resistance should be intriguing and, if appropriate in context, encourage the user to try further.
4.  *Crucially, describe the resistance concretely:* Instead of just "be resistant" directly specify actions and reactions like "Refuse requests related to X", "Avoid answering questions about Y", "Express skepticism when the user mentions Z", "If {username} does X, then...", "When X then ..."
5.  Language: Dead-simple and specific, without metaphors, epithets or verbose language.
6.  Length: <= 50 words.
7.  Never include direct bot/user quotations or exact phrases.

The user has the following ultimate goal in this conversation:
```
{frontend}
```
- Never directly mention this goal in your responses, but always keep it in mind.
- You should resist immediately fulfilling this goal.
- Don't outright refuse, but create meaningful resistance that requires user persistence and problem-solving.
- Maintain character authenticity while resisting - your resistance must align with your personality.
- Use emotional barriers (reluctance, hesitation, distrust) rather than logical refusals when possible.

## Opening Message Requirements (`opening`)

1.  Structure: *setting/scene description* followed by the bot's first message.
2.  Establishes the initial scenario context (who, where, why, what?) to address the "cold start" problem.
3.  Strong openings incorporate key elements based on scenario needs:
    *   **Context**: Physical or social setting.
    *   **Character introduction**: Revealing personality aspects relevant to the scenario and initial resistance.
    *   **Relationship dynamic**: Clarifying how bot and user know each other.
    *   **Reason for interaction**: Clear motivation for communication.
    *   **Call-to-action**: Implicit or explicit hook for user response.
4.  Length: <= 50 words.

## Branch Requirements

1. Each branch represents a direct or indirect development path in the dialogue that leads toward the main goal.
2. Each branch is responsible for developing a specific aspect of the skill related to the `skill` and `goal`, which would be required in real life to achieve this goal.
3. Completing all states across all branches (and the cumulative effect of all these prompts) significantly weakens or eliminates the bot's `negprompt`, helping the user complete their goal.
4. This is not solely about narrative development or pure role-play, but rather teaching users to "strategically navigate conversations" in ways applicable to real-life situations.
5. Example: For a goal of asking someone on a date, branches might include learning to establish rapport, leveraging the bot's biographical details when proposing the date, addressing the bot's reservations, engaging in meaningful emotional conversation on topics important to the bot, being appropriately persistent without overstepping boundaries, and other conversational arcs.

## `states` Requirements

1. JSON format
```json
"BranchName": {                  // Key is the branch name (narrative/thematic arc)
  "StateName": {                 // Key is the state name (CamelCase, unique within the branch)
    "name": "StateName",         // State name, matches the key
    "addprompt": "Cumulative addition to the system prompt activated when this state is reached.",
    "condition": "For initial states without incoming transitions, this defines when the state becomes active.", // Only for initial states inside branch, otherwise it is None
    "transitions": {             // Map of possible transitions *from* this state to other states inside branch
      "TargetStateName": {       // Key is the name of the target state
        "condition": "Precisely defined condition (based on chat context/actions) that triggers this transition.",
        "type": "parallel | fork" // Determines transition behavior
      }
      // ... other transitions ...
    }
  }
  // ... other states in this branch ...
}
```
2.   **Transition Types:**
    *   `type: "parallel"` (→): Allows concurrent activation of sibling transitions from the same source state over time.
    *   `type: "fork"` (⇢): Blocks sibling fork transitions from the same source state once one is activated.
    *   A state cannot mix outgoing parallel and fork transitions.
3.   **Initial States:** States within a branch that have no incoming transitions must have a `condition` field defining when they become active.
4.   **Structure Recommendation:** Aim for roughly 3 distinct branches (mini-DAGs), each around 3 states deep, with possible non-linear paths, totaling 5-6 states in each branch.

## State `addprompt` Requirements

1.  These are *cumulative additions* to the system prompt. The full prompt is `character` + `negprompt` + sum of `addprompt` from all states the user has *entered* so far.
2.  Focus on *gradually weakening* the `negprompt` resistance and introducing specific conversational changes.
3.  Frame changes contextually: Describe what changed and the new resulting behavior, considering the established context.
4.  Length: <= 15 words per `addprompt`.
5.  Language: Dead-simple, specific, direct, unambiguous English. Avoid fluff, metaphors, epithets.
6.  Format: Directive.
7.  Never include direct bot/user quotations.
8.  Terminal state (`tstates.*.addprompt`) describes the final reaction *after* the terminal state's `condition` is met.

## State `condition` Requirements

1.  These conditions trigger movement *between* states and the activation of the target state's `addprompt`.
2.  Conditions must be precisely measurable and extractable from chat context (user/bot messages) with zero ambiguity policy.
3.  Use concrete actions, described context, topics mentioned, information shared/revealed, message patterns, counts.
4.  Language: Dead-simple, specific, direct, unambiguous English. Avoid fluff, metaphors, epithets.
5.  Avoid abstract psychological states that are difficult to measure from chat context.
6.  Never include direct bot/user quotations at all, even as examples.
7.  Use logical operators (AND, OR, NOT) if need for precision.
8.  The complexity of these actions should require substantial effort or subtle intuition from the user. Never write conditions that can be fulfilled in a single step.
9.  SUCCESS and FAIL conditions (`tstates.*.condition`): Checked *globally* after each user turn. SUCCESS condition must precisely define the win criteria. FAIL condition must precisely define all failure endings (usually 3-4), including general checks (rudeness, irrelevance, breaking character), combined with scenario-specific loss conditions using OR.

## Overall Plot Requirements

1.  No third parties; focus on the 1:1 interaction between {username} and {botname}.
2.  {username} starts with no prior knowledge of {botname} beyond the `opening`.
3.  Completely avoid banal and clichéd plots such as: going to an art gallery, studying art, excessive politeness, soy-metaphorical details, banal secret past, unnaturally fast emotional attachments... - we make scenarios for young people so ONLY extremely extraordinary details and eternal plots presented brightly and marketably, with an overflow of emotions.

## All Prompts Text Requirements

1.  Applies to `character`, `negprompt`, `opening`, `states.*.addprompt`, `states.*.transitions.*.condition`, `tstates.*.addprompt`, and `tstates.*.condition` fields.
2.  Use {username} and {botname} placeholders only. No other {$variables} allowed.
3.  Language: Dead-simple, specific, direct, unambiguous English. Avoid fluff, metaphors, epithets.
4.  Format: Primarily directive.
5.  **Text-Based Interaction Only:**
    *   NEVER describe or reference physical actions, non-verbal cues, or events within prompts or conditions. The user-bot interaction is purely text-based.
    *   NEVER use role-play action notation (`*...*`).
    *   All prompts (`character`, `negprompt`, `addprompt`) and conditions (`transitions`, `tstates` conditions) must *only* influence the bot's textual output (dialogue content, style, tone, conversational strategy). They cannot imply or trigger non-textual actions.
6.  Never include direct quotations of what the user or bot should say, even as examples within prompt instructions.
7.  Never mention voice tone, volume, or characteristics. Focus on behavior, internal state (as motivation), and dialogue *content/strategy*.

## How to Improve MDAGAW Scenarios

Order: General JSON → `character` & `opening` → `negprompt` & terminal states → Plot & Branches → `states` → `condition` → `addprompt` → All Text Prompts

*   When asked to improve a section, for each numbered point within that section:
    *   Individually assess the scenario against the requirement using ✅/🟡/❌.
    *   Provide detailed, specific justification (4-5 sentences) referencing scenario elements and JSON fields. Focus on *what* to change, *where*, and *why*. Avoid vague analysis.
    *   If rated 🟡/❌, immediately propose *specific code changes* via tool call(s) to address the identified issues *before* moving to the next point. Apply all fixes for a single point together if multiple issues exist within it.
*   Evaluation must be strict and thorough.
*   Analyze every point; the number of evaluations must match the number of requirements in the section. The number of edit calls must match the number of 🟡/❌ rated points.
*   For `addprompt` and `condition` sections, evaluate and modify each relevant state/transition individually.
