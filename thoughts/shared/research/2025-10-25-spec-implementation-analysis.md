---
date: 2025-10-25T18:27:54+0000
researcher: Claude
git_commit: 65929f9b9c61dfe4712bfae5ba02ed67dbbdf47c
branch: andrey-local-branch
repository: finesse
tags: [research, codebase, specification, architecture, voice-agent, state-machine]
status: complete
last_updated: 2025-10-25
last_updated_by: Claude
---

# Research: Specification vs Implementation Analysis

**Date**: 2025-10-25T18:27:54+0000
**Researcher**: Claude
**Git Commit**: 65929f9b9c61dfe4712bfae5ba02ed67dbbdf47c
**Branch**: andrey-local-branch
**Repository**: finesse

## Research Question

How does the current codebase implement the Interactive Voice Case Interviewer specification defined in [spec.md](../../../spec.md) and [spec.json](../../../spec.json)?

## Summary

The specification describes a **linear, part-based case interview system** with exhibit display, `[PART_COMPLETE]` token-based state transitions, and dynamic `part_instructions` updates. However, the **actual implementation** is a **goal-oriented roleplay conversation trainer** that uses:

- **Graph-based state machines** with parallel branches and fork transitions instead of linear parts
- **LLM-evaluated transition conditions** instead of `[PART_COMPLETE]` token detection
- **Accumulative prompt assembly** instead of part-by-part instruction replacement
- **No exhibit display functionality** despite it being defined in the spec
- **Different scenario structure** focused on social skills training rather than case interviews

The spec appears to be a design document for a planned system that was not fully implemented. The current codebase serves a different use case (social skills practice) using alternative architectural patterns.

## Detailed Findings

### Core System Components

#### 1. Caseflow Engine / State Machine

