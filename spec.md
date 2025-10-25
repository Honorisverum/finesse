
## **Product Spec: Interactive Voice Case Interviewer (v1.1)**

### **1. Vision & Objective**

We are building a voice-first simulation platform to provide a realistic, adaptive, and scalable consulting case interview experience. The system must guide a candidate through a pre-defined case, probing for analysis and adapting to their reasoning, while ensuring all key analytical milestones of the case are met.

### **2. User Experience Tenets**

* **Guided, Not Rigid:** The user must follow a pre-determined analytical path (e.g., Framework -> Analysis -> Recommendation) but have the flexibility to reason and explore within each step. The system must use probes to nudge a user back on track, not just hard-fail them.
* **Adaptive & Intelligent:** The system must evaluate the *intent and process* of the user's analysis, not just a final numerical answer. It must be able to identify which step in a logical chain a user missed and probe them on that specific point.
* **Seamless & Immersive:** State transitions between case parts, including the display of on-screen Exhibits, must be instantaneous and synchronized with the AI's voice to create a single, uninterrupted session.

### **3. Core Architecture**

The architecture must enforce a strict **separation of configuration from logic**.

1.  **Case Definition (Configuration):** A static, structured data file (e.g., JSON/YAML) that defines all case-specific data. This includes all prompts, exhibit references, and the AI's objectives for each part of the case.
2.  **Caseflow Engine (State Machine):** A service that manages the application's current state. It is responsible for loading the `Case Definition` and progressing through its "Parts" in a defined order.
3.  **Voice Agent (AI Service):** The service handling all STT, TTS, and LLM-based generation. Its runtime instructions (system prompt) are **dynamically set** by the Caseflow Engine based on the application's current state.

### **4. Component Requirements**

#### **4.1. Case Definition (Configuration File)**
This is a static data model that defines a single case. It will be authored by a PM and ingested by the Caseflow Engine. It must contain an ordered list of "Parts."

Each **Part** object in the list must define:
* `part_id`: A unique identifier (e.g., `part_3_market_sizing`).
* `ai_opening_prompt`: The text the AI will speak to initiate this part.
* `exhibit_to_display`: The URI or filename of the image to be displayed, or `null`.
* `part_instructions`: This is the **dynamic system prompt** for the Voice Agent. It is a natural language-based set of objectives, rules, and guidance for the AI *for this specific part*.

**Example `part_instructions` for "DiamondLux - Market Sizing":**
> "Your objective is to guide the candidate to calculate the addressable market for *physical* stores. The key analytical steps are [Millennials -> Unmarried -> Engaged -> Ring Price -> Physical %]. The target is ~$108M.
>
> 1.  Do not perform the calculation. Your role is to ensure the candidate builds and executes the logic.
> 2.  If the candidate misses a step, probe them on that specific step (e.g., 'That's the total market, but what about the physical store preference?').
> 3.  If their final number is reasonably close to the target (e.g., $100M-$120M), accept it.
> 4.  After a reasonable TAM is established, you must ask the follow-up question: 'Given that, what market share would a $5M store need?'
> 5.  Once the market share question is answered, you must output the `[PART_COMPLETE]` token."

#### **4.2. Caseflow Engine (State Machine)**
This service is responsible for runtime progression.
* **Initialization:** Loads the `Case Definition` file.
* **State Management:** Maintains the `current_part` (e.g., `part_3_market_sizing`).
* **Transition:** On receipt of a `[PART_COMPLETE]` token from the Voice Agent, it must:
    1.  Advance its internal state to the *next* Part in the `Case Definition` list.
    2.  Immediately push the `part_instructions`, `ai_opening_prompt`, and `exhibit_to_display` for the new Part to the Voice Agent and Frontend.

#### **4.3. Voice Agent (AI Service)**
* Must support real-time, low-latency STT/TTS.
* Must support **dynamic, mid-conversation updates to its system prompt**. When the Caseflow Engine transitions to a new part, the agent's old `part_instructions` are discarded and replaced instantly.
* Must execute its current `part_instructions` to guide the user.
* Must reliably emit the `[PART_COMPLETE]` token to the Caseflow Engine *only* when the objectives in its current instructions are met.

### **5. Core System Flow (Example: Transition from Part 2 to Part 3)**

1.  **State:** `Caseflow Engine` is in state `part_2_city_selection`. The `Voice Agent`'s `part_instructions` are focused on comparing cities.
2.  **User (STT):** "...so I'd choose Nashville due to its high growth."
3.  **Voice Agent (LLM):** The user's choice fulfills its current `part_instructions`. It generates its scripted pivot response and appends the transition token.
    * **Agent Output:** "Understood. Management was intrigued... let's size the market for Austin. `[PART_COMPLETE]`"
4.  **Caseflow Engine:**
    * Detects `[PART_COMPLETE]`.
    * Advances its state to `part_3_market_sizing`.
    * Loads the `part_instructions`, `ai_opening_prompt`, and `exhibit_2_austin_data.jpg` for Part 3.
5.  **System Execution (Simultaneous):**
    * **Frontend:** Receives a command to display `exhibit_2_austin_data.jpg`.
    * **Voice Agent:** Its system prompt is instantly replaced with the new `part_instructions` for Part 3. It then executes its new `ai_opening_prompt`.
    * **Voice Agent (TTS):** "I've pulled up the market data for Austin. Can you see that?"
6.  **State:** The system is now fully in `part_3_market_sizing`. The Voice Agent is operating under the new, constrained instructions.

### **6. Key Acceptance Criteria**

* **AC 1: Adaptive Probing:** The system must demonstrate it can identify a *specific* missed logical step (e.g., the "physical store %") and generate a natural-language probe to correct the user.
* **AC 2: Graceful Validation:** The system must accept a quantitative answer that is "in the ballpark" (as defined in its `part_instructions`) and proceed, rather than getting stuck on an exact numerical match.
* **AC 3: Seamless State Transition:** The switch between case parts (both the exhibit change and the AI's change in topic) must be perceived by the user as a single, seamless event.
* **AC 4: Scoped Logic:** The AI must be verifiably constrained by its current `part_instructions`. It must not be possible for the user to "trick" the AI into discussing profitability (Part 4) while in the market sizing (Part 3) section.