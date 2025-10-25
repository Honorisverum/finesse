---
date: 2025-10-25T18:45:00+0000
researcher: Claude
git_commit: 65929f9b9c61dfe4712bfae5ba02ed67dbbdf47c
branch: andrey-local-branch
repository: finesse
topic: "State Machine and Transition System Deep Dive"
tags: [research, state-machine, mdagaw, transitions, graph-based, consulting-case-interview]
status: complete
last_updated: 2025-10-25
last_updated_by: Claude
---

# Research: State Machine and Transition System Deep Dive

**Date**: 2025-10-25T18:45:00+0000
**Researcher**: Claude
**Git Commit**: 65929f9b9c61dfe4712bfae5ba02ed67dbbdf47c
**Branch**: andrey-local-branch
**Repository**: finesse

## Research Question

How does the existing MDAGAW state machine and transition system work? This is the system that will be adapted for the consulting case interview application.

## Summary

The MDAGAW (Multi-DAG Agentic Weakener) strategy implements a **sophisticated graph-based state machine** that is superior to the linear part-based approach suggested in the original spec. Key advantages include:

1. **Multi-state activation** via `visited_states` list instead of single `current_state`
2. **Parallel branching** allowing simultaneous progress across multiple conversation dimensions
3. **Fork transitions** for mutually exclusive decision points
4. **LLM-based transition detection** that understands semantic meaning, not just keywords
5. **Accumulative prompt assembly** where all active states contribute to bot behavior
6. **Flexible state organization** with branches representing different conversation paths

This system is ideal for case interviews because it can track progress across multiple analytical dimensions (framework, data analysis, recommendations) simultaneously while maintaining conversation flow.

## How the State Machine Works

### 1. State Organization: Branches and Terminal States

**Location**: [backend/strategies/mdagaw/mdagaw.py](../../../backend/strategies/mdagaw/mdagaw.py)

States are organized into **named branches** within the `states` object, plus global **terminal states** in `tstates`:

```json
{
  "states": {
    "EmpathyBranch": {
      "NoticeWorkStress": {...},
      "BuildTrustThroughEmpathy": {...}
    },
    "IntellectualBranch": {
      "EngageOnPsychology": {...},
      "DeepenPsychologyTalk": {...}
    }
  },
  "tstates": {
    "SUCCESS": {...},
    "FAIL": {...}
  }
}
```

**Why this matters for case interviews:**
- Different branches can represent: framework development, data analysis, business intuition, recommendation quality
- Allows tracking progress across multiple evaluation dimensions simultaneously
- Terminal states define clear success/failure criteria

### 2. The `visited_states` List: Multi-State Activation

