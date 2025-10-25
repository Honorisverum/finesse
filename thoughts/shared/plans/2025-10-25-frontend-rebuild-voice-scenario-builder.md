# Frontend Rebuild: Voice Scenario Builder Implementation Plan

## Overview

Rebuild the Next.js frontend (`frontend/`) to incorporate the clean UI design from `frontend-new/` while maintaining all existing LiveKit voice integration. The new design features a landing page with scenario cards, a conversational chatbot interface for scenario generation, and a polished voice practice experience. The system will be designed for future database integration but initially use mock data for rapid prototyping.

## Current State Analysis

### Existing Next.js Frontend (`frontend/`)
- **Working Features**:
  - LiveKit voice integration with real-time RPC communication
  - API routes: `/api/scenarios`, `/api/connection-details`, `/api/scenario-detail`
  - Voice agent features: goal progress tracking, hints, post-conversation analysis
  - Scenario loading from JSON files in `scenarios/` directory
  - Full transcript view and audio visualization

- **UI Limitations**:
  - Basic form-based configuration (dropdowns for skill/scenario)
  - No conversational scenario builder
  - Minimal landing page design
  - Dense UI with all features visible at once

### Frontend-new (Vite App)
- **Good UI Elements**:
  - Clean landing page with "Try these" and "Recent conversations" cards
  - Conversational ChatSidebar (2-step scenario building)
  - Polished VoiceVisualizer with audio waveform
  - InfoSidebar for scenario details
  - Tailwind + shadcn-ui components

- **Limitations**:
  - No actual API integration (all mocked)
  - No LiveKit integration
  - Standalone Vite app (separate from Next.js)

### Scenario System
- **Storage**: JSON files in `scenarios/{skill}.json`
- **Loading**: `backend/utils.py` loads scenarios on-demand
- **Format**: Simple format with `{description, goal, opening, character[], negprompt[], botname, voice_id}`
- **Backend**: LiveKit worker extracts scenarios from JWT token attributes

## Desired End State

A unified Next.js application with:

1. **Landing Page** (`/`)
   - Hero section with scenario description input
   - "Try these" section with clickable scenario cards (from database in future, mock for now)
   - "Recent conversations" section (from database in future, mock for now)
   - Clicking a card jumps directly to voice practice with that scenario

2. **Practice Page** (`/practice`)
   - **Left Panel**: ChatSidebar - conversational 2-step scenario builder
   - **Center Panel**: VoiceVisualizer - audio waveform and voice controls
   - **Right Panel**: InfoSidebar - generated scenario details
   - Goal progress and transcript integrated cleanly
   - State flow: setup → generating → ready → active

3. **API Endpoints**
   - `POST /api/generate-scenario` - LLM-powered scenario generation
   - `GET /api/scenarios` - List practice scenarios (mock data, database-ready)
   - `GET /api/conversations/recent` - Recent conversations (mock data, database-ready)
   - Existing endpoints remain functional

4. **Database-Ready Architecture**
   - Clear data models/types defined
   - Mock data services with clean interfaces
   - TODO comments at all integration points
   - Easy to swap mock → database implementation

### Verification
Success state verified when:
- Landing page displays with clickable scenario cards
- Clicking card navigates to `/practice` with pre-loaded scenario
- Chatbot interface generates scenarios via LLM
- Voice call starts with generated scenario
- All existing LiveKit features work (progress, transcript)

## What We're NOT Doing

1. **No database implementation** - Mock data only, clear TODOs for later
2. **No user authentication** - Single-user experience for demo
3. **No conversation persistence** - Don't save conversation history yet
4. **No hints/analysis panels** - Focus on core flow (can add back later)
5. **No frontend-new app** - Not integrating two apps, just borrowing UI
6. **No state machine scenarios** - Use simple format only
7. **No mobile optimization** - Desktop-first for hackathon demo

## Implementation Approach

**Strategy**: Incremental replacement of Next.js frontend while keeping all working features functional. Port UI components from frontend-new, wire to existing backend infrastructure, add new generation endpoint.

**Key Principles**:
- Keep existing API routes working throughout
- Test each phase independently before proceeding
- Use TypeScript for type safety
- Leverage existing LiveKit integration patterns
- Design data layer for easy database swap

---

## Phase 1: Setup Data Models and Mock Data Layer

### Overview
Define TypeScript types for all data entities and create a mock data service that simulates database responses. This establishes clean contracts for future database integration.

### Changes Required

#### 1. Create Type Definitions
**File**: `frontend/types/database.ts` (new)

```typescript
// Scenario card shown on landing page
export type ScenarioCard = {
  id: string;
  title: string;
  description: string;
  icon: string;
  messageCount: string; // e.g., "2.7k"
};

// Full scenario data for voice practice
export type ScenarioData = {
  id: string;
  title: string;
  description: string;
  goal: string;
  opening: string;
  character: string[];
  negprompt: string[];
  skill: string;
  botname: string;
  botgender: "male" | "female" | "neutral";
  voice_description: string;
  elevenlabs_voice_id: string;
};

// Recent conversation record
export type ConversationRecord = {
  id: string;
  title: string;
  description: string;
  icon: string;
  messageCount: string;
  timestamp: Date;
  scenarioId: string;
};

// Request/response for scenario generation
export type GenerateScenarioRequest = {
  scenario: string; // User's description
  goal: string;     // User's goal
};

export type GenerateScenarioResponse = {
  scenarioData: ScenarioData;
};
```

