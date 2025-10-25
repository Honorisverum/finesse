import { ScenarioCard, ConversationRecord, ScenarioData } from "@/types/database";

/**
 * Mock Data Service
 *
 * This file contains mock data for the application. In a production environment,
 * these functions should be replaced with actual database queries.
 *
 * TODO: Replace all mock data with database queries
 */

/**
 * Mock scenario cards for the "Try these" section on the landing page
 * TODO: Replace with database query: SELECT * FROM scenario_cards WHERE featured = true
 */
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
  {
    id: "networking-event",
    title: "Networking at events",
    description: "Master the art of making meaningful connections at professional events",
    icon: "🤝",
    messageCount: "1.8k"
  },
  {
    id: "performance-review",
    title: "Performance review",
    description: "Navigate your annual review and advocate for your achievements",
    icon: "📊",
    messageCount: "2.3k"
  },
  {
    id: "cold-calling",
    title: "Sales cold calling",
    description: "Develop confidence making cold calls and handling objections",
    icon: "📞",
    messageCount: "4.1k"
  },
  {
    id: "public-speaking",
    title: "Public speaking",
    description: "Practice delivering presentations and speeches with confidence",
    icon: "🎤",
    messageCount: "3.9k"
  }
];

/**
 * Mock recent conversations for the "Recent conversations" section
 * TODO: Replace with database query: SELECT * FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT 8
 */
export const MOCK_RECENT_CONVERSATIONS: ConversationRecord[] = [
  {
    id: "conv-001",
    title: "VC Pitch Practice",
    description: "Practiced pitching startup idea to skeptical venture capitalist",
    icon: "🚀",
    messageCount: "24 messages",
    timestamp: new Date("2025-10-24T14:30:00"),
    scenarioId: "pitch-to-investors"
  },
  {
    id: "conv-002",
    title: "Salary Negotiation",
    description: "Negotiated a raise with a tough manager character",
    icon: "💵",
    messageCount: "18 messages",
    timestamp: new Date("2025-10-23T09:15:00"),
    scenarioId: "negotiate-salary"
  },
  {
    id: "conv-003",
    title: "Job Interview Prep",
    description: "Mock interview with challenging technical questions",
    icon: "💼",
    messageCount: "31 messages",
    timestamp: new Date("2025-10-22T16:45:00"),
    scenarioId: "practice-interviewing"
  },
  {
    id: "conv-004",
    title: "Difficult Team Discussion",
    description: "Practiced delivering critical feedback to underperforming teammate",
    icon: "⚠️",
    messageCount: "22 messages",
    timestamp: new Date("2025-10-21T11:20:00"),
    scenarioId: "difficult-conversations"
  },
  {
    id: "conv-005",
    title: "Conference Networking",
    description: "Simulated networking conversations at a tech conference",
    icon: "🌐",
    messageCount: "15 messages",
    timestamp: new Date("2025-10-20T13:00:00"),
    scenarioId: "networking-event"
  },
  {
    id: "conv-006",
    title: "Annual Review Prep",
    description: "Prepared for performance review discussion with manager",
    icon: "📈",
    messageCount: "27 messages",
    timestamp: new Date("2025-10-19T10:30:00"),
    scenarioId: "performance-review"
  },
  {
    id: "conv-007",
    title: "Sales Call Practice",
    description: "Cold calling simulation with various objection scenarios",
    icon: "☎️",
    messageCount: "19 messages",
    timestamp: new Date("2025-10-18T15:45:00"),
    scenarioId: "cold-calling"
  },
  {
    id: "conv-008",
    title: "Keynote Rehearsal",
    description: "Practiced delivering a keynote speech to a large audience",
    icon: "🎭",
    messageCount: "12 messages",
    timestamp: new Date("2025-10-17T14:00:00"),
    scenarioId: "public-speaking"
  }
];

/**
 * Retrieve a scenario by its ID
 * TODO: Replace with database query: SELECT * FROM scenarios WHERE id = ?
 *
 * @param id - The scenario ID
 * @returns The scenario data or null if not found
 */
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
    elevenlabs_voice_id: "21m00Tcm4TlvDq8ikWAM" // Default ElevenLabs voice
  };
}
