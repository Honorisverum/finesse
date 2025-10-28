# How the LLM Gets Context - Complete Data Flow

This document explains **exactly** what context the LLM has and how data flows in real-time during a conversation.

---

## 🎯 The Key Insight

**The app uses TWO separate LLMs for different purposes:**

1. **Agent LLM** (GPT-4.1) - Plays the character and responds to the user
2. **Checker LLM** (GPT-4.1) - Evaluates progress after each turn

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    INITIALIZATION (Once)                         │
└─────────────────────────────────────────────────────────────────┘

Frontend selects scenario
    ↓
Scenario JSON loaded (e.g., "riskyProjectApproval")
    ↓
scenario_data contains:
  - goal: "Secure approval and resources..."
  - character: ["You are Mr. Sterling...", "You value data..."]
  - negprompt: ["Resist approval...", "Demand figures..."]
  - opening: "So, this project... Bold..."
  - botname: "Sterling"
    ↓
utils.assemble_prompt() builds AGENT SYSTEM PROMPT
    ↓
Agent LLM initialized with this prompt ✓

┌─────────────────────────────────────────────────────────────────┐
│                 REAL-TIME CONVERSATION FLOW                      │
└─────────────────────────────────────────────────────────────────┘

User speaks: "Hi Mr. Sterling, thanks for meeting..."
    ↓
┌───────────────────────────────────────────────────────────────┐
│ AGENT LLM (Character Response)                                │
│                                                               │
│ System Prompt (from scenario):                               │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Act as character with the following personality:          ││
│ │ - You are Mr. Sterling, 55, CFO, risk-averse              ││
│ │ - You value data, ROI, and predictability                 ││
│ │ - You secretly look for boldness backed by logic          ││
│ │                                                            ││
│ │ User 'Vlad' has this goal:                                ││
│ │ "Secure approval and resources..."                        ││
│ │                                                            ││
│ │ How to resist:                                            ││
│ │ - Demand specific figures and forecasts                   ││
│ │ - Ask about negative scenarios                            ││
│ │ - Start considering if user shows ROI data                ││
│ │                                                            ││
│ │ Style: Keep responses 5-15 words, use "um", "well"        ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Conversation History (growing):                              │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ [Turn 1]                                                   ││
│ │ User: "Hi Mr. Sterling, thanks for meeting..."            ││
│ │ Assistant: "Well... let's see what you have."             ││
│ │                                                            ││
│ │ [Turn 2]                                                   ││
│ │ User: "This project could increase revenue by 25%"        ││
│ │ Assistant: "Hmm, based on what data exactly?"             ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Output: Agent responds in character                          │
└───────────────────────────────────────────────────────────────┘
    ↓
Agent responds: "Hmm, based on what data exactly?"
    ↓
Response added to conversation history
    ↓
┌───────────────────────────────────────────────────────────────┐
│ CHECKER LLM (Progress Evaluation)                            │
│                                                               │
│ System Prompt:                                               │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ You assess dialogue between Vlad and Sterling             ││
│ │                                                            ││
│ │ Conversation (last 20 messages):                          ││
│ │ """                                                        ││
│ │ Vlad: Hi Mr. Sterling, thanks for meeting...              ││
│ │ Sterling: Well... let's see what you have.                ││
│ │ Vlad: This project could increase revenue by 25%          ││
│ │ Sterling: Hmm, based on what data exactly?                ││
│ │ """                                                        ││
│ │                                                            ││
│ │ Vlad's goal:                                              ││
│ │ """                                                        ││
│ │ Secure approval and additional resources...               ││
│ │ """                                                        ││
│ │                                                            ││
│ │ Check if goal achieved? Rate progress 0-10?               ││
│ │ Previous progress: 2                                      ││
│ │                                                            ││
│ │ Is bad ending triggered (impossible to continue)?         ││
│ │                                                            ││
│ │ Generate motivational CTA (2-4 words)                     ││
│ └───────────────────────────────────────────────────────────┘│
│                                                               │
│ Output JSON:                                                 │
│ {                                                            │
│   "is_goal_complete": false,                                │
│   "progress_towards_goal": 3,                               │
│   "is_bad_ending_triggered": false,                         │
│   "CTA": "Show the data!"                                   │
│ }                                                            │
└───────────────────────────────────────────────────────────────┘
    ↓
Checker result sent to Frontend via RPC
    ↓
Frontend updates UI:
  - Progress bar: 3/10
  - CTA message: "Show the data!"
  - Hint button available
    ↓
[Next turn repeats...]
```

---

## 🔍 Detailed Breakdown

### 1. What the Agent LLM Sees

**File**: [livekitworker.py:66-72](backend/livekitworker.py#L66-L72)

```python
instructions = finesse_utils.assemble_prompt(
    scenario=userdata.scenario_data,
    username=userdata.username,
    usergender=userdata.usergender,
)
```

**File**: [utils.py:94-121](backend/utils.py#L94-L121)

The assembled prompt contains:

```
# Your Role

Act as character with the following personality:

