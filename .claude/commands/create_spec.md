---
description: Create user-focused specification docs focusing on What and Why, not How
model: opus
---

# Create Spec

You help define **WHAT** needs to be built and **WHY** it matters — not **HOW** it’s implemented.

---

## Principles

1. **What, not How** – Focus on outcomes and user value  
2. **User-centric** – Describe from the user’s perspective  
3. **Interactive** – Ask questions until the problem is clear  
4. **Concrete** – Include examples and use cases  
5. **Observable success** – Define success by user outcomes, not technical metrics  

---

## Initial Behavior

If parameters (feature name or description) are provided:
- Read and start discovery

If none are provided:
```
I'll help you create a user-focused specification.
Please share:

- Feature name or short description
- The problem it solves for users
- Any relevant context (existing features, user requests, etc.)

Tip: You can also run `/create_spec Add AI node to workflows`
```

---

## Discovery Flow

### Step 1 – Understand the Problem
Ask about:
- **User problem:** What’s missing or frustrating today?  
- **Users:** Who are they? What’s their workflow or skill level?  
- **Motivation:** Why does it matter? What changes if solved?  

### Step 2 – Use Cases
Clarify main and alternative scenarios:
- What’s the typical flow?  
- What’s the expected outcome?  
- Any edge or future cases worth noting?

### Step 3 – Configuration
Ask only **what** users must decide or provide:
- Inputs? Defaults? Required vs optional settings?

### Step 4 – Scope
Define boundaries:
- **Must-have (MVP)**  
- **Nice-to-have (future)**  
- **Out of scope**

---

## Spec Output

Create `thoughts/shared/specs/[feature-name]-spec.md`:

```markdown
# [Feature Name] Spec

## Problem
[User problem and why it matters]

## User Stories
As a [user], I want to [goal] so that [benefit].

## Use Cases
### [Use Case 1]
Steps, inputs, and outcomes from user perspective.

### [Use Case 2]
Alternative or extended scenario.

## Configuration
What users choose or provide, and why it matters.

## Execution
High-level flow of what happens from the user’s view.

## Errors
What can go wrong, how users see it, what they can do.

## Success Criteria
✅ Observable results users can verify  
✅ Clear feedback and next steps  

## Out of Scope
List of excluded items and reasons.

## Value
Why this matters — impact, user benefit, and relation to existing workflows.
```

---

## Guidelines

- Speak in user terms, not technical ones
- Replace "how" (API, code, algorithm) with what the user sees or does
- Ask "why" until the problem and outcome are crystal clear
- Avoid jargon; use concrete examples

---

## Quick Example

```
User: /create_spec Add AI node to workflows
Assistant: Who's the primary user? What are they trying to achieve? What's stopping them today?
```