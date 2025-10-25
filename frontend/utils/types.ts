export type Skill = {
  name: string;
  scenarios: Scenario[];
};

export interface Scenario {
  id: string;
  name: string;
  description: string;
  goal: string;
  opening: string;
  character: string[];
  negprompt: string[];
  skill: string;
  botname: string;
  botgender: string;
  voice_description: string;
  elevenlabs_voice_id: string;
  [key: string]: any;  // Для дополнительных полей
}

export type HintData = {
  hint: string;
  category: string;
};

export type GoalProgressData = {
  is_goal_complete: boolean;
  progress_towards_goal: number;
  previous_progress_towards_goal: number;
  is_bad_ending_triggered: boolean;
  CTA: string | null;
}; 