# 🌍 InviGrid Travel Assistant

A multi-lingual AI travel assistant built with **LangChain**, **FastAPI**, and **Next.js**. Supports flight, hotel, train, and bus searches with a complete booking workflow.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![Next.js](https://img.shields.io/badge/Next.js-16-black) ![LangChain](https://img.shields.io/badge/LangChain-0.3-green)

## ✨ Features

- 🗣️ **Multi-lingual Support** - Automatic language detection and translation (Hindi, Tamil, Telugu, etc.)
- ✈️ **Flight Search** - Search and book flights across major Indian cities
- 🏨 **Hotel Search** - Find accommodations with ratings and amenities
- 🚆 **Train/Bus Search** - IRCTC-style train and bus booking
- 📝 **Complete Booking Flow** - Multi-step booking with confirmation
- 💬 **Real-time Chat** - WebSocket-based chat with markdown rendering

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Next.js Frontend                          │
│              (React + Framer Motion + shadcn/ui)                │
└─────────────────────────────────────────────────────────────────┘
                              │ WebSocket / REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (api.py)                     │
│                   Central Memory Management                     │
└─────────────────────────────────────────────────────────────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
┌─────────────┐      ┌────────────────┐     ┌────────────────┐
│ Translation │      │  Travel Agent  │     │ Booking Agent  │
│   Agent     │      │                │     │                │
│             │      │ • LLM + Tools  │     │ • LLM + Memory │
│ • Detect    │      │ • Structured   │     │ • Multi-step   │
│ • Translate │      │   JSON output  │     │   workflow     │
└─────────────┘      └────────────────┘     └────────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │   SQLite Database  │
                    │ (Flights, Hotels,  │
                    │  Trains, Buses)    │
                    └────────────────────┘
```

## 📁 Project Structure

```
├── agents/                 # AI Agents
│   ├── memory.py          # Central memory management
│   ├── translation_agent.py
│   ├── travel_agent.py
│   ├── booking_agent.py
│   ├── router.py          # Intent classification
│   └── llm_engine.py      # LLM configuration
│
├── tools/                  # LangChain Tools
│   ├── flights.py
│   ├── hotels.py
│   ├── trains.py
│   └── recommendations.py
│
├── app/                    # Application Layer
│   ├── api.py             # FastAPI backend
│   └── main.py            # Streamlit UI (alternative)
│
├── data/                   # Database Layer
│   ├── database.py        # SQLAlchemy models
│   ├── init_db.py         # Database seeding
│   └── travel.db          # SQLite database
│
├── validation/             # Input Validation
│   └── input_guards.py    # Guardrails
│
├── frontend/               # Next.js Frontend
│   ├── app/
│   ├── components/
│   └── lib/
│
└── tests/                  # Test Suite
    └── test_agents.py
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Groq API Key (free at [console.groq.com](https://console.groq.com))

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/invigrid-travel-assistant.git
cd invigrid-travel-assistant

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Initialize database (auto-seeds with mock data)
python -c "from data.init_db import init_db; init_db()"

# Start the backend
uvicorn app.api:app --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and start chatting!

## 🔧 Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
# Optional: Google AI fallback
GOOGLE_API_KEY=your_google_api_key
```

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Test specific agent
pytest tests/test_agents.py::test_travel_agent -v
```

## 📖 Usage Examples

### Search Flights
```
User: "Find flights from Mumbai to Delhi tomorrow"
Assistant: Shows available flights with prices
```

### Book in Hindi
```
User: "मुझे कल मुंबई से दिल्ली के लिए फ्लाइट बुक करनी है"
Assistant: Responds in Hindi with flight options
```

### Complete Booking
```
User: "Book the cheapest one"
→ Form appears for passenger details
→ Payment form (simulated)
→ Confirmation with booking ID
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgements

- [LangChain](https://langchain.com) for the agent framework
- [Groq](https://groq.com) for fast LLM inference
- [shadcn/ui](https://ui.shadcn.com) for beautiful components