#### 2. Create Mock Data Service
**File**: `frontend/lib/mockData.ts` (new)

```typescript
import { ScenarioCard, ConversationRecord, ScenarioData } from "@/types/database";

// TODO: Replace with database queries
export const MOCK_TRY_THESE_SCENARIOS: ScenarioCard[] = [
  {
    id: "practice-interviewing",
    title: "Practice interviewing",
    description: "Prepare for your next job interview with realistic practice scenarios",
    icon: "👔",
    messageCount: "2.7k"
  },
  {
    id: "pitch-to-investors",
    title: "Pitch to investors",
    description: "Perfect your startup pitch and handle tough investor questions",
    icon: "💼",
    messageCount: "1.2k"
  },
  {
    id: "negotiate-salary",
    title: "Negotiate salary",
    description: "Build confidence negotiating compensation with your manager",
    icon: "💰",
    messageCount: "3.4k"
  },
  {
    id: "difficult-conversations",
    title: "Difficult conversations",
    description: "Practice handling confrontation and delivering tough feedback",
    icon: "💬",
    messageCount: "5.1k"
  },
  // ... more scenarios
];

// TODO: Replace with database queries
export const MOCK_RECENT_CONVERSATIONS: ConversationRecord[] = [
  {
    id: "conv-001",
    title: "VC Pitch Practice",
    description: "Practiced pitching startup idea to skeptical venture capitalist",
    icon: "🚀",
    messageCount: "24 messages",
    timestamp: new Date("2025-10-24"),
    scenarioId: "pitch-to-investors"
  },
  // ... more conversations
];

// TODO: Replace with database lookup
export function getScenarioById(id: string): ScenarioData | null {
  // For now, generate a mock scenario based on the card
  const card = MOCK_TRY_THESE_SCENARIOS.find(s => s.id === id);
  if (!card) return null;

  return {
    id: card.id,
    title: card.title,
    description: card.description,
    goal: "Successfully complete the practice scenario",
    opening: `*You find yourself in a ${card.title.toLowerCase()} situation* Let's begin.`,
    character: ["Professional and challenging", "Provides realistic feedback"],
    negprompt: ["Don't make it too easy", "Push for specifics"],
    skill: "custom",
    botname: "Practice Partner",
    botgender: "neutral",
    voice_description: "Clear, professional voice",
    elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM" // Default voice
  };
}
```

#### 3. Update Existing Types
**File**: `frontend/utils/types.ts`

Add to existing types:
```typescript
// Add to existing file
export type { ScenarioCard, ConversationRecord, ScenarioData, GenerateScenarioRequest, GenerateScenarioResponse } from "@/types/database";
```

### Success Criteria

#### Automated Verification:
- [x] TypeScript compilation passes: `cd frontend && npm run build`
- [x] No type errors: `cd frontend && npx tsc --noEmit`
- [x] Mock data exports successfully in node: `node -e "require('./frontend/lib/mockData.js')"`

#### Manual Verification:
- [ ] Types are clearly defined with JSDoc comments
- [ ] Mock data structure matches type definitions exactly
- [ ] TODO comments are present and descriptive

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the types and data structure look correct before proceeding to Phase 2.

---

## Phase 2: Create Scenario Generation API Endpoint

### Overview
Build `/api/generate-scenario` endpoint that uses OpenAI to convert user descriptions into structured scenario JSON. Returns data in the format expected by the LiveKit backend.

### Changes Required

#### 1. Create Generation Endpoint
**File**: `frontend/app/api/generate-scenario/route.ts` (new)

```typescript
import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { GenerateScenarioRequest, GenerateScenarioResponse } from "@/types/database";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const body: GenerateScenarioRequest = await request.json();
    const { scenario, goal } = body;

    if (!scenario || !goal) {
      return NextResponse.json(
        { error: "Missing scenario or goal" },
        { status: 400 }
      );
    }

    // Generate scenario using OpenAI
    const completion = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: `You are a scenario generator for conversation practice. Generate a realistic character and scenario based on the user's description.

Return a JSON object with these fields:
- botname: The character's name
- botgender: "male", "female", or "neutral"
- goal: The user's objective (use the provided goal)
- opening: Initial message from the character (can include roleplay in *asterisks*)
- character: Array of 3-5 strings describing personality, background, communication style
- negprompt: Array of 3-5 strings describing how the character resists or challenges the user
- voice_description: Description of voice characteristics for text-to-speech

Be creative and realistic. Make the character challenging but fair.`
        },
        {
          role: "user",
          content: `Scenario: ${scenario}\nGoal: ${goal}`
        }
      ],
      temperature: 0.8,
      response_format: { type: "json_object" }
    });

    const generatedContent = completion.choices[0].message.content;
    if (!generatedContent) {
      throw new Error("No content generated");
    }

    const generated = JSON.parse(generatedContent);

    // Build complete scenario data
    const scenarioData: GenerateScenarioResponse["scenarioData"] = {
      id: `generated_${Date.now()}`,
      title: scenario,
      description: scenario,
      goal: goal,
      opening: generated.opening || "*The scenario begins* Hello.",
      character: generated.character || ["Professional character"],
      negprompt: generated.negprompt || ["Maintain professional distance"],
      skill: "custom",
      botname: generated.botname || "Practice Partner",
      botgender: generated.botgender || "neutral",
      voice_description: generated.voice_description || "Clear professional voice",
      elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM" // Default ElevenLabs voice
    };

    return NextResponse.json({ scenarioData } as GenerateScenarioResponse);

  } catch (error) {
    console.error("Error generating scenario:", error);
    return NextResponse.json(
      { error: "Failed to generate scenario" },
      { status: 500 }
    );
  }
}

