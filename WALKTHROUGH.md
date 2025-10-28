# State Machine Walkthrough - Step by Step Guide

This guide will walk you through understanding and experimenting with the state machine implementation in Finesse.

---

## 📚 What You'll Learn

1. How state machines work in this app
2. How to read and modify state definitions
3. How to create your own scenarios
4. How to test and visualize state flows

---

## 🎯 Step 1: Understand the Basics

### What is a State Machine?

A state machine defines:
- **States**: Different stages in a conversation or process
- **Transitions**: Rules for moving from one state to another
- **Terminal States**: End points (SUCCESS or FAIL)

### Key Files

| File | Purpose |
|------|---------|
| `backend/langraph/agentic.py` | Main production state machine (barista scenario) |
| `backend/simple_state_machine_example.py` | Simple Python learning example |
| `frontend/examples/SimpleStateMachine.tsx` | Interactive React demo |

---

## 🚀 Step 2: Run the Simple Python Example

### What to do:

```bash
cd backend
python3 simple_state_machine_example.py
```

### What you'll see:

```
=== SIMPLE STATE MACHINE ===

STATE: START
  Possible transitions:
    → FriendlyChat: User says hello...
    → FAIL: User is too loud...

STATE: FriendlyChat
  Behavior: You smile and respond warmly...
  ...
```

### What to learn:

- Each state has a **prompt** (character behavior)
- Each state has **transitions** (possible next states)
- Transitions have **conditions** (what triggers them)

### 📝 Exercise:

1. Open `backend/simple_state_machine_example.py`
2. Find the `SIMPLE_STATES` dictionary (around line 16)
3. Try to trace the path from START to SUCCESS

---

## 🎨 Step 3: View the Interactive Demo

### What to do:

You need to add this component to a Next.js page to view it.

**Option A: Create a standalone demo page**

```bash
# Create a new page
mkdir -p frontend/app/demo
```

Then create `frontend/app/demo/page.tsx`:

```tsx
import SimpleStateMachine from '@/examples/SimpleStateMachine';

export default function DemoPage() {
  return <SimpleStateMachine />;
}
```

**Option B: Use it in an existing page**

Add to any page:
```tsx
import SimpleStateMachine from '@/examples/SimpleStateMachine';

// In your component:
<SimpleStateMachine />
```

### View it:

```bash
cd frontend
npm run dev
```

Then open: `http://localhost:3000/demo`

### What you'll see:

- Current state visualization
- Possible transitions
- Hints (what to do / what to avoid)
- Example conversation paths you can play through

### 📝 Exercise:

1. Click "Play this path" on the "Success Path"
2. Click "Next Step" repeatedly
3. Watch the state changes in the blue box
4. Read the conversation history at the bottom

---

## 🔍 Step 4: Study the Production Example

### What to do:

```bash
# Open the main state machine file
code backend/langraph/agentic.py
```

### What to look for:

**Lines 22-94**: The `STATES` dictionary

Example state structure:
```python
"InterestedFlirt": {
    "prompt": "You are now showing special interest...",
    "transitions": {
        "HintAtSecret": "[username] observantly notices...",
        "ArtConversation": "[username] brings up art topics...",
        "FAIL": "[username] makes crude comment..."
    }
}
```

### Key observations:

1. **More complex** than the simple example
2. **Multiple paths to success** (through HintAtSecret OR ArtConversation)
3. **Natural language conditions** instead of code logic
4. **Character personality** defined in prompts

### 📝 Exercise:

Draw the state diagram on paper:
```
START → ?
  ↓
  ? → ?
  ↓
  SUCCESS
```

Fill in the blanks by reading the transitions.

---

## ✏️ Step 5: Modify the Simple Example

### Challenge: Add a new state

**Goal**: Add a "DeepDiscussion" state between SharedInterest and SUCCESS

### What to do:

1. Open `backend/simple_state_machine_example.py`
2. Find the `SIMPLE_STATES` dictionary
3. Add a new state:

