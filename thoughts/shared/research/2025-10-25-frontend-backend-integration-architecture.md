---
date: 2025-10-25T22:02:19+0000
researcher: Claude
git_commit: 65929f9b9c61dfe4712bfae5ba02ed67dbbdf47c
branch: andrey-local-branch
repository: finesse
topic: "Frontend-Backend Integration Architecture for Voice Scenario Generation"
tags: [research, codebase, livekit, api-endpoints, scenario-loading, voice-integration]
status: complete
last_updated: 2025-10-25
last_updated_by: Claude
---

# Research: Frontend-Backend Integration Architecture for Voice Scenario Generation

**Date**: 2025-10-25T22:02:19+0000
**Researcher**: Claude
**Git Commit**: 65929f9b9c61dfe4712bfae5ba02ed67dbbdf47c
**Branch**: andrey-local-branch
**Repository**: finesse

## Research Question

How to implement 4 integration tasks to connect frontend-new with the existing backend:
1. Create `/api/generate-scenario` endpoint that returns mdagaw-compatible JSON
2. Wire ChatSidebar to backend API (replace mock timeout)
3. Integrate LiveKit voice into VoiceVisualizer (replace mock recording)
4. Pass generated scenario to voice agent on "Begin Practice"

## Summary

The codebase uses a hybrid architecture with Next.js API routes for REST endpoints and LiveKit's RPC system for real-time voice communication. Scenarios are passed via JWT token attributes during LiveKit connection establishment. The system supports two scenario formats: a simpler format for LiveKit workers and a complex mdagaw state-machine format for Gradio strategies.

**Key Integration Points:**
- **API Layer**: Next.js API routes at `frontend/app/api/*` handle scenario loading and LiveKit token generation
- **Voice Layer**: LiveKit room connections with RPC methods for bidirectional communication
- **Scenario Transmission**: Embedded in JWT token attributes (`skill`, `scenarioName`, `userName`, `userGender`)
- **Backend Worker**: LiveKit worker (`backend/livekitworker.py`) extracts scenario from token and initializes voice agent

## Detailed Findings

### 1. Current Backend API Structure

#### HTTP Server Framework
The application uses **Next.js 14 API Routes** (not Flask/FastAPI) for REST-like endpoints, combined with **LiveKit Agents Framework** for real-time voice communication.

#### Existing Next.js API Endpoints

**`GET /api/scenarios`** ([frontend/app/api/scenarios/route.ts](frontend/app/api/scenarios/route.ts))
- Returns list of all skills and their scenarios
- Reads from `scenarios/*.json` files
- Response structure: `{ skills: Skill[] }`

**`GET /api/connection-details`** ([frontend/app/api/connection-details/route.ts](frontend/app/api/connection-details/route.ts))
- Generates LiveKit connection tokens
- Query params: `skill`, `scenarioName`, `userName`, `userGender`
- Embeds scenario data in JWT token attributes (lines 93-98):
  ```typescript
  at.attributes = {
    skill,
    scenarioName,
    userName,
    userGender
  };
  ```
- Returns: `{ serverUrl, roomName, participantToken, participantName }`

**`GET /api/scenario-detail`** ([frontend/app/api/scenario-detail/route.ts](frontend/app/api/scenario-detail/route.ts))
- Returns detailed info for a specific scenario
- Query params: `skill`, `id`
- Reads from `scenarios/{skill}.json`

#### LiveKit RPC Methods (Real-time)

**Backend-to-Frontend** ([backend/livekitworker.py](backend/livekitworker.py)):
- `checker` (lines 104-110) - Goal progress updates
- `end_conversation` (line 440-468 in frontend) - Conversation end signal

**Frontend-to-Backend** ([frontend/app/page.tsx](frontend/app/page.tsx)):
- `hint` (lines 314-346) - Request contextual hints
- `postanalyzer` (lines 349-437) - Request conversation analysis

