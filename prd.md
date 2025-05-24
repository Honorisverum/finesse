# Finesse App Gradio Demo

I want to create a gradio dashboard for the NLP MVP of my project. It will be a chatbot with extensions and a bunch of settings options. The app is about "Learning People Skills Stress-Free via AI Gaming" immersively through chat, goals in these chats, progression, and AI guidance.

## Key Elements

### skills and scenarios

The user can choose which skill they want to develop. For each skill, there is a progression of scenarios to develop it, for example, from level 1 to level 5 in difficulty. A scenario is not only a goal corresponding to the skill but also the bot's personality, plot, all necessary prompts for the engine, and more.

Here are the current skills that we'll work with for now:
- Small Talk: Starting and maintaining casual conversations (smallTalk)
- Social IQ: Reading Emotions and non-verbal cues (socialIq)
- Persuasion: Influencing others through effective communication (persuasion)
- Dating: Navigating romantic conversations and connections (dating)
- Conflict Resolution: Resolving interpersonal disputes constructively (conflictResolution)


### engine

This is the mechanism for how the goal engine works in chat: the gameplay process, bot resistance, and stages of the process. There are 2 types:

**Pos/Neg Dynamic Additions**:
- Each goal (scenario) has its own 2 types of additions to the bot's system prompt: neg_prompt and pos_prompt
- neg_prompt: changes the bot's behavior to "resist the user's completion of the goal," making goal achievement more difficult
- pos_prompt: changes the bot's behavior to "agree to the completion of the goal and help with it," pushing the bot toward helping the user achieve the goal
- neg_prompt is written more subtly than just "under no circumstances...", rather the bot should not agree or make achieving the goal easier, BUT should intrigue the user and contribute to continuing the dialogue (the specific form depends on the type of goal itself)
- for the first 5 messages from the user, only neg_prompt is always added so they don't complete the goal right from the start
- then a variable goal_difficulty_p=0.8 is introduced as the probability of adding neg_prompt instead of pos_prompt; every goal_difficulty_nstep=5 messages from the user we subtract 0.1
- stylistics of all prompts: no graphomania, no fluff or metaphors, no "soy" storylines, only dead simple straightforward and clear English language with maximally intriguing and hardcore marketing descriptions, strong emotional involvement and play on the extreme degree of excitement from often polar emotions and states
- format of each scenario in this engine
```json
{
  "name": "unique scenario identifier, short name in English without spaces and special characters, camelCase",
  "frontend_description_for_user": "emotionally attractive and intriguing task description for the user (10-15 words), no standard soy storylines about libraries or cafes - highest degree of intrigue and marketing, uses deliberately vague wording for secrets and mysteries that need to be uncovered (never names them directly), encourages action through fun/intrigue/challenge/danger, may contain [botname] which is replaced with the bot's name, should be extremely clear and evoke a desire to start immediately",
  "bot_personality": "detailed description of the bot's personality and characteristics (50-100 words), includes name, age, profession, specific biographical facts, appearance, psychological features, key character traits, speech habits, manner of communication, interests, everything that defines their personality; if the scenario's goal is to reveal a secret, this secret should be explicitly stated here",
  "opening_setup": "initial dialogue scene (15-30 words), describes the physical setting and circumstances of first contact, sets the tone and atmosphere for the entire interaction, may include a brief description of the user's role or context of their appearance, includes the bot's first line, uses * for describing actions and emotions",
  "neg_prompt": "precise instructions on how the bot should resist the user's achievement of the goal (50-80 words), doesn't rigidly block the goal's completion but intrigues, flirts, and entices the user to continue the dialogue, preferably doesn't include specific phrases in quotes that the bot can use, clear unambiguous wording without ambiguity, explicitly indicates all specific entities that should be revealed or hidden, uses [name] as a placeholder for the user's name, describes non-verbal signs and speech patterns, describes to the bot exactly how it needs to change its behavior",
  "pos_prompt": "precise instructions on which specific user actions should make the bot yield and help them achieve the goal (50-80 words), formulations like 'if the user does X, then you do Y' without intermediate steps, preferably doesn't include specific phrases in quotes that the bot can use, clear unambiguous wording without nuances, explicitly indicates all specific entities that should be revealed, uses [name] as a placeholder for the user's name, describes non-verbal signs and speech patterns, describes to the bot exactly how it needs to change its behavior",
  "goal_for_goal_checker": "exact formulation of the goal for the completion check system (15-25 words), uses A to denote the user and B to denote the bot, describes the conditions for successful completion of the goal in extremely concrete terms",
  "skill": "name of the skill that this scenario trains, must correspond to one of the predefined skills in the system",
  "level": "difficulty level of the scenario from 1 to 5, where 1 is the simplest and 5 is the most difficult, each skill must have exactly one scenario of each level"
}
```
- all scenarios are already implemented in `posneg.json`, can be loaded using json.load, there is a list of these scenarios there.