export const runtime = 'nodejs';
```

#### 2. Add Environment Variable Check
**File**: `frontend/.env.local` (update or create)

```bash
OPENAI_API_KEY=sk-...
```

**File**: `frontend/.env.example` (update or create)

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

#### 3. Update Connection Details Endpoint for Custom Scenarios
**File**: `frontend/app/api/connection-details/route.ts`

Modify to handle generated scenarios stored in session or passed as JSON:

```typescript
// Around line 30, add after existing scenario loading:
import { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const skill = searchParams.get("skill");
  const scenarioName = searchParams.get("scenarioName");
  const userName = searchParams.get("userName");
  const userGender = searchParams.get("userGender");

  // NEW: Check if scenarioData is passed directly for generated scenarios
  const scenarioDataParam = searchParams.get("scenarioData");
  let scenarioData: any;

  if (scenarioDataParam) {
    // For generated scenarios, data is passed directly
    try {
      scenarioData = JSON.parse(scenarioDataParam);
    } catch (e) {
      return NextResponse.json({ error: "Invalid scenarioData" }, { status: 400 });
    }
  } else {
    // Existing logic for loading from files
    // ... keep existing code
  }

  // ... rest remains the same
}
```

### Success Criteria

#### Automated Verification:
- [x] API endpoint compiles: `cd frontend && npm run build`
- [x] TypeScript types are correct: `cd frontend && npx tsc --noEmit`
- [x] Environment variable is set: `test -n "$OPENAI_API_KEY" && echo "OK" || echo "Missing"`

#### Manual Verification:
- [ ] Test API call returns valid JSON: `curl -X POST http://localhost:3000/api/generate-scenario -H "Content-Type: application/json" -d '{"scenario":"job interview","goal":"get hired"}'`
- [ ] Response matches GenerateScenarioResponse type
- [ ] Generated scenario has all required fields
- [ ] OpenAI call completes in reasonable time (<10 seconds)

**Implementation Note**: After completing this phase and all automated verification passes, test the API endpoint manually with curl or Postman before proceeding to Phase 3.

---

## Phase 3: Port UI Components from frontend-new

### Overview
Copy shadcn-ui components and practice page components from frontend-new into the Next.js frontend. Adapt them to work with Next.js conventions (app router, client components).

### Changes Required

#### 1. Copy shadcn-ui Base Components
**Copy from**: `frontend-new/src/components/ui/*`
**Copy to**: `frontend/components/ui/*`

Components to copy:
- `button.tsx`
- `input.tsx`
- `card.tsx`
- `scroll-area.tsx`
- `sheet.tsx`
- Any other UI primitives used

**Modification needed**: Add `"use client"` directive at top of each file for Next.js app router

#### 2. Copy Practice Components
**File**: `frontend/components/practice/ChatSidebar.tsx` (new)

Copy from `frontend-new/src/components/practice/ChatSidebar.tsx` and modify:

```typescript
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Sparkles, ArrowLeft } from "lucide-react";
import Link from "next/link"; // CHANGE: Use Next.js Link
import { GenerateScenarioRequest, GenerateScenarioResponse } from "@/types/database";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatSidebarProps {
  scenario: string;
  onScenarioChange: (scenario: string) => void;
  onGenerate: () => void;
  onReady: (scenarioData: any) => void; // CHANGE: Pass generated scenario data
}

export default function ChatSidebar({
  scenario,
  onScenarioChange,
  onGenerate,
  onReady
}: ChatSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Welcome! Tell me about the conversation you'd like to practice. For example: 'I need to pitch my startup to a VC' or 'I want to negotiate a raise with my boss'.",
    },
  ]);
  const [input, setInput] = useState("");
  const [questionCount, setQuestionCount] = useState(0);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);

    if (questionCount === 0) {
      onScenarioChange(input);
    }

    const currentInput = input;
    setInput("");

    // CHANGE: Replace setTimeout with actual API call
    if (questionCount === 0) {
      // First question - ask for goal
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Got it! What's your main goal for this conversation? What would success look like?",
          },
        ]);
        setQuestionCount(1);
      }, 500);
    } else {
      // Second question - generate scenario
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Excellent! I'm now generating your practice scenario and persona...",
        },
      ]);
      onGenerate();

      try {
        // CHANGE: Call actual API
        const response = await fetch('/api/generate-scenario', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scenario: scenario,
            goal: currentInput
          } as GenerateScenarioRequest)
        });

        if (!response.ok) {
          throw new Error('Failed to generate scenario');
        }

        const data: GenerateScenarioResponse = await response.json();

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Your scenario is ready! Click the 'Begin Practice' button to start your conversation.",
          },
        ]);

        onReady(data.scenarioData);
      } catch (error) {
        console.error('Error generating scenario:', error);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Sorry, there was an error generating your scenario. Please try again.",
          },
        ]);
      }
    }
  };

  // ... rest of the component remains the same as frontend-new
  // Just ensure all imports use Next.js conventions
}
```

