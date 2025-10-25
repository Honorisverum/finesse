/**
 * Database Type Definitions
 *
 * These types define the data structures for the voice scenario builder.
 * They are designed to be database-agnostic and will support future
 * integration with a persistent database layer.
 */

/**
 * Scenario card shown on landing page
 * Represents a practice scenario that users can select
 */
export type ScenarioCard = {
  id: string;
  title: string;
  description: string;
  icon: string;
  messageCount: string; // e.g., "2.7k"
};

/**
 * Full scenario data for voice practice
 * Contains all information needed to run a voice conversation
 */
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

/**
 * Recent conversation record
 * Represents a past conversation for the "Recent conversations" section
 */
export type ConversationRecord = {
  id: string;
  title: string;
  description: string;
  icon: string;
  messageCount: string;
  timestamp: Date;
  scenarioId: string;
};

/**
 * Request format for scenario generation API
 * Used when calling POST /api/generate-scenario
 */
export type GenerateScenarioRequest = {
  scenario: string; // User's description
  goal: string;     // User's goal
};

/**
 * Response format for scenario generation API
 * Returned by POST /api/generate-scenario
 */
export type GenerateScenarioResponse = {
  scenarioData: ScenarioData;
};