**Agentic Graph** (Not implementing yet)
- authentic bot prompt, no constant initial additions
- we create only cool moments and cool possible states in the plot without the need to make it coherent
- we generate mermaid where vertices are bot states and graphs are possible user transitions
- some nodes finish at "SUCCESS", some at "FAIL"
- every node is an addition to prompt
- transition is json_schema possible leads to other nodes (good and bad, closer and farther from goal)

In Agentic Graph, the bot's behavior is governed by state-based nodes. After each user message, we need to determine whether the conversation has moved to a new node (state) and respond accordingly.  
However, detecting this transition reliably requires an LLM call — which introduces latency.  
The challenge: how to react instantly while still reflecting correct state transitions without breaking immersion or slowing down the interaction.
- Emotional roleplay message before response  
  A short non-verbal reaction from the bot (*roleplay message*) is sent immediately after the user's message while the next state is being computed. Creates immersion and hides LLM latency.  
  Example: *She pauses, her eyes narrowing slightly.*
- Soft transitions between nodes  
  The system prompt includes the current node and nearby possible transitions. If the user behavior matches a trigger, the bot naturally shifts tone and content mid-reply without requiring a second call.  
  Example: If the user gets vulnerable, start responding like you're in emotionalConfession.
- Transition-aware response with JSON flag  
  The model returns a JSON object with a flag indicating if a state transition occurred. If true, the app makes a second call using the new state and streams the reply from it.  
  Example: { "is_transition": true, "transition_to": "manipulativeCharm", "base_answer": "..." }

**Multi-DAG Agentic Weakerer** (Not implementing yet)

- Initially, the bot has a strong negative prompt preventing the user from reaching SUCCESS, but states progressively weaken this resistance as the user advances through states
- Each state is a prompt addition with transition condition
- Prompt additions from all states the user has visited are sequentially summed into the system prompt
- Start State: START, you always start from this, zero prompt addition
- Terminal states: SUCCESS and FAIL, both don't have incoming arrows making them always theoretically accessible to the user
- Besides Terminal States and START, there are also a collection of DAG mini-graphs, typically not very deep, that don't lead directly to SUCCESS or FAIL and do not start with START, but rather develop the narrative and progressively help the user approach the goal through accumulating prompt additions
- These mini-graphs represent separate narrative/conversational/psychological branches that the user can follow in parallel
- There are 2 types of directed arrows between states: → and ⇢
- States within these mini-graphs that don't have incoming arrows are considered initial states, and users immediately begin checker on all of them
- Each state can have at most 1 incoming arrow
- There can only be one of 3 situations:
  - A state has exactly one outgoing → arrow
  - A state has more than one outgoing → arrows. This means the user can traverse all these arrows. Even transitioning along one arrow doesn't block progression along the others.
  - A state has more than one outgoing ⇢ arrows. This is a fork state. During conversation, the user can only transition strictly along one of these arrows. When a transition occurs, the other arrows are blocked and can no longer be traversed.
- Which states are currently checking for possible transitions?
  - States not connected by arrows to any others, which always includes at least SUCCESS and FAIL
  - States that have → arrows leading to them from states you're already in
  - States that have unblocked ⇢ arrows leading to them from states you're already in