**File**: `frontend/components/practice/VoiceVisualizer.tsx` (new)

Copy from `frontend-new/src/components/practice/VoiceVisualizer.tsx` - initially keep it as is, we'll wire up LiveKit in Phase 6.

**File**: `frontend/components/practice/InfoSidebar.tsx` (new)

Copy from `frontend-new/src/components/practice/InfoSidebar.tsx` and modify to display actual scenario data.

#### 3. Copy Utility Files
**File**: `frontend/lib/utils.ts`

If not already present, copy from `frontend-new/src/lib/utils.ts` (the `cn()` className helper).

#### 4. Update Tailwind Config
**File**: `frontend/tailwind.config.ts`

Merge configuration from `frontend-new/tailwind.config.ts`:
- Copy custom colors
- Copy animations
- Copy any custom utilities

#### 5. Update Global Styles
**File**: `frontend/app/globals.css`

Add shadcn-ui CSS variables and any custom styles from `frontend-new/src/index.css`.

### Success Criteria

#### Automated Verification:
- [x] All components compile: `cd frontend && npm run build`
- [x] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [x] No missing dependencies: `cd frontend && npm install`
- [x] Tailwind generates styles correctly: `cd frontend && npm run build`

#### Manual Verification:
- [ ] Components render without errors in Storybook or test page
- [ ] Styles match frontend-new appearance
- [ ] No console errors when components load
- [ ] Lucide icons render correctly

**Implementation Note**: After completing this phase, create a test page to verify all components render correctly before integrating into main app.

---

## Phase 4: Build Landing Page

### Overview
Create new landing page at `/` with hero section, "Try these" scenario cards, and "Recent conversations" section using the ported UI components.

### Changes Required

#### 1. Create Landing Page Component
**File**: `frontend/app/page.tsx` (replace existing)

