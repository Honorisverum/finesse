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