### 2. Scenario Loading and Structure

#### Simple Scenario Format (LiveKit Worker)

**Storage Location**: `/scenarios/*.json` (7 skill-based files)

**Structure** ([scenarios/smalltalk.json:2-26](scenarios/smalltalk.json)):
```json
{
  "scenarioId": {
    "description": "User-facing description",
    "goal": "Objective to achieve",
    "opening": "Initial bot message",
    "character": ["Personality trait 1", "Trait 2"],
    "negprompt": ["Resistance rule 1", "Rule 2"],
    "skill": "smalltalk",
    "botname": "CharacterName",
    "botgender": "male/female",
    "voice_description": "TTS voice description",
    "elevenlabs_voice_id": "voice_id_string"
  }
}
```

**Loading Function** ([backend/utils.py:16-25](backend/utils.py)):
```python
def load_scenarios(skills: list[str] = None):
    # Returns: {skill: {scenario_name: scenario_data}}
```

#### MDAGAW State Machine Format

**Storage Location**: `/backend/strategies/mdagaw/*.json`

**Structure** ([backend/strategies/mdagaw/cafeBarista.json](backend/strategies/mdagaw/cafeBarista.json)):
```json
{
  "name": "scenarioId",
  "botname": "Name",
  "goal": "User objective",
  "character": "Personality description",
  "negprompt": "Resistance instructions",
  "opening": "Initial message",
  "states": {
    "BranchName": {
      "StateName": {
        "name": "StateName",
        "addprompt": "Prompt addition when state active",
        "condition": "Activation condition",
        "transitions": {
          "TargetState": {
            "condition": "Transition trigger",
            "type": "parallel|fork"
          }
        }
      }
    }
  },
  "tstates": {
    "SUCCESS": { "addprompt": "...", "condition": "..." },
    "FAIL": { "addprompt": "...", "condition": "..." }
  },
  "skill": "custom",
  "level": "1"
}
```

**Key Features**:
- Multiple parallel branches can be active simultaneously
- Fork transitions block alternative paths
- Prompts accumulate as states are visited
- LLM evaluates transition conditions in natural language

### 3. LiveKit Integration in Current Frontend

#### Room Connection Flow ([frontend/app/page.tsx](frontend/app/page.tsx))

**Step 1: Request Connection Details** (lines 113-122)
```typescript
const url = new URL("/api/connection-details", window.location.origin);
url.searchParams.append("skill", selectedSkill);
url.searchParams.append("scenarioName", selectedScenario);
url.searchParams.append("userName", userName);
url.searchParams.append("userGender", userGender);
```

**Step 2: Connect to Room** (lines 127-128)
```typescript
await room.connect(connectionDetailsData.serverUrl, connectionDetailsData.participantToken);
await room.localParticipant.setMicrophoneEnabled(true);
```

**Step 3: Voice Assistant Hook** (line 203)
```typescript
const { state: agentState } = useVoiceAssistant();
```

#### RPC Communication

**Registering Handlers** (lines 76-101):
```typescript
room.registerRpcMethod('checker', async (data) => {
  const payload = JSON.parse(data.payload);
  setGoalProgress(payload);
  return 'ok';
});
```

**Calling Methods** (lines 327-331):
```typescript
const response = await roomContext.localParticipant.performRpc({
  destinationIdentity: serverParticipant,
  method: 'hint',
  payload: 'hint request',
});
```

#### Key Components Used
- `Room` from `livekit-client` - Core connection object
- `RoomContext` - Context provider for room state
- `useVoiceAssistant` - Hook for agent state
- `BarVisualizer` - Audio waveform visualization
- `RoomAudioRenderer` - Automatic audio rendering
- `VoiceAssistantControlBar` - Microphone controls

### 4. How Scenarios Are Passed to Voice Agent

#### Backend Worker Entry Point ([backend/livekitworker.py:176-203](backend/livekitworker.py))