```typescript
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { MessageSquare, Sparkles, Target, Send } from "lucide-react";
import { MOCK_TRY_THESE_SCENARIOS, MOCK_RECENT_CONVERSATIONS } from "@/lib/mockData";
import ConversationCard from "@/components/ConversationCard";

export default function Home() {
  const [message, setMessage] = useState("");
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      // Navigate to practice page with custom scenario
      router.push(`/practice?custom=${encodeURIComponent(message)}`);
    }
  };

  const handleCardClick = (scenarioId: string) => {
    // Navigate to practice with pre-selected scenario
    router.push(`/practice?scenario=${scenarioId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-secondary/20">
      {/* Hero Section */}
      <main className="container mx-auto px-6 pt-24 pb-32">
        <div className="max-w-3xl mx-auto text-center">
          {/* Animated Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-8">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">AI-Powered Practice</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-5xl md:text-7xl font-bold mb-6">
            Practice conversations
            <br />
            <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              before they happen
            </span>
          </h1>

          {/* Description */}
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Pitch to investors. Negotiate with your boss. Prepare for difficult conversations.
            Describe your scenario and practice with an AI persona tailored to your goal.
          </p>

          {/* Chat Input */}
          <form onSubmit={handleSubmit} className="mb-16">
            <div className="relative max-w-2xl mx-auto">
              <Input
                type="text"
                placeholder="Describe your conversation scenario..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="h-14 pr-14 text-base border-2 focus-visible:ring-primary"
              />
              <Button
                type="submit"
                size="icon"
                className="absolute right-1 top-1 h-12 w-12"
                disabled={!message.trim()}
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </form>

          {/* Feature Pills */}
          <div className="flex flex-wrap items-center justify-center gap-8">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MessageSquare className="h-4 w-4 text-primary" />
              <span>Custom personas</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Target className="h-4 w-4 text-primary" />
              <span>Goal-oriented practice</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>Performance scoring</span>
            </div>
          </div>
        </div>
      </main>

      {/* Dashboard Section */}
      <section className="container mx-auto px-6 pb-20 pt-16">
        <div className="max-w-6xl mx-auto">
          {/* Try these */}
          <div className="mb-10">
            <h2 className="text-2xl font-bold mb-4">Try these</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {MOCK_TRY_THESE_SCENARIOS.map((scenario) => (
                <div key={scenario.id} onClick={() => handleCardClick(scenario.id)}>
                  <ConversationCard
                    title={scenario.title}
                    description={scenario.description}
                    icon={scenario.icon}
                    messageCount={scenario.messageCount}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Recent Conversations */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Recent conversations</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {MOCK_RECENT_CONVERSATIONS.map((conversation) => (
                <div key={conversation.id} onClick={() => handleCardClick(conversation.scenarioId)}>
                  <ConversationCard
                    title={conversation.title}
                    description={conversation.description}
                    icon={conversation.icon}
                    messageCount={conversation.messageCount}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
```

#### 2. Create ConversationCard Component
**File**: `frontend/components/ConversationCard.tsx` (new)

```typescript
"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ConversationCardProps {
  title: string;
  description: string;
  icon: string;
  messageCount: string;
}

export default function ConversationCard({
  title,
  description,
  icon,
  messageCount
}: ConversationCardProps) {
  return (
    <Card className="cursor-pointer hover:shadow-lg transition-all hover:scale-105">
      <CardHeader>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">{icon}</span>
          <CardTitle className="text-lg">{title}</CardTitle>
        </div>
        <CardDescription className="text-sm">{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">{messageCount}</p>
      </CardContent>
    </Card>
  );
}
```

### Success Criteria

#### Automated Verification:
- [ ] Landing page compiles: `cd frontend && npm run build`
- [ ] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [ ] No missing imports: Build succeeds without module errors
- [ ] Routing works: `npm run dev` starts without errors

#### Manual Verification:
- [ ] Landing page displays correctly at http://localhost:3000
- [ ] Hero section shows with gradient text
- [ ] All scenario cards render from mock data
- [ ] Clicking a card navigates to `/practice?scenario=id`
- [ ] Input box accepts text and navigates to `/practice?custom=text`
- [ ] Responsive layout works on different screen sizes
- [ ] No layout shifts or flashing

**Implementation Note**: After completing this phase, verify the landing page works fully before proceeding to build the practice page.

---

## Phase 5: Build Practice Page with Chat Interface

### Overview
Create `/practice` page that shows ChatSidebar, VoiceVisualizer, and InfoSidebar in a three-column layout. Handle both custom scenarios (from chat) and pre-selected scenarios (from landing page cards).

### Changes Required

#### 1. Create Practice Page
**File**: `frontend/app/practice/page.tsx` (new)

```typescript
"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ChatSidebar from "@/components/practice/ChatSidebar";
import VoiceVisualizer from "@/components/practice/VoiceVisualizer";
import InfoSidebar from "@/components/practice/InfoSidebar";
import { getScenarioById } from "@/lib/mockData";
import { ScenarioData } from "@/types/database";

type PracticeState = "setup" | "generating" | "ready" | "active";

function PracticePageContent() {
  const searchParams = useSearchParams();
  const scenarioId = searchParams.get("scenario");
  const customScenario = searchParams.get("custom");

  const [scenario, setScenario] = useState("");
  const [practiceState, setPracticeState] = useState<PracticeState>("setup");
  const [scenarioData, setScenarioData] = useState<ScenarioData | null>(null);

  // Load pre-selected scenario from landing page
  useEffect(() => {
    if (scenarioId) {
      // TODO: Replace with database lookup
      const loadedScenario = getScenarioById(scenarioId);
      if (loadedScenario) {
        setScenarioData(loadedScenario);
        setScenario(loadedScenario.title);
        setPracticeState("ready");
      }
    } else if (customScenario) {
      // Pre-fill custom scenario from hero input
      setScenario(customScenario);
    }
  }, [scenarioId, customScenario]);

  const handleGenerate = () => {
    setPracticeState("generating");
  };

  const handleReady = (generatedScenarioData: ScenarioData) => {
    setScenarioData(generatedScenarioData);
    setPracticeState("ready");
  };

  const handleStart = () => {
    setPracticeState("active");
  };

  const showInfoSidebar = practiceState === "ready" || practiceState === "active";

  return (
    <div className="flex h-screen w-full bg-background">
      <ChatSidebar
        scenario={scenario}
        onScenarioChange={setScenario}
        onGenerate={handleGenerate}
        onReady={handleReady}
      />
      <main className="flex-1 flex items-center justify-center p-8">
        <VoiceVisualizer
          practiceState={practiceState}
          scenarioData={scenarioData}
          onStart={handleStart}
        />
      </main>
      {showInfoSidebar && scenarioData && (
        <InfoSidebar scenario={scenarioData} />
      )}
    </div>
  );
}

export default function PracticePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PracticePageContent />
    </Suspense>
  );
}
```

#### 2. Update VoiceVisualizer to Accept Scenario Data
**File**: `frontend/components/practice/VoiceVisualizer.tsx`

Modify props to include scenarioData:

```typescript
import { ScenarioData } from "@/types/database";

interface VoiceVisualizerProps {
  practiceState: PracticeState;
  scenarioData: ScenarioData | null;
  onStart: () => void;
}

export default function VoiceVisualizer({
  practiceState,
  scenarioData,
  onStart
}: VoiceVisualizerProps) {
  // ... existing visualization code

  // Will wire up LiveKit in Phase 6
}
```

#### 3. Update InfoSidebar to Display Scenario Data
**File**: `frontend/components/practice/InfoSidebar.tsx`

```typescript
"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Target, User, MessageSquare } from "lucide-react";
import { ScenarioData } from "@/types/database";

interface InfoSidebarProps {
  scenario: ScenarioData;
}

export default function InfoSidebar({ scenario }: InfoSidebarProps) {
  return (
    <aside className="w-96 border-l border-border bg-card p-6">
      <ScrollArea className="h-full">
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold mb-2">{scenario.title}</h2>
            <p className="text-sm text-muted-foreground">{scenario.description}</p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5 text-primary" />
                Your Goal
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm">{scenario.goal}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5 text-primary" />
                Character
              </CardTitle>
              <CardDescription>{scenario.botname}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="text-sm space-y-2">
                {scenario.character.map((trait, index) => (
                  <li key={index} className="flex gap-2">
                    <span className="text-primary">•</span>
                    <span>{trait}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-primary" />
                Opening
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm italic">{scenario.opening}</p>
            </CardContent>
          </Card>
        </div>
      </ScrollArea>
    </aside>
  );
}
```

### Success Criteria

#### Automated Verification:
- [ ] Practice page compiles: `cd frontend && npm run build`
- [ ] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [ ] All imports resolve correctly
- [ ] Next.js app router works: `npm run dev`

#### Manual Verification:
- [ ] Navigate to `/practice` shows setup state
- [ ] Navigate to `/practice?scenario=id` shows ready state with loaded scenario
- [ ] Navigate to `/practice?custom=text` pre-fills chat with text
- [ ] ChatSidebar shows on left, VoiceVisualizer in center
- [ ] After generation, InfoSidebar appears on right
- [ ] State transitions work: setup → generating → ready
- [ ] Layout is responsive and doesn't break

**Implementation Note**: After completing this phase, test all navigation paths from the landing page before integrating LiveKit voice.

---

## Phase 6: Integrate LiveKit Voice with New UI

### Overview
Wire the polished VoiceVisualizer UI to the existing LiveKit integration. Create room connection, handle voice states, and display audio visualization while maintaining the clean UI design.

### Changes Required

#### 1. Update VoiceVisualizer with LiveKit Integration
**File**: `frontend/components/practice/VoiceVisualizer.tsx`

Replace mock recording with real LiveKit:

```typescript
"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Mic, MicOff } from "lucide-react";
import { Room } from "livekit-client";
import {
  useVoiceAssistant,
  useRoomContext,
  BarVisualizer,
  RoomAudioRenderer,
} from "@livekit/components-react";
import { ScenarioData } from "@/types/database";

type PracticeState = "setup" | "generating" | "ready" | "active";

interface VoiceVisualizerProps {
  practiceState: PracticeState;
  scenarioData: ScenarioData | null;
  onStart: () => void;
}

export default function VoiceVisualizer({
  practiceState,
  scenarioData,
  onStart
}: VoiceVisualizerProps) {
  const roomContext = useRoomContext();
  const { state: agentState, audioTrack } = useVoiceAssistant();
  const [isConnecting, setIsConnecting] = useState(false);

  const handleBeginPractice = async () => {
    if (!scenarioData) return;

    setIsConnecting(true);
    try {
      // Call connection details API with scenario data
      const url = new URL("/api/connection-details", window.location.origin);

      // For generated scenarios, pass data directly
      // TODO: For database scenarios, pass scenarioId instead
      url.searchParams.append("skill", scenarioData.skill);
      url.searchParams.append("scenarioName", scenarioData.id);
      url.searchParams.append("userName", "User"); // TODO: Get from auth
      url.searchParams.append("userGender", "neutral");

      // Pass scenario data directly for custom scenarios
      if (scenarioData.skill === "custom") {
        url.searchParams.append("scenarioData", JSON.stringify(scenarioData));
      }

      const response = await fetch(url.toString());
      const connectionDetails = await response.json();

      // Connect to LiveKit room
      await roomContext.connect(
        connectionDetails.serverUrl,
        connectionDetails.participantToken
      );

      // Enable microphone
      await roomContext.localParticipant.setMicrophoneEnabled(true);

      onStart();
    } catch (error) {
      console.error("Failed to connect:", error);
    } finally {
      setIsConnecting(false);
    }
  };

  // Setup state
  if (practiceState === "setup") {
    return (
      <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
        <div className="w-full border border-border rounded-2xl p-12 shadow-lg">
          <div className="text-center space-y-4">
            <h3 className="text-2xl font-semibold text-muted-foreground">
              Describe your scenario in the chat
            </h3>
            <p className="text-sm text-muted-foreground">
              Tell me what conversation you'd like to practice
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Generating state
  if (practiceState === "generating") {
    return (
      <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
        <div className="w-full bg-card border border-border rounded-2xl p-8 shadow-lg">
          <div className="space-y-4">
            <Skeleton className="w-full h-48" />
          </div>
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-2xl font-semibold">Generating your scenario...</h3>
          <p className="text-sm text-muted-foreground">
            Creating a custom persona and conversation flow
          </p>
        </div>
      </div>
    );
  }

  // Ready state
  if (practiceState === "ready") {
    return (
      <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
        <div className="w-full bg-card border border-border rounded-2xl p-8 shadow-lg">
          <BarVisualizer
            state={agentState}
            barCount={5}
            trackRef={audioTrack}
            className="w-full h-48 opacity-30"
          />
        </div>

        <div className="text-center space-y-2">
          <h3 className="text-2xl font-semibold">Your scenario is ready!</h3>
          <p className="text-sm text-muted-foreground">
            Click below to begin your practice conversation
          </p>
        </div>

        <Button
          size="lg"
          className="h-16 px-12 text-lg"
          onClick={handleBeginPractice}
          disabled={isConnecting}
        >
          {isConnecting ? "Connecting..." : "Begin Practice"}
        </Button>
      </div>
    );
  }

  // Active state
  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-4xl">
      <div className="w-full bg-card border border-border rounded-2xl p-8 shadow-lg">
        <BarVisualizer
          state={agentState}
          barCount={5}
          trackRef={audioTrack}
          className="w-full h-48"
        />
      </div>

      <div className="text-center space-y-2">
        <p className="text-sm text-muted-foreground">
          {agentState === "listening" ? "Listening..." :
           agentState === "thinking" ? "Thinking..." :
           agentState === "speaking" ? "Speaking..." : "Ready"}
        </p>
        <h3 className="text-2xl font-semibold">
          In conversation with {scenarioData?.botname}
        </h3>
      </div>

      <RoomAudioRenderer />
    </div>
  );
}
```

#### 2. Wrap Practice Page with RoomContext
**File**: `frontend/app/practice/page.tsx`

Add RoomContext.Provider:

```typescript
"use client";

import { useState, useEffect, Suspense } from "react";
import { Room } from "livekit-client";
import { RoomContext } from "@livekit/components-react";
// ... other imports

function PracticePageContent() {
  const [room] = useState(new Room());
  // ... existing state

  return (
    <RoomContext.Provider value={room}>
      <div className="flex h-screen w-full bg-background">
        {/* ... existing components */}
      </div>
    </RoomContext.Provider>
  );
}
```

#### 3. Add Goal Progress and Transcript (Optional but Recommended)
**File**: `frontend/components/practice/VoiceVisualizer.tsx`

Add at bottom of active state:

```typescript
// Add after audio renderer
<div className="w-full max-w-2xl space-y-4">
  {/* Goal Progress */}
  <GoalProgressPanel goalProgress={goalProgress} />

  {/* Transcript */}
  <TranscriptionView transcriptions={combinedTranscriptions} />
</div>
```

Import and wire up goal progress tracking (pattern from existing frontend):

```typescript
const [goalProgress, setGoalProgress] = useState<GoalProgressData | null>(null);

useEffect(() => {
  if (roomContext) {
    roomContext.registerRpcMethod('checker', async (data) => {
      const payload = JSON.parse(data.payload);
      setGoalProgress(payload);
      return 'ok';
    });

    return () => {
      roomContext.unregisterRpcMethod('checker');
    };
  }
}, [roomContext]);
```

### Success Criteria

#### Automated Verification:
- [ ] Components compile with LiveKit imports: `cd frontend && npm run build`
- [ ] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [ ] LiveKit dependencies installed: `npm list livekit-client @livekit/components-react`

#### Manual Verification:
- [ ] Click "Begin Practice" connects to LiveKit room
- [ ] Microphone permission requested and granted
- [ ] Audio waveform visualizes agent voice
- [ ] Agent state updates correctly (listening/thinking/speaking)
- [ ] Voice conversation works end-to-end
- [ ] Goal progress updates appear during conversation
- [ ] Transcript shows both user and agent messages
- [ ] Audio quality is clear and latency is acceptable

**Implementation Note**: After completing this phase, test a full conversation from landing page → scenario selection → generation → voice call → completion.

---

## Phase 7: Polish and Testing

### Overview
Final polish, error handling, loading states, and comprehensive testing of the full user flow.

### Changes Required

#### 1. Add Error Boundaries
**File**: `frontend/app/error.tsx` (new)

```typescript
"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <h2 className="text-2xl font-bold mb-4">Something went wrong!</h2>
      <p className="text-muted-foreground mb-4">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

#### 2. Add Loading States
**File**: `frontend/app/loading.tsx` (new)

```typescript
export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
    </div>
  );
}
```

#### 3. Add 404 Page
**File**: `frontend/app/not-found.tsx` (new)

```typescript
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <h2 className="text-4xl font-bold mb-4">404</h2>
      <p className="text-xl text-muted-foreground mb-8">Page not found</p>
      <Link href="/">
        <Button>Return Home</Button>
      </Link>
    </div>
  );
}
```

#### 4. Add Disconnect Handling
**File**: `frontend/components/practice/VoiceVisualizer.tsx`

Add disconnect button in active state:

```typescript
import { DisconnectButton } from "@livekit/components-react";

// In active state, add:
<div className="flex gap-4">
  <DisconnectButton />
  <Button onClick={() => window.location.href = '/'}>
    End & Return Home
  </Button>
</div>
```

#### 5. Add Environment Variable Validation
**File**: `frontend/lib/env.ts` (new)

```typescript
function validateEnv() {
  const required = [
    'OPENAI_API_KEY',
    'LIVEKIT_API_KEY',
    'LIVEKIT_API_SECRET',
    'LIVEKIT_URL'
  ];

  const missing = required.filter(key => !process.env[key]);

  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }
}

validateEnv();
```

Import in `frontend/app/layout.tsx` to validate on startup.

#### 6. Add README with Setup Instructions
**File**: `frontend/README.md` (update)

```markdown
# Finesse - Voice Conversation Practice

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env.local
   ```

   Edit `.env.local` and add:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `LIVEKIT_API_KEY` - Your LiveKit API key
   - `LIVEKIT_API_SECRET` - Your LiveKit API secret
   - `LIVEKIT_URL` - Your LiveKit server URL

3. Run development server:
   ```bash
   npm run dev
   ```

4. Open http://localhost:3000

## Usage

1. On landing page, either:
   - Click a scenario card to jump straight to practice
   - Type a custom scenario in the hero input

2. On practice page:
   - Describe your scenario in the chat (2-step conversation)
   - Click "Begin Practice" when ready
   - Have a voice conversation with the AI character
   - Track your progress and view transcript

## TODO: Database Integration

The following features use mock data and need database integration:

- [ ] "Try these" scenario cards: Replace `MOCK_TRY_THESE_SCENARIOS` in `lib/mockData.ts`
- [ ] "Recent conversations": Replace `MOCK_RECENT_CONVERSATIONS` in `lib/mockData.ts`
- [ ] Save generated scenarios: Add POST endpoint to save to DB
- [ ] Save conversation history: Add POST endpoint after conversation ends
- [ ] User authentication: Add session management

See inline `// TODO: Connect to database` comments throughout the codebase.
```

### Success Criteria

#### Automated Verification:
- [ ] Full build succeeds: `cd frontend && npm run build`
- [ ] No TypeScript errors: `cd frontend && npx tsc --noEmit`
- [ ] No ESLint warnings: `cd frontend && npm run lint`
- [ ] Environment validation works: Start app without env vars fails gracefully

#### Manual Verification:
- [ ] Error boundaries catch and display errors nicely
- [ ] Loading states show during navigation
- [ ] 404 page displays for invalid routes
- [ ] Disconnect button ends conversation cleanly
- [ ] Returning home from practice page works
- [ ] No console errors in browser during normal flow
- [ ] All environment variables documented
- [ ] README instructions are clear and complete

**Implementation Note**: After completing this phase, perform end-to-end testing of all user flows before considering the implementation complete.

---

## Testing Strategy

### Automated Tests (Future Work)
- Unit tests for API endpoints with mock OpenAI responses
- Component tests for UI elements
- Integration tests for LiveKit connection flow
- E2E tests with Playwright for full user journeys

### Manual Testing Checklist

**Landing Page Flow**:
1. Load landing page, verify all cards display
2. Click "Try these" card → verify navigates to practice with scenario
3. Click "Recent conversation" card → verify navigates to practice
4. Type in hero input → verify navigates to practice with custom text
5. Verify responsive design on mobile/tablet/desktop

**Custom Scenario Flow**:
1. Navigate to `/practice?custom=test scenario`
2. Verify chat pre-fills with text
3. Type goal in chat
4. Verify API call generates scenario
5. Verify InfoSidebar shows generated details
6. Click "Begin Practice"
7. Verify LiveKit connection succeeds
8. Have 2-minute voice conversation
9. Verify goal progress updates
10. Verify transcript updates
11. Disconnect and return home

**Pre-selected Scenario Flow**:
1. Click "Practice interviewing" card on landing page
2. Verify skips chat and goes straight to "ready" state
3. Verify InfoSidebar shows pre-loaded scenario
4. Click "Begin Practice"
5. Verify conversation starts immediately
6. Complete conversation
7. Verify end state handling

**Error Cases**:
1. Trigger API error (invalid OpenAI key) → verify error message
2. Trigger LiveKit connection error → verify error handling
3. Navigate to invalid URL → verify 404 page
4. Disconnect mid-conversation → verify clean cleanup
5. Refresh during active conversation → verify state recovery

### Performance Targets
- Landing page load: < 2s
- Scenario generation: < 10s
- LiveKit connection: < 3s
- Voice latency: < 500ms
- First audio from agent: < 2s after connection

---

## Migration Notes

### From frontend-new to Next.js
- All `"use client"` directives added to ported components
- `react-router` `Link` replaced with Next.js `Link`
- `useNavigate` replaced with `useRouter().push()`
- `BrowserRouter` removed (Next.js app router handles routing)
- Import paths updated to use `@/` alias

### Preserving Existing Features
- LiveKit integration patterns remain unchanged
- RPC methods (checker, hint, postanalyzer) still available
- Goal progress tracking maintained
- Transcript view maintained
- All existing API endpoints functional

### Database Integration Path
1. Set up database schema (see data models in Phase 1)
2. Create database migration files
3. Implement data access layer (e.g., Prisma, Drizzle)
4. Replace mock data functions with DB queries
5. Add user authentication
6. Implement conversation saving
7. Add scenario management UI

---

## Performance Considerations

### Bundle Size
- Lazy load practice page components
- Code split LiveKit components
- Optimize shadcn-ui imports (import specific components)
- Remove unused dependencies from package.json

### API Optimization
- Cache generated scenarios for repeated use
- Implement request deduplication
- Add rate limiting to generation endpoint
- Consider streaming OpenAI responses

### Voice Quality
- Monitor LiveKit connection quality
- Implement adaptive bitrate
- Add reconnection logic
- Handle network interruptions gracefully

---

## References

- Original research: `thoughts/shared/research/2025-10-25-frontend-backend-integration-architecture.md`
- LiveKit patterns: `frontend/app/page.tsx` (existing implementation)
- UI components: `frontend-new/src/components/` (source material)
- Scenario format: `scenarios/smalltalk.json` (reference structure)
- Backend worker: `backend/livekitworker.py` (voice agent implementation)