```python
"DeepDiscussion": {
    "prompt": "You passionately discuss your favorite books, losing track of time",
    "transitions": {
        "SUCCESS": "User proposes specific meeting plan with time and place",
        "SharedInterest": "User continues general book chat without commitment",
        "FAIL": "User rudely disagrees with your book opinions"
    }
}
```

4. Update "SharedInterest" to transition to "DeepDiscussion":

```python
"SharedInterest": {
    "prompt": "You become more animated, discussing your favorite books enthusiastically",
    "transitions": {
        "DeepDiscussion": "User asks deep questions about your favorite book",  # NEW!
        "FriendlyChat": "User continues pleasant conversation but doesn't advance friendship",
        "FAIL": "User dismisses your book interests or is judgmental"
    }
}
```

5. Run it again:

```bash
python3 simple_state_machine_example.py
```

### Expected outcome:

You should now see "DeepDiscussion" in the state list!

---

## 🎭 Step 6: Create Your Own Scenario

### Challenge: Design a new scenario from scratch

**Example ideas**:
- Ordering at a fancy restaurant (learn wine pairing)
- Tech support call (diagnose a problem)
- Job interview (impress the interviewer)
- Museum tour guide (learn about art)

### What to do:

1. Copy `simple_state_machine_example.py` to a new file:

```bash
cd backend
cp simple_state_machine_example.py my_custom_scenario.py
```

2. Define your scenario goal (replace line 1-14)
3. Define at least 4 states + SUCCESS + FAIL
4. Define transitions between states
5. Run it!

### Template to use:

```python
CUSTOM_SCENARIO = {
    "START": {
        "prompt": None,
        "transitions": {
            "FirstStep": "Describe what user needs to do",
            "FAIL": "Describe what would fail immediately"
        }
    },

    "FirstStep": {
        "prompt": "How the character behaves in this state",
        "transitions": {
            "SecondStep": "What advances the conversation",
            "FAIL": "What causes failure"
        }
    },

    # ... add more states

    "SUCCESS": {
        "prompt": "What success looks like"
    },

    "FAIL": {
        "prompt": "What failure looks like"
    }
}
```

---

## 🧪 Step 7: Test State Transitions

### How the app actually evaluates transitions:

The production app uses an LLM (GPT-4) to evaluate if a transition should occur:

1. **User says something**
2. **Checker module** (`backend/checker.py`) analyzes the conversation
3. **LLM decides** if conditions are met
4. **State transitions** (or stays the same)
5. **Progress updated** (0-10 scale)

### What to do:

Look at how the checker works:

```bash
code backend/checker.py
```

**Key function**: `achecker()` (line ~30)

This function:
- Takes the conversation history
- Takes the goal description
- Asks GPT-4 to evaluate progress
- Returns a score (0-10) and status

### 📝 Exercise:

Read the prompt template in `checker.py`. Can you identify:
1. What information is sent to the LLM?
2. What format does it expect back?
3. How does it determine "bad ending"?

---

## 🎯 Step 8: Understand the Full Flow

### Complete lifecycle of a state machine conversation:

```
1. User selects scenario
   ↓
2. Frontend connects to LiveKit
   ↓
3. Backend loads state machine (STATES dict from agentic.py)
   ↓
4. Conversation starts at "START" state
   ↓
5. For each user message:
   a. Agent responds based on current state's prompt
   b. Checker evaluates conversation
   c. If transition condition met → change state
   d. Frontend receives progress update via RPC
   e. UI shows progress bar & hints
   ↓
6. Conversation ends when:
   - SUCCESS state reached
   - FAIL state reached
   - User disconnects
   ↓
7. Post-analysis runs
   ↓
8. User sees detailed feedback
```

### Files involved:

| Step | File | What happens |
|------|------|-------------|
| 1-2 | `frontend/app/page.tsx` | User interaction |
| 3 | `backend/langraph/agentic.py` | Load states |
| 4-5 | `backend/livekitworker.py` | Orchestrate conversation |
| 5b | `backend/checker.py` | Evaluate progress |
| 5d | `frontend/app/page.tsx` | Receive RPC updates |
| 7 | `backend/postanalyser.py` | Generate feedback |