- The user can simultaneously be in multiple states at any given time, and their state collection grows as they progress through the conversation, accumulating more and more prompt additions
- State prompts should be designed to be cumulative - each sequential state within a DAG adds new emotional effects or dialogue patterns without hard canceling previous ones, gradually changing the conversation
- DAGs focus on indirect progress toward the goal through various communication dynamics (emotional connection, user conv actions, negotiation, argumentation, knowledge sharing, impression management, etc. - all sub-branches of conversation) rather than only directly addressing the objective, this gradually weakening the bot's initial negative prompt resistance to goal


### checker

---
checker(chat_context, goal) → isGoalComplete: bool | GoalProgress: int (1 to 10) | hint: str
---

This function analyzes the current chat context and provides:
- isGoalComplete: whether the goal has been completed by the user in the current chat
- GoalProgress: on a scale from 1 to 10, how close they are to completing the goal
- hint: contextual advice to help the user get closer to completing the goal

It is called after each turn from the bot, but not during the first 5 messages.
chat_context is the intermediate chat context where user messages are marked as from speaker 'A' and bot messages as from speaker 'B'.
goal is a detailed description of the goal in language understandable to the LLM using the designations 'A' and 'B'.
This function is already implemented in the file `checker.py` function `checker`.


### postanalyser

---
postanalyser(full_chat_context, goal) → completeScore: str | radarDiagram: List[int] of size 5 with values from 1 to 10 | insights: List[str] of size <=3 | feedback: List[str] of size <=3
---

This is a post-analyzer that looks at the completed chat with an accomplished goal and provides useful data and analysis:
- It is called once immediately after the successful completion of a scenario with a goal in the chat, i.e., victory.
- completeScore is the overall score for completing the goal from E-, E, E+, D-... to A-, A, A+ if everything was really good
- radarDiagram is a breakdown of the user's performance into 5 characteristics (leadership, frame, emotions, vibe, game) in the form of a radar diagram, each characteristic from 1 to 10. These characteristics are fixed and always these 5. Characteristics != skills that the user is developing. Skills are the end goal of this process, while characteristics are just the individual style of this specific user.
- insights is a set of up to 3 strings, each of which is some interesting statistic or insight about the completion. For example, you managed faster than x% of users, {bot_name} laughed at your jokes 3 times, at the beginning you were pushing on emotions which is not typical for you,... (and so on, many different types)
- feedback is a set of up to 3 strings, each of which is advice to the user on how they should have better completed this or how to improve in the future. Like insights, it's very contextual and based on the past chat.

### dpe

---
dpe(chat_context, type, goal) → plot_twist: str | options: dict
---

This is dynamic plot engine - another feature of our chats and scenarios:
- Once every 5 messages, a plot twist from the narrative narrator is announced in the chat, dramatically changing the course of the plot to make completing the chat goal more fun, i.e., the plot twist is related to it and knows about it during generation.
- This message is not from the bot or user but rather centered, i.e., it's just some event, recorded in history from the bot as an *[PLOT_TWIST] role-play* message.
- There can be many types of such messages, but for now we'll stick with one - action.
- Essentially, this is just an additional LLM call that comes up with these twists based on context, the history is recorded in the system prompt as text, and options dict is output.
- In this type, immediately after the plot twist, the user is offered a choice of 1 of 2 mini-actions, recorded in history from the user as *action*
- Each action leads to some reaction from the bot - an emotional reaction that is communicated to the user for a couple of seconds, recorded in the context from the bot as *reaction*.
- The choice must be made quickly, there is a 5-second timer; if not in time, a *fallback_reaction* is issued that distances the user from the goal - implement this as a 3rd option for simplicity.
- After this process, the chat continues.
- All of this is returned in options as a dict, i.e., {'option1': {'action1': str, 'reaction1': str}, 'option2': {'action2': str, 'reaction2': str}, 'fallback_reaction': str}