- You are Mr. Sterling, 55 years old, CFO, known for meticulous and risk-averse
- You value data, ROI, and predictability above all else
- You are skeptical of any 'revolutionary' ideas without solid justification
- You secretly pride yourself on one risky but successful decision

# Dialogue with the Vlad which has the ultimate goal in mind

You will have a conversation with Vlad with gender 'male'.

The Vlad has the following ultimate goal:
```
Secure approval and additional resources beyond initial ask for immediate launch
```

How you should resist this goal:
- Never directly mention this goal in your responses
- You should resist immediately fulfilling this goal at the beginning
- Don't outright refuse, but create meaningful resistance
- Maintain character authenticity while resisting

# How you should resist the goal and react to responses

As a character, you should react to Vlad's responses in the following way:

- Resist approval, constantly returning to questions of budget, risks, profitability
- Demand specific figures and forecasts at every step
- Ignore general words about innovation
- Start asking clarifying questions if user presents clear, measurable KPIs
- Start considering seriously if user addresses all risk concerns
- Agree ONLY if user: 1) Presented ROI data 2) Addressed risks 3) Touched on your pride

# Roleplaying Style

Keep responses concise to one short sentence (5-15 words)
Stay in role no matter what. Never break character.
Respond only with direct speech text, don't use *roleplay*

Use life-like conversation patterns:
- Use natural fillers like "um", "well", "hmm" occasionally
- Leave thoughts unfinished sometimes or trail off with "..."
- Occasionally correct yourself mid-sentence
- Vary response length based on emotional state (5-15 words)
```

**Plus** the entire conversation history (growing):
- User turn 1, Agent turn 1
- User turn 2, Agent turn 2
- ... (all previous turns)

### 2. What the Checker LLM Sees

**File**: [checker.py:93-135](backend/checker.py#L93-L135)

The checker gets a **DIFFERENT** prompt:

```
# Your Role

You act as chat context assessor where two people are talking.
Your job is to assess whether the goal has been achieved.

# Conversation

You will be given a piece of dialogue between Vlad and Sterling:
"""
Vlad: Hi Mr. Sterling, thanks for meeting with me today
Sterling: Well... let's see what you have
Vlad: This project could increase revenue by 25% in Q3
Sterling: Hmm, based on what data exactly?
"""

# Goal Assessment Task

Vlad has the following goal in the dialogue:
"""
Secure his approval and additional resources beyond your initial ask
"""

Sterling may resist and refuse to fulfill Vlad's goal, but may also agree.
Your task is to check whether Vlad's goal has already been achieved.

# Assessment Guidelines

Consider the following:
- If Sterling wants to fulfill goal but minor circumstances interfere → True
- If Sterling wants to fulfill goal but hesitates because shy → True
- If dialogue is not related to goal at all → False

Additionally, return the goal progress as a number between 0 and 10:
- 0: No discussion related to the goal has occurred
- 1-3: Initial steps taken, very indirect attempt
- 4-6: Actively working towards goal, Sterling still resistant
- 7-9: Very close. Sterling shows clear signs of agreeing
- 10: Goal explicitly and clearly achieved
- Be conservative in your assessment
- Base score on Sterling's willingness, not just Vlad's efforts

Also, determine if "bad ending" triggered where progress is now impossible:
- The moment or opportunity has been missed
- Connection has been lost (extreme hostility)
- Vlad is behaving inappropriately, offensive
- Sterling has firmly and absolutely rejected the goal
- Conversation has derailed completely with no path to return

You should generate a motivational message (CTA) when there has been significant
change in progress compared to previous progress value of 2.
- If current > previous: brief, encouraging message
- If current < previous: express it was a bad move
- Do not give hints, just motivate or report failures
- CTA must be extremely concise (2-4 words maximum)
- End with exclamation or question mark
- Address Vlad directly without using name

Respond in JSON format as {
    'is_goal_complete': (bool),
    'progress_towards_goal': (int),
    'is_bad_ending_triggered': (bool),
    'CTA': (str, <= 4 words),
}
```

---

## 🎭 Key Differences

| Aspect | Agent LLM | Checker LLM |
|--------|-----------|-------------|
| **Purpose** | Play the character | Evaluate progress |
| **System Prompt** | Character personality, how to resist goal | Assessment criteria, scoring guidelines |
| **Conversation Context** | Full history (all turns) | Last 20 messages only |
| **Knowledge of Goal** | ✅ Yes (knows user's goal to resist it) | ✅ Yes (knows goal to evaluate it) |
| **Output** | Natural dialogue response | JSON with scores |
| **When Called** | Every user turn | After every agent response |
| **Temperature** | Higher (more creative) | Lower (0.0 - more consistent) |

---

## 💡 The "State Machine" Implementation

Here's the crucial insight:

### Traditional State Machine (Your SimpleStateMachine.tsx):
```
currentState = "FriendlyChat"
if (userInput matches condition) → transition to "SharedInterest"
```

### This App's Approach:
```
NO explicit currentState variable!

