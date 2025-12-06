# 🎥 Demo Video Script: InviGrid Travel Assistant

This script guides you through recording a 5-10 minute demo video showcasing the key capabilities of the InviGrid Travel Assistant.

> [!NOTE]
> Scenarios have been adapted to use **supported Indian cities** (Mumbai, Delhi, Goa, etc.) to ensure the live backend returns real results.

---

## 🎬 Setup

1. **Clear Database**: `python -c "from agents.memory import clear_memory; clear_memory('default')"` (Optional, or just refresh page)
2. **Open Browser**: `http://localhost:3000`
3. **Open Terminal**: Show `uvicorn` logs side-by-side if possible to show "Thought Process"

---

##  Scenario 1: Happy Path (French) 🇫🇷

**Goal**: Show translation + search + booking flow.

1. **User**: Type (or copy-paste):
   `Je veux aller à Goa la semaine prochaine`
   *(English: I want to go to Goa next week)*

2. **Wait for response**:
   - System detects French 🇫🇷
   - Shows flight/train options to Goa

3. **User**: Type:
   `Réserve le vol du mardi`
   *(English: Reserve the Tuesday flight)*

4. **Action**:
   - Click/Type details in the **Booking Form**
   - Complete the **Payment Form** (enter `1234`)
   - Show the **Confirmation Card**

---

## Scenario 2: Ambiguous Input (Japanese) 🇯🇵

**Goal**: Show clarification questions.

1. **Click**: "New Chat" or refresh.
2. **User**: Type:
   `来週旅行したい`
   *(English: I want to travel next week)*

3. **Wait for response**:
   - Agent should ask: "Where do you want to go?" or "From where?" in Japanese.

---

## Scenario 3: Language Mixing (Spanish + English) 🇪🇸

**Goal**: Show robust entity extraction.

1. **User**: Type:
   `Quiero un hotel en Mumbai cerca de Gateway of India`
   *(Spanish syntax + English entities)*

2. **Wait for response**:
   - System detects Spanish intent
   - Extracts "Mumbai" and "Gateway of India"
   - Shows hotels in Mumbai 🏨

---

## Scenario 4: Error Recovery (English) 🇺🇸

**Goal**: Show graceful handling of missing context.

1. **Click**: "New Chat" or refresh.
2. **User**: Type:
   `Book the cheapest flight`

3. **Wait for response**:
   - Agent checks memory → Empty
   - **Response**: "I don't have any flight options in our conversation yet. Where would you like to fly from and to?"

---

## Scenario 5: Context Switching 🔄

**Goal**: Show memory management.

1. **User**: Type:
   `Show me flights to Delhi`

2. **Wait for response**:
   - Shows flight results ✈️

3. **User**: Type:
   `Actually, what about trains from Pune to Mumbai?`

4. **Wait for response**:
   - System switches context
   - Shows **Train** results 🚆 (clearing previous flight focus)

---

## 🌟 Bonus: Full Booking Flow (Hindi) 🇮🇳

**Goal**: Show end-to-end native language support.

1. **User**:
   `मुझे मुंबई से दिल्ली के लिए सबसे सस्ती फ्लाइट चाहिए`
   *(I want the cheapest flight from Mumbai to Delhi)*

2. **Agent checks database** and returns options in Hindi.

3. **User**:
   `पहली वाली बुक करो`
   *(Book the first one)*

4. **Flow**:
   - Fill Booking Form (Name: "Rahul", Email: "rahul@test.com")
   - Fill Payment (1234)
   - **Success**: "आपका टिकट बुक हो गया है!" (Your ticket is booked!)
