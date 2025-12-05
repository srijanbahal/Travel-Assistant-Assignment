# Multi-Lingual Travel Assistant

An intelligent travel assistant that helps users who don't speak the local language. This system handles the complete journey from understanding what the user wants (in any language) to providing relevant travel information and bookings.

## Features

- **Multi-Lingual Support**: Automatically detects and translates between English and Hindi, Tamil, Bengali, Marathi, etc.
- **Travel Services**: Flight, Hotel, and Train search capabilities.
- **Booking Workflow**: Simulated booking process with confirmation generation.
- **Agentic Architecture**: Powered by LangChain and LangGraph for robust orchestration.

## Architecture

The system consists of three main agents:
1.  **Translation Agent**: Handles language detection and translation.
2.  **Travel Services Agent**: Processes queries and fetches travel data.
3.  **Booking Agent**: Manages the booking state machine.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd Invigrid
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**:
    Copy `.env.example` to `.env` and add your API keys.
    ```bash
    cp .env.example .env
    ```

5.  **Run the Application**:
    ```bash
    streamlit run app/main.py
    ```

## Tech Stack

- **Frontend**: Streamlit
- **Orchestration**: LangGraph, LangChain
- **LLM**: Google Gemini / Llama 3.1 (Groq)
- **Language**: Python 3.10+