---

## 🏆 Step 9: Advanced Modifications

### Challenge 1: Add Hints to States

Modify `backend/langraph/agentic.py` to include hints:

```python
"InterestedFlirt": {
    "prompt": "You are now showing special interest...",
    "hints": {
        "what_to_do": "Notice something unique about her (not appearance)",
        "what_to_avoid": "Don't be too forward or crude"
    },
    "transitions": {
        # ... existing transitions
    }
}
```

### Challenge 2: Add State Entry/Exit Actions

What if you want something to happen when entering/exiting a state?

Add to your custom scenario:
```python
"SomeState": {
    "prompt": "Behavior description",
    "on_entry": "Log: User reached SomeState",
    "on_exit": "Log: User left SomeState",
    "transitions": { ... }
}
```

Then write a function to handle these:
```python
def handle_state_transition(from_state, to_state):
    from_data = STATES[from_state]
    to_data = STATES[to_state]

    if from_data.get("on_exit"):
        print(from_data["on_exit"])

    if to_data.get("on_entry"):
        print(to_data["on_entry"])
```

### Challenge 3: Visualize Your State Machine

The app can generate Mermaid diagrams! Look at:

```bash
code backend/strategies/agentic/agentic.py
```

Function `build_state_diagram()` (around line 50) creates visual diagrams.

Try running it for your custom scenario!

---

## 🐛 Step 10: Debugging State Machines

### Common issues:

**1. State never transitions**
- Check: Are transition conditions too strict?
- Fix: Make conditions more general or add fallback transitions

**2. Always goes to FAIL**
- Check: Is FAIL condition too broad?
- Fix: Make FAIL more specific, success conditions more achievable

**3. Circular loops**
- Check: Can user get stuck between states?
- Fix: Add escape paths or time-based transitions

### Debugging tools:

**Print state changes**:
```python
def debug_transition(from_state, to_state, reason):
    print(f"🔄 {from_state} → {to_state}")
    print(f"   Reason: {reason}")
```

**Track conversation history**:
```python
conversation_log = []

def log_turn(state, user_input, agent_response):
    conversation_log.append({
        "state": state,
        "user": user_input,
        "agent": agent_response
    })
```

---

## 📊 Next Steps

### Beginner Level:
- ✅ Run both example files
- ✅ Modify simple example (add 1 state)
- ✅ Draw state diagram on paper

### Intermediate Level:
- ⬜ Create complete custom scenario (5+ states)
- ⬜ Add hints to all states
- ⬜ Test different conversation paths

### Advanced Level:
- ⬜ Integrate with actual LLM for evaluation
- ⬜ Build React component for your scenario
- ⬜ Add branching paths with probabilities
- ⬜ Implement state machine validator

---

## 💡 Key Concepts Recap

| Concept | Explanation |
|---------|-------------|
| **State** | A stage in the conversation with specific behavior |
| **Transition** | Moving from one state to another |
| **Condition** | What must happen for a transition to occur |
| **Prompt** | Instructions for how character behaves in a state |
| **Terminal State** | End state (SUCCESS or FAIL) |
| **LLM Evaluation** | Using AI to determine if conditions are met |
| **Progress Tracking** | Numerical score (0-10) of how close to goal |

---

## 🆘 Getting Help

### Questions to ask yourself:

1. **What state am I in?** → Look at current state
2. **Where can I go?** → Look at transitions
3. **How do I get there?** → Read condition descriptions
4. **Why did I fail?** → Check FAIL conditions
5. **What's the shortest path to SUCCESS?** → Trace transitions

### Resources:

- `backend/langraph/agentic.py` - Production example
- `backend/simple_state_machine_example.py` - Learning example
- `frontend/examples/SimpleStateMachine.tsx` - Interactive demo
- `backend/checker.py` - How evaluation works

---

## 🎉 You're Ready!

You now understand:
- ✅ State machine structure
- ✅ How transitions work
- ✅ How to modify scenarios
- ✅ How to create new ones
- ✅ How the app evaluates progress

Start experimenting and build your own scenarios!