**Location**: [backend/strategies/mdagaw/mdagaw.py:519-523](../../../backend/strategies/mdagaw/mdagaw.py#L519-L523)

Instead of tracking a single `current_state`, the system maintains a **list of all visited states**:

```python
def start(skill, level, username):
    scenario = get_scenario_by_skill_level(SCENARIOS, skill, level)
    scenario["visited_states"] = ["START"]  # Initialize
    messages = [{"role": "assistant", "content": scenario['opening']}]
    return scenario, messages
```

**As conversation progresses** ([backend/strategies/mdagaw/mdagaw.py:669-671](../../../backend/strategies/mdagaw/mdagaw.py#L669-L671)):

```python
# When a transition triggers
if target_state not in scenario["visited_states"]:
    scenario["visited_states"].append(target_state)
```

**Example evolution:**
- Start: `["START"]`
- After first transition: `["START", "DefineFramework"]`
- After parallel branches activate: `["START", "DefineFramework", "RequestData", "ShowBusinessIntuition"]`

**Why this is better than single state:**
- Tracks progress across multiple analytical dimensions
- Enables accumulative prompt updates (all states contribute)
- Allows parallel evaluation of different skills
- Natural fit for case interviews where candidates juggle multiple concerns

### 3. Transition Collection from Multiple Active States

**Location**: [backend/strategies/mdagaw/mdagaw.py:557-620](../../../backend/strategies/mdagaw/mdagaw.py#L557-L620)

Every turn, the system collects potential transitions from **three sources**:

#### Source 1: Initial State Activations

States with a `condition` field but no incoming transitions:

```json
"DefineFramework": {
  "condition": "{username} proposes a structured approach OR asks what factors to consider",
  "addprompt": "Acknowledge framework quality when {username} structures analysis logically."
}
```

These can activate directly from START when their condition is met.

#### Source 2: Transitions from Active States

For each state in `visited_states`, collect its outgoing transitions:

```python
for state_name in active_states:
    if "transitions" in state_data:
        for target, transition_data in state_data["transitions"].items():
            if not transition_data.get("isBlocked"):
                all_transitions[f"{state_name}:{target}"] = transition_data
```

#### Source 3: Global Terminal States

```python
if "tstates" in scenario:
    for terminal_state in ["SUCCESS", "FAIL"]:
        if terminal_state not in visited_states:
            all_transitions[f"GLOBAL:{terminal_state}"] = terminal_data
```

**Case interview application:**
- Initial states = recognizing different analytical approaches
- Active state transitions = progressing deeper in each dimension
- Terminal SUCCESS = meets all case interview criteria
- Terminal FAIL = critical errors or time violations

### 4. LLM-Based Transition Detection

**Location**: [backend/old/transition.py:60-88](../../../backend/old/transition.py#L60-88)

The system uses an **LLM to semantically evaluate** if transitions should occur:

```python
def transition(chat_context, system_prompt, state_prompt, transitions, username, botname):
    task = TRANSITION_PROMPT.format(
        system_prompt=system_prompt,
        state_prompt=state_prompt,
        transitions=format_transitions(transitions, username, botname),
        username=username,
        botname=botname,
        json_instructions=JSON_INSTRUCTIONS
    )

    return litellmapi.run(
        model="openai/gpt-4.1",
        messages=[{"role": "system", "content": task}] + chat_context,
        json_mode=True
    )['json']
```

**Returns**:
```json
{
  "is_transition": true,
  "to_state": "DefineFramework",
  "explanation": "User proposed SWOT framework for market analysis"
}
```

**Transition Prompt Template** ([backend/old/transition.py:7-27](../../../backend/old/transition.py#L7-L27)):

```
{system_prompt}

{state_prompt}

For your next response, determine if {username}'s most recent message triggers
any of the available state transitions.

IMPORTANT INSTRUCTIONS:
1. Only trigger when ALL criteria EXPLICITLY met - be conservative
2. Do not infer or assume information not present
3. Set high threshold - when in doubt, do NOT transition
4. Hypothetical or ambiguous statements DO NOT qualify
5. Consider exact wording as strict requirements

Available transitions:
{formatted_transitions}
```

**Why this is superior for case interviews:**
- Understands semantic meaning: "Let's think about the market structure" → triggers framework state
- Recognizes concepts expressed in various ways
- Conservative by design (5 strict rules prevent false positives)
- Evaluates complex multi-part conditions: "framework AND data request AND no calculation errors"

### 5. Parallel vs Fork Transitions

**Location**: [backend/strategies/mdagaw/mdagaw.py:683-692](../../../backend/strategies/mdagaw/mdagaw.py#L683-L692)

#### Parallel Transitions (type: "parallel")

Allow multiple paths to be active simultaneously:

```json
"DefineFramework": {
  "transitions": {
    "RefineFramework": {
      "condition": "{username} adds more analytical dimensions",
      "type": "parallel"
    },
    "RequestData": {
      "condition": "{username} asks for specific data points",
      "type": "parallel"
    }
  }
}
```

Both transitions remain available. User can refine framework AND request data.

#### Fork Transitions (type: "fork")

Mutually exclusive choice points:

```json
"PresentRecommendation": {
  "transitions": {
    "DataDrivenConclusion": {
      "condition": "{username} bases recommendation on analyzed data",
      "type": "fork"
    },
    "IntuitionDrivenConclusion": {
      "condition": "{username} relies primarily on gut feel",
      "type": "fork"
    }
  }
}
```

**Fork blocking logic**:
```python
if source_state["transitions"][target_state].get("type") == "fork":
    # Block all other fork transitions from this state
    for other_target in source_state["transitions"]:
        if other_target != target_state:
            source_state["transitions"][other_target]["isBlocked"] = True
```

Once user chooses data-driven approach, intuition-driven path is permanently blocked.

**Case interview application:**
- **Parallel**: Framework development + data analysis + recommendations can progress simultaneously
- **Fork**: Mutually exclusive approaches (top-down vs bottom-up, qualitative vs quantitative)

### 6. Accumulative Prompt Assembly

**Location**: [backend/strategies/mdagaw/mdagaw.py:720-748](../../../backend/strategies/mdagaw/mdagaw.py#L720-L748)

System prompt is built by **concatenating prompts from all visited states**:

```python
# Start with base character
accumulated_prompt = scenario["character"]
if "negprompt" in scenario:
    accumulated_prompt += "\n\n" + scenario["negprompt"]

# Add prompt from each visited state
for state_name in scenario["visited_states"]:
    if state_name == "START":
        continue

    # Get from terminal states or branch states
    state_prompt = None
    if state_name in ["SUCCESS", "FAIL"] and "tstates" in scenario:
        state_prompt = scenario["tstates"][state_name]["addprompt"]
    else:
        for branch_name, branch_states in scenario["states"].items():
            if state_name in branch_states:
                state_prompt = branch_states[state_name]["addprompt"]
                break

    if state_prompt:
        accumulated_prompt += "\n\n" + state_prompt

# Add roleplay guidelines
system_prompt = accumulated_prompt + "\n\n" + ROLEPLAY_SYSTEM_PROMPT_ADDITION
```

**Example for case interview:**

```
Base: "You are a McKinsey interviewer assessing a market entry case."

+ DefineFramework: "Acknowledge when candidate proposes structured frameworks."
+ RequestData: "Provide data only when specifically requested."
+ PerformCalculation: "Wait silently while candidate calculates. Provide hints if they struggle >30 seconds."
+ ShowBusinessIntuition: "Probe deeper when candidate makes insightful observations."

= Combined prompt with all behaviors active
```

**Why this works for case interviews:**
- Interviewer behavior evolves as candidate progresses
- Each analytical dimension adds new evaluation criteria
- Natural flow: start strict, become more collaborative as candidate demonstrates competence
- Can layer: framework quality + quantitative skills + business judgment

## Complete Flow: User Message → Transition → State Update → Response

### Step-by-Step Execution

#### Step 1: User Message Addition
**Location**: [backend/strategies/mdagaw/mdagaw.py:555](../../../backend/strategies/mdagaw/mdagaw.py#L555)

```python
def response(user_message, messages, scenario, username, ...):
    messages.append({"role": "user", "content": user_message})
```

User says: *"I think we should use a framework to analyze this. Let's consider market attractiveness, competitive landscape, and company capabilities."*

#### Step 2: Collect Available Transitions
**Location**: [backend/strategies/mdagaw/mdagaw.py:557-620](../../../backend/strategies/mdagaw/mdagaw.py#L557-L620)

```python
active_states = scenario["visited_states"]  # ["START"]
all_transitions = {}

# Check initial states
for branch_name, branch_states in scenario["states"].items():
    for state_name, state_data in branch_states.items():
        if "condition" in state_data:  # Initial state
            if state_name not in active_states:
                all_transitions[f"INITIAL:{state_name}"] = state_data

# Check terminal states
if "tstates" in scenario:
    for terminal_state in ["SUCCESS", "FAIL"]:
        all_transitions[f"GLOBAL:{terminal_state}"] = terminal_data
```

**Collected transitions**:
```python
{
  "INITIAL:DefineFramework": {"condition": "proposes structured approach"},
  "INITIAL:RequestData": {"condition": "asks for specific data"},
  "GLOBAL:SUCCESS": {"condition": "completes all case phases"},
  "GLOBAL:FAIL": {"condition": "makes critical error"}
}
```

#### Step 3: Build Context for Transition Checker
**Location**: [backend/strategies/mdagaw/mdagaw.py:632-646](../../../backend/strategies/mdagaw/mdagaw.py#L632-L646)

```python
character_prompt = scenario["character"]
state_prompt = ""

for active_state in scenario["visited_states"]:
    if active_state in branch_states and "addprompt" in branch_states[active_state]:
        state_prompt += "\n\n" + branch_states[active_state]["addprompt"]
```

Sends to LLM: character description + accumulated state prompts + available transitions

#### Step 4: LLM Evaluates Transitions
**Location**: [backend/old/transition.py:60-88](../../../backend/old/transition.py#L60-88)

LLM analyzes: *"User proposed framework with market attractiveness, competitive landscape, capabilities. This matches DefineFramework condition."*

Returns:
```json
{
  "is_transition": true,
  "to_state": "DefineFramework",
  "explanation": "Candidate proposed 3C-style framework for market entry analysis"
}
```

#### Step 5: Apply Transition
**Location**: [backend/strategies/mdagaw/mdagaw.py:660-692](../../../backend/strategies/mdagaw/mdagaw.py#L660-L692)

```python
if transitionjson['is_transition']:
    target_state = transitionjson['to_state']

    # Add to visited states
    if target_state not in scenario["visited_states"]:
        scenario["visited_states"].append(target_state)

    # Handle fork blocking if needed
    if transition_type == "fork":
        # Block sibling fork transitions
```

**Result**: `visited_states` = `["START", "DefineFramework"]`

#### Step 6: Accumulate Prompts
**Location**: [backend/strategies/mdagaw/mdagaw.py:720-748](../../../backend/strategies/mdagaw/mdagaw.py#L720-L748)

```python
accumulated_prompt = scenario["character"]
# + scenario["negprompt"]
# + "Acknowledge when candidate proposes structured frameworks." (from DefineFramework)
```

#### Step 7: Generate Response
**Location**: [backend/strategies/mdagaw/mdagaw.py:750-760](../../../backend/strategies/mdagaw/mdagaw.py#L750-L760)

```python
bot_response = litellmapi.run(
    messages=[{"role": "system", "content": system_prompt}] + messages,
    model=response_model,
    temperature=response_temperature
)["content"]

messages.append({"role": "assistant", "content": bot_response})
```

Bot responds: *"Good start with that framework. Market attractiveness, competitive dynamics, and our capabilities—that's a solid structure. Let's dive into market attractiveness first. What specific factors would you want to evaluate?"*

#### Step 8: Check Terminal States
**Location**: [backend/strategies/mdagaw/mdagaw.py:762-778](../../../backend/strategies/mdagaw/mdagaw.py#L762-L778)

```python
most_recent_state = scenario["visited_states"][-1]
if most_recent_state in ["SUCCESS", "FAIL"]:
    # End conversation
    return (..., gr.update(interactive=False, placeholder="Case completed."), ...)
else:
    # Continue conversation
    return (..., gr.update(interactive=True), ...)
```

If not terminal, conversation continues.

## Scenario JSON Schema for MDAGAW

### Complete Structure

```json
{
  "name": "marketEntryCaseInterview",
  "botname": "Sarah",
  "goal": "Complete a market entry case interview with a solid recommendation",

  "character": "You are Sarah Chen, senior McKinsey consultant conducting a market entry case interview. Assess candidate's structured thinking, quantitative skills, and business judgment.",

  "negprompt": "Do not provide data unless specifically requested. Challenge weak assumptions. Remain skeptical until candidate demonstrates competence.",

  "opening": "*conference room with whiteboard* Welcome. Our client is a luxury automotive manufacturer considering entering the electric vehicle market in Southeast Asia. How would you approach this?",

  "states": {
    "FrameworkBranch": {
      "DefineFramework": {
        "name": "DefineFramework",
        "condition": "{username} proposes a structured analytical approach OR asks what factors to consider",
        "addprompt": "Acknowledge framework quality when {username} structures analysis logically.",
        "transitions": {
          "RefineFramework": {
            "condition": "{username} adds additional analytical dimensions OR clarifies framework components",
            "type": "parallel"
          }
        }
      },
      "RefineFramework": {
        "name": "RefineFramework",
        "addprompt": "Provide positive feedback when {username} demonstrates MECE thinking.",
        "transitions": {}
      }
    },

    "DataAnalysisBranch": {
      "RequestData": {
        "name": "RequestData",
        "condition": "{username} asks for specific quantitative data OR market information",
        "addprompt": "Provide requested data clearly. Track if {username} takes notes.",
        "transitions": {
          "PerformCalculation": {
            "condition": "{username} begins quantitative analysis OR requests time to calculate",
            "type": "parallel"
          }
        }
      },
      "PerformCalculation": {
        "name": "PerformCalculation",
        "addprompt": "Wait silently during calculations. Offer hints if struggling >30 seconds.",
        "transitions": {
          "VerifyCalculation": {
            "condition": "{username} presents calculation result OR shows their work",
            "type": "parallel"
          }
        }
      }
    },

    "InsightsBranch": {
      "ShowBusinessIntuition": {
        "name": "ShowBusinessIntuition",
        "condition": "{username} makes insightful observation about market dynamics OR competitive positioning",
        "addprompt": "Probe deeper when {username} demonstrates strategic thinking.",
        "transitions": {
          "SynthesizeFindings": {
            "condition": "{username} connects multiple analytical threads OR identifies key tradeoffs",
            "type": "parallel"
          }
        }
      }
    },

    "RecommendationBranch": {
      "PresentRecommendation": {
        "name": "PresentRecommendation",
        "condition": "{username} summarizes analysis AND states recommendation",
        "addprompt": "Evaluate recommendation logic and data support.",
        "transitions": {
          "DataDrivenConclusion": {
            "condition": "{username} bases recommendation on analyzed data AND addresses risks",
            "type": "fork"
          },
          "WeakConclusion": {
            "condition": "{username} makes unsupported claims OR ignores analysis",
            "type": "fork"
          }
        }
      }
    }
  },

  "tstates": {
    "SUCCESS": {
      "name": "SUCCESS",
      "addprompt": "Provide enthusiastic positive feedback. Mention specific strengths demonstrated.",
      "condition": "{username} has reached RefineFramework AND VerifyCalculation AND SynthesizeFindings AND DataDrivenConclusion states"
    },
    "FAIL": {
      "name": "FAIL",
      "addprompt": "End interview professionally. Provide constructive feedback on gaps.",
      "condition": "{username} makes calculation error >50% off OR proposes illogical recommendation OR takes >20 minutes with minimal progress OR breaks character"
    }
  },

  "skill": "CaseInterview",
  "level": "1"
}
```

### Field Definitions

**Top-Level Fields**:
- `name`: Scenario identifier (camelCase)
- `botname`: Interviewer name
- `goal`: User-visible success condition
- `character`: Base interviewer personality and role (≤50 words)
- `negprompt`: Initial skeptical/challenging behavior (≤50 words)
- `opening`: Setting description + first message (≤50 words)
- `states`: Object containing branch-organized states
- `tstates`: Terminal SUCCESS and FAIL states
- `skill`, `level`: Categorization

**State Fields**:
- `name`: State identifier (matches object key)
- `condition`: **Only for initial states** - when to activate from START
- `addprompt`: Prompt addition when state active (≤15 words)
- `transitions`: Object mapping target states to transition definitions

**Transition Fields**:
- `condition`: Precisely defined trigger condition
- `type`: "parallel" (concurrent) or "fork" (exclusive)

**Terminal State Fields**:
- `name`: "SUCCESS" or "FAIL"
- `addprompt`: Final reaction behavior
- `condition`: Global win/loss condition

## Adapting for Case Interviews

### Mapping Concepts

| Social Skills Pattern | Case Interview Equivalent |
|----------------------|---------------------------|
| EmpathyBranch | FrameworkBranch (structured thinking) |
| IntellectualBranch | DataAnalysisBranch (quantitative skills) |
| ObservationBranch | InsightsBranch (business intuition) |
| BuildTrust states | RefineFramework states (increasing sophistication) |
| Fork: Sensitive/Insensitive | Fork: DataDriven/Intuition recommendation |
| SUCCESS: Get date | SUCCESS: Complete case with strong recommendation |
| FAIL: Offensive behavior | FAIL: Critical errors or time violations |

### Key Advantages for Case Interviews

1. **Parallel Skill Evaluation**: Track framework quality, quantitative accuracy, and business judgment simultaneously

2. **Progressive Difficulty**: `visited_states` enables interviewer behavior to evolve:
   - START: Skeptical, minimal guidance
   - DefineFramework: Acknowledge structure
   - PerformCalculation: Provide hints when needed
   - SynthesizeFindings: Collaborative problem-solving

3. **Natural Branching**: Different candidates take different paths:
   - Some lead with framework → then request data
   - Others request data first → then structure
   - Both valid, both tracked

4. **Clear Success Criteria**: Terminal SUCCESS requires visiting final states in multiple branches:
   ```
   "condition": "reached RefineFramework AND VerifyCalculation AND DataDrivenConclusion"
   ```

5. **Semantic Transition Detection**: LLM understands various phrasings:
   - "Let's use Porter's Five Forces" → DefineFramework
   - "I need market size data" → RequestData
   - "This suggests limited competitive advantage" → ShowBusinessIntuition

6. **Fork Decisions Matter**: Once candidate chooses approach (top-down vs bottom-up), path is set—mirrors real case dynamics

## Code References

**Core State Machine**:
- [backend/strategies/mdagaw/mdagaw.py:550-793](../../../backend/strategies/mdagaw/mdagaw.py#L550-L793) - Complete response cycle
- [backend/strategies/mdagaw/mdagaw.py:519-547](../../../backend/strategies/mdagaw/mdagaw.py#L519-L547) - Scenario initialization
- [backend/strategies/mdagaw/mdagaw.py:720-748](../../../backend/strategies/mdagaw/mdagaw.py#L720-L748) - Prompt accumulation

**Transition System**:
- [backend/old/transition.py:7-27](../../../backend/old/transition.py#L7-L27) - Transition prompt template
- [backend/old/transition.py:60-88](../../../backend/old/transition.py#L60-88) - LLM-based evaluation
- [backend/old/transition.py:42-57](../../../backend/old/transition.py#L42-L57) - Transition formatting

**Example Scenarios**:
- [backend/strategies/mdagaw/cafeBarista.json](../../../backend/strategies/mdagaw/cafeBarista.json) - Complex multi-branch example
- [backend/strategies/mdagaw/resistPassiveAggressive.json](../../../backend/strategies/mdagaw/resistPassiveAggressive.json) - Fork transitions
- [backend/strategies/mdagaw/emotionMirror.json](../../../backend/strategies/mdagaw/emotionMirror.json) - Terminal state conditions

**Documentation**:
- [backend/strategies/mdagaw/mdagaw.md](../../../backend/strategies/mdagaw/mdagaw.md) - Strategy design doc

## Related Research

- [2025-10-25-spec-implementation-analysis.md](2025-10-25-spec-implementation-analysis.md) - Specification vs implementation comparison

## Recommendations for Case Interview Implementation

1. **Adopt MDAGAW strategy** - Superior to linear parts for tracking multi-dimensional progress

2. **Define 3-4 branches** for typical case:
   - FrameworkBranch: Structured thinking quality
   - DataAnalysisBranch: Quantitative skills
   - InsightsBranch: Business judgment
   - RecommendationBranch: Synthesis and communication

3. **Use parallel transitions** for most progressions - candidate develops multiple skills simultaneously

4. **Reserve fork transitions** for critical decision points:
   - Top-down vs bottom-up market sizing
   - Data-driven vs intuition-driven recommendation
   - Quantitative vs qualitative approach

5. **Leverage accumulative prompts** to evolve interviewer behavior:
   - Start: Challenging, minimal hints
   - Middle: Acknowledge good work, provide targeted guidance
   - End: Collaborative, probing for depth

6. **Define clear SUCCESS condition**:
   ```json
   "condition": "has reached terminal states in FrameworkBranch AND DataAnalysisBranch AND InsightsBranch AND made DataDrivenRecommendation"
   ```

7. **Keep transition conditions specific**:
   - Good: "proposes market sizing using top-down approach with TAM/SAM/SOM"
   - Bad: "does market sizing"

8. **Use LLM transition detection** - allows natural phrasing variations

9. **Track `visited_states` for scoring** - more states visited in each branch = stronger performance

10. **Exhibit display can be added** via RPC (infrastructure exists, just not implemented)