**Extract from Token Attributes** (lines 177-184):
```python
ALL_SCENARIOS = finesse_utils.load_scenarios()
remote_participant = ctx.room.remote_participants[remote_participant_identity]
attributes = remote_participant.attributes
skill = attributes["skill"]
scenario_name = attributes["scenarioName"]
scenario_data = ALL_SCENARIOS[skill][scenario_name]
```

**Create Session Info** (lines 191-203):
```python
userdata = SessionInfo(
    userid=userid,
    username=username,
    usergender=usergender,
    skill=skill,
    scenario_name=scenario_name,
    scenario_data=scenario_data,
)
```

**Assemble System Prompt** ([backend/utils.py:95-121](backend/utils.py)):
```python
def assemble_prompt(scenario, username, usergender):
    # Formats character, goal, negprompt into system prompt
    # Replaces {username} and {usergender} placeholders
```

**Initialize Agent** ([backend/livekitworker.py:50-63](backend/livekitworker.py)):
```python
class FinesseTutor(agents.Agent):
    def __init__(self, userdata: SessionInfo):
        instructions = finesse_utils.assemble_prompt(
            scenario=userdata.scenario_data,
            username=userdata.username,
            usergender=userdata.usergender,
        )
        super().__init__(instructions=instructions)
```

**Opening Message** ([backend/livekitworker.py:73-86](backend/livekitworker.py)):
```python
async def on_enter(self):
    roleplay, script = self.split_opening(self.userdata.scenario_data["opening"])
    self.session.history.add_message(role="user", content=roleplay)
    self.session.say(text=script, allow_interruptions=False)
```

#### Runtime Access
Throughout the session, RPC handlers access scenario data via:
```python
agent = session.current_agent
scenario_data = agent.userdata.scenario_data
goal = scenario_data["goal"]
botname = scenario_data["botname"]
```

## Code References

**API Routes:**
- `frontend/app/api/scenarios/route.ts` - Scenario list endpoint
- `frontend/app/api/connection-details/route.ts:19-98` - LiveKit token generation
- `frontend/app/api/scenario-detail/route.ts` - Scenario detail endpoint

**Scenario Loading:**
- `backend/utils.py:16-25` - `load_scenarios()` function
- `backend/utils.py:95-121` - `assemble_prompt()` function
- `backend/strategies/mdagaw/mdagaw.py:34-49` - MDAGAW loading functions

**LiveKit Integration:**
- `frontend/app/page.tsx:26` - Room instance creation
- `frontend/app/page.tsx:103-129` - Connection establishment
- `frontend/app/page.tsx:76-101` - RPC method registration
- `frontend/app/page.tsx:327-331` - RPC method calls
- `backend/livekitworker.py:167-203` - Worker entrypoint
- `backend/livekitworker.py:33-40` - SessionInfo dataclass
- `backend/livekitworker.py:50-63` - Agent initialization

**Scenario Files:**
- `scenarios/smalltalk.json` - Example simple format
- `backend/strategies/mdagaw/cafeBarista.json` - Example state machine format

## Architecture Documentation

### Data Flow for Scenario-Based Voice Conversations

```
1. Frontend: User selects skill + scenario
   ↓
2. Frontend: Calls GET /api/connection-details?skill=X&scenarioName=Y
   ↓
3. Backend API: Generates JWT token with attributes {skill, scenarioName, userName, userGender}
   ↓
4. Frontend: Connects to LiveKit room with token
   ↓
5. Backend Worker: Extracts attributes from remote participant
   ↓
6. Backend Worker: Loads scenario from scenarios/{skill}.json
   ↓
7. Backend Worker: Assembles system prompt from scenario data
   ↓
8. Backend Worker: Initializes voice agent with instructions
   ↓
9. Backend Worker: Speaks opening message
   ↓
10. Runtime: RPC methods access scenario via agent.userdata.scenario_data
```

### Key Design Patterns

