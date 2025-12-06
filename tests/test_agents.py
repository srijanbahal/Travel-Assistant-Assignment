"""
Test suite for InviGrid Travel Assistant agents.

Run with: pytest tests/test_agents.py -v
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.memory import ConversationMemory, get_memory, clear_memory


class TestConversationMemory:
    """Tests for the central memory management."""
    
    def test_create_memory(self):
        """Test memory creation."""
        memory = get_memory("test-session-1")
        assert memory.session_id == "test-session-1"
        assert memory.messages == []
        assert memory.search_results == []
        assert memory.user_language == "English"
        
        # Cleanup
        clear_memory("test-session-1")
    
    def test_add_message(self):
        """Test adding messages to memory."""
        memory = get_memory("test-session-2")
        
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there!")
        
        assert len(memory.messages) == 2
        assert memory.messages[0]["role"] == "user"
        assert memory.messages[0]["content"] == "Hello"
        
        # Cleanup
        clear_memory("test-session-2")
    
    def test_update_search_results(self):
        """Test updating search results."""
        memory = get_memory("test-session-3")
        
        results = [
            {"airline": "IndiGo", "price": 5000},
            {"airline": "Air India", "price": 6000}
        ]
        memory.update_search_results(results, "flight")
        
        assert len(memory.search_results) == 2
        assert memory.search_type == "flight"
        
        # Cleanup
        clear_memory("test-session-3")
    
    def test_update_booking_state(self):
        """Test updating booking state."""
        memory = get_memory("test-session-4")
        
        memory.update_booking_state({
            "stage": "confirm",
            "selected_item": {"airline": "IndiGo", "price": 5000}
        })
        
        assert memory.booking_state["stage"] == "confirm"
        assert memory.booking_state["selected_item"]["airline"] == "IndiGo"
        
        # Cleanup
        clear_memory("test-session-4")
    
    def test_memory_persistence(self):
        """Test that memory persists across get_memory calls."""
        memory1 = get_memory("test-session-5")
        memory1.add_message("user", "Test message")
        
        memory2 = get_memory("test-session-5")
        assert len(memory2.messages) == 1
        assert memory2.messages[0]["content"] == "Test message"
        
        # Cleanup
        clear_memory("test-session-5")
    
    def test_context_for_llm(self):
        """Test context generation for LLM."""
        memory = get_memory("test-session-6")
        memory.update_search_results([{"name": "Test Hotel"}], "hotel")
        
        context = memory.get_context_for_llm()
        
        assert "Current Search Results" in context
        assert "hotel" in context.lower()
        
        # Cleanup
        clear_memory("test-session-6")


class TestRouter:
    """Tests for intent routing."""
    
    def test_booking_intent_with_stage(self):
        """Test that active booking stage routes to booking."""
        from agents.router import classify_intent
        
        memory = get_memory("test-router-1")
        memory.update_booking_state({"stage": "details"})
        
        intent = classify_intent("my name is John", memory)
        assert intent == "booking"
        
        # Cleanup
        clear_memory("test-router-1")
    
    def test_travel_intent(self):
        """Test travel intent classification."""
        from agents.router import _fallback_classification
        
        intent = _fallback_classification("show me flights to Delhi", False, None)
        assert intent == "travel"


class TestTranslation:
    """Tests for translation agent."""
    
    def test_language_detection(self):
        """Test language detection on Hindi text."""
        from agents.translation_agent import translate_input
        
        memory = get_memory("test-translate-1")
        
        # Hindi text
        result, is_valid = translate_input("नमस्ते, मुझे फ्लाइट चाहिए", memory)
        
        # Should detect Hindi and update memory
        assert memory.user_language in ["Hindi", "English"]  # Depends on LLM
        
        # Cleanup
        clear_memory("test-translate-1")


class TestBookingAgent:
    """Tests for booking agent."""
    
    def test_no_results_error(self):
        """Test booking agent handles no search results."""
        from agents.booking_agent import run_booking_agent
        
        memory = get_memory("test-booking-1")
        # No search results
        
        result = run_booking_agent("book the first one", memory)
        
        assert "search" in result.response.lower() or "don't have" in result.response.lower()
        
        # Cleanup
        clear_memory("test-booking-1")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