Instead:
- Agent LLM has character instructions: "start asking clarifying questions IF..."
- Checker LLM evaluates: progress = 5/10
- Agent naturally changes behavior based on conversation flow
- Progress score approximates "how far through the states"
```

**The "states" exist as behavioral instructions in the negprompt:**

From the scenario file:
```json
"negprompt": [
  "Resist approval, constantly returning to questions of budget...",
  "Demand specific figures and forecasts at every step...",
  "Start asking clarifying questions IF user presents clear KPIs",  ← State transition!
  "Start considering seriously IF user addresses all risks",        ← Another transition!
  "Agree ONLY IF user: 1) ROI data 2) Risks 3) Pride"              ← SUCCESS state!
]
```

These are **implicit states** embedded as conditional instructions!

---

## 📈 Real Example: Progress Flow

Let's trace a real conversation:

### Turn 1
```
User: "Hi Mr. Sterling, I have a great project idea"
Agent: "Well... we'll see. What is it?"

Checker evaluates:
  - Last 20 messages: [User: Hi..., Sterling: Well...]
  - Goal: "Secure approval and resources"
  - Progress: 1/10 (just started, no substance)
  - CTA: "Explain it!"
```

### Turn 3
```
User: "25% revenue increase in Q3 based on market analysis"
Agent: "Hmm, what about the budget? What's the risk?"

Checker evaluates:
  - Last 20 messages: [full conversation so far]
  - Goal: "Secure approval and resources"
  - Progress: 4/10 (presenting data, but Sterling still resistant)
  - Previous progress: 1
  - CTA: "Good start!"
```

### Turn 7
```
User: "ROI is 3x in 18 months. Plan B if it fails. Like your 2005 expansion."
Agent: "That's... actually well thought out. Alright, approved. Talk to finance."

Checker evaluates:
  - Last 20 messages: [full conversation]
  - Goal: "Secure approval and resources"
  - Progress: 10/10 (Sterling explicitly agreed!)
  - is_goal_complete: true
  - CTA: "You did it!"
```

---

## 🔧 How Much Context?

### Agent LLM Context Window:

**FULL conversation history** from the start:

```python
session.history.items
```

This includes:
- Opening message
- Every user turn
- Every agent turn
- No limit (uses full GPT-4 context window)

### Checker LLM Context Window:

**Last 20 messages** only:

```python
context_window_size=20
```

From [livekitworker.py:320](backend/livekitworker.py#L320):

```python
checker_result = await finesse_checker.achecker(
    chat_context=session.history.items,
    goal=scenario_data["goal"],
    botname=scenario_data["botname"],
    username=agent.userdata.username,
    previous_progress=session._last_checker['progress_towards_goal'],
    context_window_size=20,  ← Only last 20 messages
)
```

**Why?** Checker doesn't need full history, just recent context to evaluate current progress.

---

## 🎯 Data Shared in Real-Time

### Agent → Frontend (via RPC)

1. **Voice response** (automatic via LiveKit)
2. **Emoji reactions** (via `emoji_reaction` tool)

### Checker → Frontend (via RPC)

From [livekitworker.py:324](backend/livekitworker.py#L324):

```python
await agent.make_rpc_call(
    method="checker",
    payload=json.dumps(checker_result)
)
```

Payload:
```json
{
  "is_goal_complete": false,
  "progress_towards_goal": 5,
  "previous_progress_towards_goal": 3,
  "is_bad_ending_triggered": false,
  "CTA": "Keep pushing!"
}
```

### Frontend Receives

From [frontend/app/page.tsx](frontend/app/page.tsx):

```typescript
room.registerRpcMethod('checker', async (data) => {
    const payload = JSON.parse(data.payload);
    setGoalProgress(payload);
});
```

Updates UI:
- Progress bar: 5/10
- CTA message: "Keep pushing!"
- Color changes (green if improving, red if declining)

---

## 🧩 Summary: Bridging to SimpleStateMachine.tsx

### Your Simple Example:
```typescript
currentState = "FriendlyChat"
// Explicit state tracking
// Manual transitions: setCurrentState("SharedInterest")
```

### Production App:
```
NO currentState variable!

Agent Instructions:
  "Resist approval..." ← Implicit "ResistingState"
  "Start asking clarifying questions IF..." ← Transition condition
  "Start considering seriously IF..." ← Implicit "ConsideringState"
  "Agree ONLY IF..." ← Transition to SUCCESS

Checker Score:
  0-3 → Roughly "ResistingState"
  4-6 → Roughly "ConsideringState"
  7-9 → Roughly "NearlyAgreeing"
  10 → SUCCESS
```

**The states exist in the LLM's understanding, not in code variables!**

---

## 🎓 Key Takeaways

1. **Two LLMs**: Agent (character) vs Checker (evaluator)
2. **Agent knows the goal**: To resist it authentically
3. **Checker evaluates objectively**: Based on conversation content
4. **No explicit state variable**: States are behavioral instructions
5. **Progress score approximates states**: 0-10 scale instead of discrete states
6. **Context windows differ**: Agent (full), Checker (last 20)
7. **Real-time feedback**: Checker results → Frontend every turn
8. **Natural transitions**: LLM interprets when to change behavior based on prompts

The brilliance: **The LLM becomes the state machine**, using natural language understanding instead of hardcoded if-then logic!
