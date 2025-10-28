# Quick Start Guide - State Machine Learning

## ⚡ 3 Steps to Get Started

### Step 1: Run the Python Example (2 minutes)

```bash
cd backend
python3 simple_state_machine_example.py
```

**What you'll see**: A printout of the state machine structure and an example conversation flow.

**What to learn**: How states connect to each other.

---

### Step 2: View the Interactive Demo (5 minutes)

```bash
cd frontend
npm run dev
```

Then open: **http://localhost:3000/demo**

**What you'll see**: An interactive visualization where you can:
- Click through example conversation paths
- See states change in real-time
- View hints and transition conditions

**What to learn**: How conversations flow through states.

---

### Step 3: Read the Real Implementation (10 minutes)

Open this file: `backend/langraph/agentic.py`

Look at lines **22-94** to see the production state machine.

**What to learn**: How real scenarios are structured.

---

## 🎯 What to Do Next

Choose your path:

### Path A: Modify Examples (Beginner)
1. Open `backend/simple_state_machine_example.py`
2. Add a new state between SharedInterest and SUCCESS
3. Run it and see the changes

### Path B: Create New Scenario (Intermediate)
1. Copy `simple_state_machine_example.py` to `my_scenario.py`
2. Replace all states with your own scenario (e.g., "ordering at restaurant")
3. Test different conversation paths

### Path C: Build React Version (Advanced)
1. Open `frontend/examples/SimpleStateMachine.tsx`
2. Add your custom scenario from Path B
3. View it at http://localhost:3000/demo

---

## 📚 Full Guide

For detailed explanations and exercises, see: **[WALKTHROUGH.md](WALKTHROUGH.md)**

---

## 🆘 Stuck?

**Q: Where is the state machine code?**
A: Backend: `backend/langraph/agentic.py` | Frontend: `frontend/examples/SimpleStateMachine.tsx`

**Q: How do I see the demo?**
A: Run `npm run dev` in `frontend/` folder, then go to http://localhost:3000/demo

**Q: How do I modify a state?**
A: Edit the `SIMPLE_STATES` dictionary in `simple_state_machine_example.py`

**Q: Can I create my own scenario?**
A: Yes! Copy the example file and modify the SIMPLE_STATES dictionary.

---

## 📖 Files You Need to Know

| File | Purpose | When to use |
|------|---------|-------------|
| `QUICKSTART.md` | This file - get started fast | First time |
| `WALKTHROUGH.md` | Detailed guide with exercises | Learning |
| `backend/simple_state_machine_example.py` | Python learning example | Experimenting |
| `backend/langraph/agentic.py` | Real production code | Understanding the app |
| `frontend/examples/SimpleStateMachine.tsx` | Interactive demo | Visualizing |
| `frontend/app/demo/page.tsx` | Demo page | Viewing the demo |

---

## ⏱️ Time Investment

- **10 minutes**: Run examples, understand basics
- **30 minutes**: Modify examples, create simple scenario
- **1 hour**: Build custom scenario, understand full flow
- **2+ hours**: Master the system, build production scenarios

Start with 10 minutes and see where it takes you!
