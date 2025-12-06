# Architecture & Design Decisions

This document explains the architectural choices, agent communication protocol, state management approach, error handling strategies, and trade-offs made in the InviGrid Travel Assistant.

## Table of Contents
1. [System Overview](#system-overview)
2. [Agent Communication Protocol](#agent-communication-protocol)
3. [State Management](#state-management)
4. [Error Handling Strategy](#error-handling-strategy)
5. [Trade-offs & Decisions](#trade-offs--decisions)

---

## System Overview

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        Next.js Frontend                                  │  │
│  │  • React Components (Chat, Booking, Search Results)                     │  │
│  │  • Framer Motion Animations                                             │  │
│  │  • WebSocket Client for real-time updates                               │  │
│  │  • REST fallback for reliability                                        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ WebSocket (primary) / REST (fallback)
                                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                        FastAPI Backend                                   │  │
│  │  • Session management                                                   │  │
│  │  • Central Memory coordination                                          │  │
│  │  • Agent orchestration                                                  │  │
│  │  • Response formatting                                                  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                         │
│              ┌──────────────────────┼──────────────────────┐                  │
│              ▼                      ▼                      ▼                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │   Translation   │    │   Router Agent  │    │  Memory Manager │           │
│  │     Agent       │    │                 │    │ (ConversationM- │           │
│  │                 │    │  • LLM-based    │    │  emory class)   │           │
│  │ • Detect lang   │    │  • Fallback KW  │    │                 │           │
│  │ • Translate I/O │    │  • Intent →     │    │ • Messages      │           │
│  │ • Update memory │    │    travel/book  │    │ • Search state  │           │
│  └─────────────────┘    └─────────────────┘    │ • Booking state │           │
│                                                 │ • Language prefs│           │
│                                                 └─────────────────┘           │
└───────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                                 ▼
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│          TRAVEL AGENT            │  │         BOOKING AGENT            │
│                                  │  │                                  │
│  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │
│  │     LLM with Structured    │  │  │  │   LLM with Structured      │  │
│  │        JSON Output         │  │  │  │       JSON Output          │  │
│  │                            │  │  │  │                            │  │
│  │  Input: User query +       │  │  │  │  Input: User message +     │  │
│  │         Memory context     │  │  │  │         Memory context     │  │
│  │                            │  │  │  │                            │  │
│  │  Output:                   │  │  │  │  Output:                   │  │
│  │  {"action": "search",      │  │  │  │  {"action": "select",      │  │
│  │   "tool": "search_flights",│  │  │  │   "item_index": 1,         │  │
│  │   "params": {...}}         │  │  │  │   "response": "..."}       │  │
│  └────────────────────────────┘  │  │  └────────────────────────────┘  │
│              │                   │  │              │                   │
│              ▼                   │  │              ▼                   │
│  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │
│  │      Tool Execution        │  │  │  │    State Machine Logic     │  │
│  │  • search_flights.invoke() │  │  │  │  • confirm → details →     │  │
│  │  • search_hotels.invoke()  │  │  │  │    payment → complete      │  │
│  │  • search_trains.invoke()  │  │  │  │  • Extract user details    │  │
│  │  • get_attractions.invoke()│  │  │  │  • Generate confirmation   │  │
│  └────────────────────────────┘  │  │  └────────────────────────────┘  │
└──────────────────────────────────┘  └──────────────────────────────────┘
                    │                                 │
                    └────────────────┬────────────────┘
                                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                     SQLite + SQLAlchemy                                  │  │
│  │  • Flights (10k+ records)                                               │  │
│  │  • Hotels (30 records per city)                                         │  │
│  │  • Trains, Buses                                                        │  │
│  │  • Chat History                                                         │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Communication Protocol

### Message Flow

```
User Message
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. TRANSLATION INPUT                                                        │
│    • Input: Raw user message                                                │
│    • Process: Detect language, translate to English                         │
│    • Output: English text + updated memory.user_language                    │
│    • Side Effect: Updates memory.locale_preferences                         │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. INTENT ROUTING                                                           │
│    • Input: English message + Memory context                                │
│    • Process: LLM classification → "travel" or "booking"                    │
│    • Fast-path: If booking_stage is active, route to booking                │
│    • Fallback: Keyword matching if LLM fails                                │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ├──────────────────────────────────┬──────────────────────────────────────┐
    ▼                                  ▼                                      │
┌──────────────────────┐    ┌───────────────────────┐                         │
│ 3A. TRAVEL AGENT     │    │ 3B. BOOKING AGENT     │                         │
│                      │    │                       │                         │
│ LLM → JSON Decision: │    │ LLM → JSON Decision:  │                         │
│ • action: search     │    │ • action: select      │                         │
│ • tool: search_*     │    │ • item_index: N       │                         │
│ • params: {...}      │    │ • action: confirm     │                         │
│ • response: "..."    │    │ • action: details     │                         │
│                      │    │ • action: payment     │                         │
│ Execute tool.invoke()│    │                       │                         │
│ Format results       │    │ Update booking_state  │                         │
│ Update memory        │    │ Update memory         │                         │
└──────────────────────┘    └───────────────────────┘                         │
    │                                  │                                      │
    └──────────────────────────────────┴──────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. TRANSLATION OUTPUT                                                       │
│    • Input: English response                                                │
│    • Process: Translate to memory.user_language                             │
│    • Output: Localized response                                             │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
User Response (with search results / booking state)
```

### Structured JSON Protocol

Instead of using `llm.bind_tools()` (which had issues with Groq), agents return structured JSON:

**Travel Agent Output Format:**
```json
{
  "action": "search" | "respond",
  "tool": "search_flights" | "search_hotels" | "search_trains" | ...,
  "params": {
    "origin": "Mumbai",
    "destination": "Delhi",
    "date": "2025-01-15"
  },
  "response": "Optional direct response text"
}
```

**Booking Agent Output Format:**
```json
{
  "action": "select" | "confirm" | "details" | "payment" | "cancel" | "unclear",
  "item_index": 1,
  "extracted_details": {
    "name": "John Doe",
    "email": "john@email.com",
    "phone": "+91 98765 43210",
    "card_digits": "1234"
  },
  "response": "User-facing message"
}
```

---

## State Management

### Central Memory Architecture

The `ConversationMemory` class (in `agents/memory.py`) serves as the single source of truth:

```python
@dataclass
class ConversationMemory:
    session_id: str
    messages: List[Dict]           # Chat history
    summary: Optional[str]         # Compressed history
    search_results: List[Dict]     # Last search results ← CRITICAL
    search_type: str               # flight/hotel/train/bus
    booking_state: Dict            # stage, selected_item, user_details
    user_language: str             # Detected language
    locale_preferences: Dict       # Currency, date format
    created_at: datetime
    last_updated: datetime
```

### Why Central Memory?

**Problem with LangGraph state passing:**
- State fields were being overwritten during node transitions
- `last_search_results` would disappear when transitioning to booking
- Debugging was difficult due to hidden state flows

**Solution:**
- Each agent receives the full memory object
- Agents read from memory at start
- Agents write updates to memory at end
- API layer owns the memory lifecycle

### Memory Lifecycle

```
Session Start
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  get_memory(session_id)                                                 │
│  • Creates new ConversationMemory if not exists                        │
│  • Returns existing memory if found                                    │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Agent reads memory.search_results, memory.booking_state, etc.         │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Agent performs action                                                  │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  memory.update_search_results(results, type)                           │
│  memory.update_booking_state(state)                                    │
│  memory.add_message(role, content)                                     │
└─────────────────────────────────────────────────────────────────────────┘
    │
    ▼
Session End / Next Request
```

---

## Error Handling Strategy

### Multi-Layer Error Handling

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Input Validation (Guardrails)                                  │
│ • Profanity filter                                                      │
│ • Injection detection                                                   │
│ • Length limits                                                         │
│ • Returns sanitized input or rejection message                          │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Agent-Level Error Handling                                     │
│ • Try-catch around LLM calls                                            │
│ • Fallback responses on failure                                         │
│ • JSON parsing with multiple fallbacks                                  │
│ • Logging via agents/logger.py                                          │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 3: API-Level Error Handling                                       │
│ • HTTP error codes (400, 500)                                           │
│ • WebSocket error messages                                              │
│ • Session recovery                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### JSON Parsing Fallback Chain

```python
def _parse_json_response(text: str) -> Dict:
    # 1. Try direct JSON parse
    try:
        return json.loads(text)
    except:
        pass
    
    # 2. Try extracting JSON from text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    
    # 3. Try extracting response field
    response_match = re.search(r'"response"\s*:\s*"([^"]+)"', text)
    if response_match:
        return {"action": "respond", "response": response_match.group(1)}
    
    # 4. Clean JSON artifacts and return as response
    clean_text = re.sub(r'\{[^}]*\}', '', text).strip()
    if clean_text:
        return {"action": "respond", "response": clean_text}
    
    # 5. Ultimate fallback
    return {"action": "respond", "response": "How can I help?"}
```

---

## Trade-offs & Decisions

### Decision 1: Central Memory vs LangGraph State

| Approach | Pros | Cons |
|----------|------|------|
| **LangGraph State** | Built-in state management, declarative flow | State loss between nodes, debugging difficulty |
| **Central Memory** ✅ | Full control, guaranteed persistence, easy debugging | More code, manual state updates |

**Decision:** Central Memory
**Rationale:** Context loss was causing critical booking failures. Central memory guarantees search results persist.

---

### Decision 2: Structured JSON vs bind_tools()

| Approach | Pros | Cons |
|----------|------|------|
| **bind_tools()** | Native LangChain support, automatic parsing | Groq compatibility issues, less control |
| **Structured JSON** ✅ | Full control, works with any LLM, predictable | Manual parsing needed, prompt engineering |

**Decision:** Structured JSON output
**Rationale:** Groq's tool calling was unreliable. Manual JSON parsing gives us fallback options.

---

### Decision 3: SQLite vs Vector DB for Search

| Approach | Pros | Cons |
|----------|------|------|
| **SQLite** ✅ | Fast, structured queries, exact matching | No semantic search, rigid schema |
| **Vector DB** | Semantic search, flexible queries | Slower, overkill for structured data |

**Decision:** SQLite for travel data
**Rationale:** Flight/hotel data is highly structured. SQL with fuzzy matching covers 95% of cases. Vector DB would be beneficial for recommendations and cultural tips.

---

### Decision 4: WebSocket vs REST

| Approach | Pros | Cons |
|----------|------|------|
| **WebSocket** ✅ | Real-time, typing indicators, lower latency | Connection management complexity |
| **REST** ✅ | Simple, reliable, stateless | Higher latency, no real-time updates |

**Decision:** Both (WebSocket primary, REST fallback)
**Rationale:** Best user experience with WebSocket, but REST ensures reliability when WebSocket fails.

---

### Decision 5: Stateless Translation Agent

| Approach | Pros | Cons |
|----------|------|------|
| **Stateful Translation** | Can use context for better translation | Complexity, context management |
| **Stateless Translation** ✅ | Simple, fast, focused | Less context-aware |

**Decision:** Stateless translation that updates memory
**Rationale:** Translation doesn't need conversation history. It only needs to know the target language, which it reads/writes to memory.

---

## Future Improvements

1. **Vector DB for Recommendations** - Add semantic search for "romantic getaway", "beach vacation"
2. **Conversation Summarization** - Compress long conversations to maintain context
3. **Streaming Responses** - Token-by-token streaming for better UX
4. **Multi-Provider Fallback** - Auto-switch between Groq, Google, OpenAI
5. **Caching Layer** - Redis for frequently searched routes
6. **Real Payment Integration** - Stripe/Razorpay integration

---

## Monitoring & Observability

### Logging

```python
from agents.logger import log_llm_call, log_tool_call, log_error, log_agent_handoff

# Usage
log_llm_call("travel_agent", message[:50])
log_tool_call("TravelAgent", "search_flights", params)
log_agent_handoff("Router", "TravelAgent", message, context)
log_error("BookingAgent", "Payment failed: insufficient funds")
```

### Log Output Format
```
08:22:54 | INFO | [LLM] travel_agent: "Find flights from Mumbai..."
08:22:54 | INFO | [TOOL] TravelAgent(search_flights) → {'origin': 'Mumbai', ...}
08:22:54 | INFO | [HANDOFF] Router → TravelAgent
08:22:54 | ERROR | [ERROR] BookingAgent: Tool execution failed
```

---

## Conclusion

This architecture prioritizes:
1. **Reliability** - Central memory ensures no context loss
2. **Maintainability** - Clear agent boundaries, structured protocols
3. **Flexibility** - JSON-based communication decouples agents from LLM specifics
4. **User Experience** - Real-time updates, multi-language support, complete booking flow