**Token-Based Scenario Transmission**: Scenarios aren't sent as room metadata or data messages. Instead, they're embedded in JWT token attributes and extracted by the backend when the agent joins the room.

**Two-Format System**: Simple format for voice-only scenarios, complex mdagaw format for state-machine-driven conversations with branching paths.

**Prompt Accumulation (MDAGAW)**: Instead of replacing prompts on state transitions, the system accumulates `addprompt` values from all visited states to build context progressively.

**RPC Bidirectionality**: Both frontend and backend can initiate RPC calls, enabling real-time progress updates and on-demand hints/analysis.

## Related Research

- [thoughts/shared/research/2025-10-25-spec-implementation-analysis.md](../research/2025-10-25-spec-implementation-analysis.md) - Detailed analysis of spec vs. implementation differences

## Implementation Guidance

### Task 1: Create `/api/generate-scenario` Endpoint

**Location**: Create `frontend-new/app/api/generate-scenario/route.ts`

**Input Format**:
```typescript
{
  scenario: string,  // User's scenario description
  goal: string       // User's goal
}
```

**Required Output** (mdagaw-compatible JSON):
```json
{
  "name": "generated_scenario_id",
  "botname": "CharacterName",
  "goal": "Extracted goal",
  "character": "Generated personality",
  "negprompt": "Generated resistance rules",
  "opening": "Generated opening message",
  "skill": "custom",
  "level": "1",
  "voice_description": "Generated voice description",
  "elevenlabs_voice_id": "default_voice_id"
}
```

**Note**: Simple format sufficient for basic demo; full mdagaw state machine optional.

### Task 2: Wire ChatSidebar to Backend

**File**: `frontend-new/src/components/practice/ChatSidebar.tsx:45-77`

**Current Code** (mock timeout):
```typescript
setTimeout(() => {
  if (questionCount === 0) {
    setMessages([...prev, { role: "assistant", content: "Got it! ..." }]);
    setQuestionCount(1);
  } else {
    setMessages([...prev, { role: "assistant", content: "Generating..." }]);
    onGenerate();
    setTimeout(() => { onReady(); }, 3000);
  }
}, 1000);
```

**Replace With** (actual API call):
```typescript
const response = await fetch('/api/generate-scenario', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ scenario, goal: input })
});
const generatedScenario = await response.json();
// Store generatedScenario for later use
```

### Task 3: Integrate LiveKit Voice

**File**: `frontend-new/src/components/practice/VoiceVisualizer.tsx`

**Pattern to Follow**: Copy LiveKit integration from `frontend/app/page.tsx`:
- Import `Room`, `RoomContext`, `useVoiceAssistant` from `@livekit/components-react`
- Create room instance with `useState(new Room())`
- Call `/api/connection-details` with generated scenario info
- Connect room: `room.connect(serverUrl, token)`
- Register RPC handlers: `room.registerRpcMethod('checker', ...)`
- Replace mock recording state (lines 14-29) with actual `useVoiceAssistant` hook

### Task 4: Pass Generated Scenario to Voice Agent

**Flow**:
1. ChatSidebar generates scenario → stores in React state
2. User clicks "Begin Practice" → VoiceVisualizer receives scenario via props
3. VoiceVisualizer calls `/api/connection-details` with:
   ```typescript
   ?skill=custom&scenarioName=generated_scenario_id&userName=User&userGender=neutral
   ```
4. Backend extracts from token and loads scenario (may need to save generated JSON to `scenarios/custom.json` first)

**Alternative Approach**: Save generated scenario to backend temp storage and reference by ID in connection details.

## Open Questions

1. Should generated scenarios be saved to `scenarios/custom.json` or kept in memory/temporary storage?
2. What ElevenLabs voice ID should be used for generated scenarios?
3. Should generated scenarios use simple format or full mdagaw state machine format?
4. How to handle scenario persistence across sessions (if user wants to retry same scenario)?