**Specification** ([spec.md:19](../../../spec.md#L19), [spec.md:42-49](../../../spec.md#L42-L49)):
- A service that loads Case Definition files and progresses through "Parts" in defined order
- Detects `[PART_COMPLETE]` token and advances to next part
- Pushes new `part_instructions`, `ai_opening_prompt`, and `exhibit_to_display` on transitions

**Current Implementation**:

**Primary Strategy** ([backend/strategies/mdagaw/mdagaw.py:550-793](../../../backend/strategies/mdagaw/mdagaw.py#L550-L793)):
- Graph-based state machine with multiple parallel branches
- Uses `visited_states` list to track all activated states
- Accumulates prompts from all visited states rather than replacing them
- No `[PART_COMPLETE]` token detection found in codebase

**State Management** ([backend/strategies/mdagaw/mdagaw.py:519-523](../../../backend/strategies/mdagaw/mdagaw.py#L519-L523)):
```python
def start(skill, level, username):
    scenario = get_scenario_by_skill_level(SCENARIOS, skill, level)
    scenario = format_scenario(scenario, username, scenario["botname"])
    scenario["visited_states"] = ["START"]  # Track all visited states
```

**Alternative Strategies**:
- [backend/strategies/agentic/agentic.py](../../../backend/strategies/agentic/agentic.py) - Single `current_state` tracking
- [backend/strategies/posneg/posneg.py](../../../backend/strategies/posneg/posneg.py) - Positive/negative feedback based

**Legacy Implementation** (unused):
- [backend/old/transition.py](../../../backend/old/transition.py) - Old state transition logic
- [backend/old/dpe.py](../../../backend/old/dpe.py) - Legacy state machine components

#### 2. Voice Agent (STT/TTS/LLM Integration)

**Specification** ([spec.md:50-54](../../../spec.md#L50-L54)):
- Real-time, low-latency STT/TTS
- Dynamic mid-conversation system prompt updates
- Reliable `[PART_COMPLETE]` token emission

**Current Implementation** ([backend/livekitworker.py:50-424](../../../backend/livekitworker.py#L50-L424)):

**STT Service** ([backend/livekitworker.py:207-212](../../../backend/livekitworker.py#L207-L212)):
- **Service**: Deepgram STT with `nova-3-general` model
- **Language**: en-US
- **Features**: Filler words enabled

**TTS Service** ([backend/livekitworker.py:223-237](../../../backend/livekitworker.py#L223-L237)):
- **Service**: ElevenLabs TTS
- **Model**: `eleven_turbo_v2_5` (standard) or `eleven_monolingual_v1` (custom)
- **Encoding**: MP3 at 44.1kHz, 96kbps
- **Custom Implementation**: [backend/tts.py:149-261](../../../backend/tts.py#L149-L261) - Non-streaming variant with `next_text` context

**LLM Service** ([backend/livekitworker.py:213-216](../../../backend/livekitworker.py#L213-L216)):
- **Service**: OpenAI GPT-4.1
- **API Key**: Environment variable `OPENAI_API_KEY`

**Prompt Management** ([backend/livekitworker.py:58-63](../../../backend/livekitworker.py#L58-L63)):
- System prompt assembled once at initialization via [backend/utils.py:95-121](../../../backend/utils.py#L95-L121)
- Static throughout conversation (no mid-conversation replacement)
- Temporary overrides possible via `session.generate_reply(instructions=...)` for ending scenarios

**Agent Class** ([backend/livekitworker.py:50-160](../../../backend/livekitworker.py#L50-L160)):
```python
class FinesseTutor(agents.Agent):
    def __init__(self, ctx: JobContext, userdata: SessionInfo):
        instructions = finesse_utils.assemble_prompt(
            scenario=userdata.scenario_data,
            username=userdata.username,
            usergender=userdata.usergender,
        )
        super().__init__(instructions=instructions)
```

#### 3. Case Definition Loading

**Specification** ([spec.md:24-40](../../../spec.md#L24-L40)):
- Static JSON/YAML file with `parts` array
- Each part has: `part_id`, `ai_opening_prompt`, `exhibit_to_display`, `part_instructions`

**Spec Example** ([spec.json:1-42](../../../spec.json#L1-L42)):
```json
{
    "case_id": "diamondlux_v1",
    "title": "DiamondLux Millennial Expansion",
    "parts": [
      {
        "part_id": "part_1_framework_and_strategy",
        "ai_opening_prompt": "Our client today is DiamondLux...",
        "exhibit_to_display": null,
        "part_instructions": "Your objective: Get the candidate..."
      }
    ]
}
```

**Current Implementation** ([backend/utils.py:16-25](../../../backend/utils.py#L16-L25)):
```python
def load_scenarios(skills: list[str] = None):
    skills = skills or SKILLS
    all_scenarios = defaultdict(dict)
    base_path = Path(__file__).parent.parent / "scenarios"
    for skill in skills:
        file_name = f"{skill}.json"
        file_path = base_path / file_name
        with open(file_path, 'r') as f:
            all_scenarios[skill].update(json.load(f))
    return all_scenarios
```

**Actual Scenario Structure** ([scenarios/smalltalk.json:1-100](../../../scenarios/smalltalk.json#L1-L100)):
```json
{
  "elevatorPitchCEO": {
    "description": "Your mission: turn this brief...",
    "goal": "get the CEO to compliment your specific contribution...",
    "opening": "*The elevator is slowly descending...",
    "character": ["You are James Hawthorne, 58 years old..."],
    "negprompt": ["Avoid complimenting the user's work..."],
    "skill": "smalltalk",
    "botname": "James",
    "elevenlabs_voice_id": "fsYawdZmGnJKupmmEeSt"
  }
}
```

**Key Differences**:
- No `parts` array in actual scenarios
- No `part_instructions`, `ai_opening_prompt`, `exhibit_to_display` fields
- Single `opening`, `goal`, and `character` for entire conversation
- Focus on social skills (smalltalk, attraction, negotiation, etc.) not case interviews

**Available Skills** ([backend/utils.py:6-14](../../../backend/utils.py#L6-L14)):
- smalltalk
- attraction
- artofpersuasion
- negotiation
- conflictresolution
- decodingemotions
- manipulationdefense

#### 4. State Transition Mechanism

**Specification** ([spec.md:56-70](../../../spec.md#L56-L70)):
1. Voice Agent emits `[PART_COMPLETE]` when objectives met
2. Caseflow Engine detects token
3. Engine advances to next part
4. Frontend displays new exhibit
5. Voice Agent receives new `part_instructions` and speaks `ai_opening_prompt`

**Current Implementation** ([backend/strategies/mdagaw/mdagaw.py:632-709](../../../backend/strategies/mdagaw/mdagaw.py#L632-L709)):

**Transition Detection** ([backend/old/transition.py:60-88](../../../backend/old/transition.py#L60-L88)):
- Uses **LLM to evaluate** if transition conditions are met
- No token-based detection
- Sends conversation context + transition conditions to GPT-4.1
- Returns JSON: `{"is_transition": bool, "to_state": str, "explanation": str}`

**Transition Execution**:
```python
# Collect potential transitions from active states
all_transitions = {}
for branch_name, branch_states in scenario["states"].items():
    for state_name, state_data in branch_states.items():
        if "transitions" in state_data:
            for target, transition_data in state_data["transitions"].items():
                if not transition_data.get("isBlocked"):
                    all_transitions[f"{state_name}:{target}"] = transition_data

# LLM evaluates which transition should occur
transitionjson = transition.transition(
    chat_context=messages,
    system_prompt=character_prompt,
    state_prompt=state_prompt,
    transitions=transitions_to_check,
    username=username,
    botname=scenario["botname"]
)

# Apply transition if triggered
if transitionjson['is_transition']:
    target_state = transitionjson['to_state']
    scenario["visited_states"].append(target_state)

    # Handle fork transitions - block other paths
    if transition_type == "fork":
        for other_target in source_state["transitions"]:
            if other_target != target_state:
                source_state["transitions"][other_target]["isBlocked"] = True
```

**Transition Types**:
- **Parallel**: Multiple states can be active simultaneously
- **Fork**: Exclusive choice that blocks other outgoing transitions

**Prompt Accumulation** ([backend/strategies/mdagaw/mdagaw.py:720-745](../../../backend/strategies/mdagaw/mdagaw.py#L720-L745)):
```python
# Build accumulated system prompt from all visited states
accumulated_prompt = scenario["character"]
if "negprompt" in scenario:
    accumulated_prompt += "\n\n" + scenario["negprompt"]

for state_name in scenario["visited_states"]:
    if state_name == "START":
        continue

    # Get prompt from terminal states
    if state_name in ["SUCCESS", "FAIL"] and "tstates" in scenario:
        if "addprompt" in scenario["tstates"][state_name]:
            state_prompt = scenario["tstates"][state_name]["addprompt"]

    # Or from branch states
    else:
        for branch_name, branch_states in scenario["states"].items():
            if state_name in branch_states and "addprompt" in branch_states[state_name]:
                state_prompt = branch_states[state_name]["addprompt"]
                break

    if state_prompt:
        accumulated_prompt += "\n\n" + state_prompt
```

#### 5. Frontend Exhibit Display

**Specification** ([spec.md:66-69](../../../spec.md#L66-L69)):
- Frontend receives command to display `exhibit_to_display`
- Display synchronized with Voice Agent's topic change
- Creates seamless, uninterrupted experience

**Current Implementation**: **NOT IMPLEMENTED**

**Frontend Analysis** ([frontend/app/page.tsx:1-1081](../../../frontend/app/page.tsx#L1-L1081)):
- No exhibit display logic found
- No state variables for exhibit management
- No RPC handlers for exhibit commands
- No UI components for rendering exhibits

**Current RPC Methods** ([frontend/app/page.tsx:76-302](../../../frontend/app/page.tsx#L76-L302)):
- `checker` - Receives goal progress updates
- `postanalyzer` - Receives conversation analysis
- `hint` - Receives contextual hints
- `end_conversation` - Handles conversation termination

**Scenario Photos** ([frontend/app/page.tsx:753-757](../../../frontend/app/page.tsx#L753-L757)):
- Static preview images shown during scenario selection
- Loaded from `/photos/{skill}/{scenarioId}.png`
- Not dynamic exhibit display as specified

**UI Components**:
- [frontend/components/TranscriptionView.tsx](../../../frontend/components/TranscriptionView.tsx) - Shows conversation transcript
- [frontend/components/HintPanel.tsx](../../../frontend/components/HintPanel.tsx) - Displays hints
- [frontend/components/GoalProgressPanel.tsx](../../../frontend/components/GoalProgressPanel.tsx) - Shows progress meter
- [frontend/components/PostAnalyzerPanel.tsx](../../../frontend/components/PostAnalyzerPanel.tsx) - Post-conversation analysis
- **No exhibit viewer component exists**

### Architecture Comparison

| Aspect | Specification | Current Implementation |
|--------|--------------|----------------------|
| **Use Case** | Case interview practice (consulting, market sizing) | Social skills training (dating, negotiation, small talk) |
| **Structure** | Linear parts (1→2→3→4→5→6) | Graph-based state machine with branches |
| **State Tracking** | `current_part` (single active part) | `visited_states` (list of all activated states) |
| **Transitions** | `[PART_COMPLETE]` token detection | LLM evaluation of transition conditions |
| **Prompt Updates** | Replace `part_instructions` per part | Accumulate `addprompt` from all visited states |
| **Exhibit Display** | Dynamic image display per part | Not implemented |
| **Opening Prompts** | `ai_opening_prompt` per part | Single `opening` for entire scenario |
| **Goal** | Multi-phase analytical progression | Single conversation goal achievement |
| **Scenario Files** | `spec.json` with `parts` array | `scenarios/*.json` with `character`, `goal`, `negprompt` |
| **Skills** | Case interviews (market sizing, profitability, etc.) | Social skills (7 categories) |

### Code References

**Specification Files**:
- [spec.md](../../../spec.md) - Product specification document
- [spec.json](../../../spec.json) - Example case definition (DiamondLux)

**Backend Core**:
- [backend/livekitworker.py:50-424](../../../backend/livekitworker.py#L50-L424) - Main agent implementation
- [backend/utils.py:16-25](../../../backend/utils.py#L16-L25) - Scenario loading
- [backend/utils.py:95-121](../../../backend/utils.py#L95-L121) - Prompt assembly

**State Machine Strategies**:
- [backend/strategies/mdagaw/mdagaw.py:550-793](../../../backend/strategies/mdagaw/mdagaw.py#L550-L793) - Multi-branch state machine
- [backend/strategies/agentic/agentic.py:283-358](../../../backend/strategies/agentic/agentic.py#L283-L358) - Single state tracking
- [backend/strategies/posneg/posneg.py](../../../backend/strategies/posneg/posneg.py) - Feedback-based strategy

**Transition Logic**:
- [backend/old/transition.py:60-88](../../../backend/old/transition.py#L60-L88) - LLM-based transition evaluation
- [backend/strategies/mdagaw/mdagaw.py:632-709](../../../backend/strategies/mdagaw/mdagaw.py#L632-L709) - Transition execution

**Voice Services**:
- [backend/livekitworker.py:207-212](../../../backend/livekitworker.py#L207-L212) - Deepgram STT
- [backend/livekitworker.py:223-237](../../../backend/livekitworker.py#L223-L237) - ElevenLabs TTS
- [backend/livekitworker.py:213-216](../../../backend/livekitworker.py#L213-L216) - OpenAI LLM
- [backend/tts.py:149-261](../../../backend/tts.py#L149-L261) - Custom TTS implementation

**Frontend**:
- [frontend/app/page.tsx:1-1081](../../../frontend/app/page.tsx#L1-L1081) - Main application
- [frontend/app/api/scenarios/route.ts](../../../frontend/app/api/scenarios/route.ts) - Scenario listing API
- [frontend/app/api/scenario-detail/route.ts](../../../frontend/app/api/scenario-detail/route.ts) - Scenario details API
- [frontend/app/api/connection-details/route.ts](../../../frontend/app/api/connection-details/route.ts) - LiveKit connection

**Scenario Files**:
- [scenarios/smalltalk.json](../../../scenarios/smalltalk.json)
- [scenarios/attraction.json](../../../scenarios/attraction.json)
- [scenarios/artofpersuasion.json](../../../scenarios/artofpersuasion.json)
- [scenarios/negotiation.json](../../../scenarios/negotiation.json)
- [scenarios/conflictresolution.json](../../../scenarios/conflictresolution.json)
- [scenarios/decodingemotions.json](../../../scenarios/decodingemotions.json)
- [scenarios/manipulationdefense.json](../../../scenarios/manipulationdefense.json)

### Implementation Gaps

**Features Defined in Spec but Not Implemented**:

1. **`[PART_COMPLETE]` Token Detection**
   - Spec: Voice Agent emits token when objectives met
   - Reality: No token detection in codebase; uses LLM-evaluated conditions

2. **Linear Part Progression**
   - Spec: Sequential parts (part_1 → part_2 → part_3)
   - Reality: Graph-based state machine with parallel branches

3. **Dynamic `part_instructions` Replacement**
   - Spec: System prompt replaced with new `part_instructions` on each transition
   - Reality: Prompts accumulated from all visited states

4. **Exhibit Display**
   - Spec: `exhibit_to_display` field with synchronized image rendering
   - Reality: No exhibit display functionality; no frontend components or RPC handlers

5. **`ai_opening_prompt` per Part**
   - Spec: AI speaks new opening prompt when entering each part
   - Reality: Single `opening` message at conversation start

6. **Case Interview Structure**
   - Spec: Multi-phase case (framework → city selection → market sizing → profitability → risks → recommendation)
   - Reality: Single-goal roleplay conversations

**Features Implemented but Not in Spec**:

1. **Goal Progress Tracking**
   - [backend/checker.py](../../../backend/checker.py) - Evaluates progress toward conversation goal (0-10 scale)
   - [frontend/components/GoalProgressPanel.tsx](../../../frontend/components/GoalProgressPanel.tsx) - Visual progress display

2. **Hint System**
   - [backend/hint.py](../../../backend/hint.py) - Generates contextual hints
   - [frontend/components/HintPanel.tsx](../../../frontend/components/HintPanel.tsx) - Hint display

3. **Post-Conversation Analysis**
   - [backend/postanalyser.py](../../../backend/postanalyser.py) - Analyzes completed conversations
   - [frontend/components/PostAnalyzerPanel.tsx](../../../frontend/components/PostAnalyzerPanel.tsx) - Analysis display

4. **Fork/Parallel Transition Types**
   - [backend/strategies/mdagaw/mdagaw.py:683-692](../../../backend/strategies/mdagaw/mdagaw.py#L683-L692) - Exclusive fork choices that block alternatives

5. **Multiple Strategy Implementations**
   - Three different state machine approaches (mdagaw, agentic, posneg)
   - Located in [backend/strategies/](../../../backend/strategies/)

6. **Social Skills Training**
   - Seven skill categories not mentioned in spec
   - Focus on interpersonal scenarios rather than business cases

### Current System Flow Example

**Typical Conversation Flow**:

1. **Initialization** ([backend/livekitworker.py:176-203](../../../backend/livekitworker.py#L176-L203)):
   - User selects skill and scenario from frontend
   - Backend loads scenario from JSON file
   - System prompt assembled from `character` + `negprompt` + roleplay additions

2. **Opening** ([backend/livekitworker.py:84-86](../../../backend/livekitworker.py#L84-L86)):
   - Agent speaks scenario's `opening` message
   - Conversation begins

3. **User Turn** ([backend/livekitworker.py:242-251](../../../backend/livekitworker.py#L242-L251)):
   - User speaks → Deepgram STT converts to text
   - Message added to conversation history

4. **State Transition Check** ([backend/strategies/mdagaw/mdagaw.py:632-709](../../../backend/strategies/mdagaw/mdagaw.py#L632-L709)):
   - Collect available transitions from active states
   - LLM evaluates if any transition condition is met
   - If yes: add target state to `visited_states`, update prompts

5. **Agent Response** ([backend/strategies/mdagaw/mdagaw.py:747-760](../../../backend/strategies/mdagaw/mdagaw.py#L747-L760)):
   - Generate response using accumulated system prompt
   - ElevenLabs TTS converts to speech
   - Audio played to user

6. **Goal Progress Check** ([backend/livekitworker.py:310-332](../../../backend/livekitworker.py#L310-L332)):
   - After each agent message, check goal achievement
   - Send progress update to frontend via RPC
   - Frontend displays progress bar

7. **Ending** ([backend/livekitworker.py:116-157](../../../backend/livekitworker.py#L116-L157)):
   - Good ending: Goal achieved, congratulatory message
   - Bad ending: Negative trigger detected, failure message
   - User exit: User invokes `end_conversation()` function

### Historical Context

Based on the codebase structure, the development appears to have progressed as follows:

1. **Specification Phase**: [spec.md](../../../spec.md) and [spec.json](../../../spec.json) created as design documents for a case interview training system

2. **Pivot to Social Skills**: Implementation shifted to social skills training with different requirements:
   - More complex state machines needed (graph-based vs linear)
   - Different content domain (social interactions vs business analysis)
   - Added features like hints and real-time progress tracking

3. **Multiple Strategy Experiments**: Three different state machine implementations developed in [backend/strategies/](../../../backend/strategies/):
   - **agentic**: Simple current state tracking
   - **mdagaw**: Complex multi-branch with fork/parallel transitions
   - **posneg**: Feedback-based approach

4. **LiveKit Integration**: Voice infrastructure built around LiveKit agents framework with:
   - Real-time STT/TTS/LLM pipeline
   - RPC communication between backend and frontend
   - Session management and conversation history tracking

5. **Legacy Code Preserved**: Old implementations kept in [backend/old/](../../../backend/old/) for reference

The spec.json file appears to be **aspirational documentation** for a different product direction that was not pursued. The actual product is a voice-based social skills trainer, not a case interview practice tool.

## Related Research

No other research documents found in thoughts/shared/research/

## Open Questions

1. **Is the spec.json file still relevant?** Should it be updated to reflect the actual implementation, or is it documentation for a planned future feature?

2. **Why maintain three different strategy implementations?** Are they for different use cases, or is one preferred over others?

3. **What is the migration path from spec to reality?** If case interview practice is still desired, what would need to be built to match the specification?

4. **How are scenarios authored?** Is there tooling to help create the complex state machine structures, or are they hand-crafted JSON?

5. **What determines which strategy is used?** The code shows multiple strategies but it's unclear how one is selected at runtime.

6. **Is exhibit display planned for future development?** The frontend has infrastructure for RPC communication that could support this feature.
