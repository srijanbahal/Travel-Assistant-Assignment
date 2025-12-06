"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChatMessage, TypingIndicator, ChatInput } from "@/components/chat";
import { SearchResults, PaymentFlow, BookingForm, type BookingFormData } from "@/components/booking";
import { Header } from "@/components/layout";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  generateSessionId,
  ChatWebSocket,
  sendMessageREST,
  type Message, 
  type SearchResult,
  type BookingStage,
  type BookingContext 
} from "@/lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "👋 Welcome to InviGrid Travel Assistant!\n\nI can help you search for flights, hotels, trains, and buses. Try asking:\n• \"Find flights from Delhi to Mumbai\"\n• \"Search hotels in Goa\"\n• \"Book a train to Chennai\"",
      timestamp: new Date(),
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchContext, setSearchContext] = useState<string>("unknown");
  const [bookingStage, setBookingStage] = useState<BookingStage>(null);
  const [bookingContext, setBookingContext] = useState<BookingContext>({});
  const [userLanguage, setUserLanguage] = useState("English");
  const [sessionId, setSessionId] = useState(() => generateSessionId());
  
  const wsRef = useRef<ChatWebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  // WebSocket connection
  useEffect(() => {
    const ws = new ChatWebSocket(
      sessionId,
      // Message handler
      (data) => {
        if (data.type === "thinking") {
          setIsTyping(true);
        } else if (data.type === "response") {
          setIsTyping(false);
          
          // Update state from response
          if (data.search_results && data.search_results.length > 0) {
            setSearchResults(data.search_results);
          }
          if (data.search_context) {
            setSearchContext(data.search_context);
          }
          if (data.booking_stage !== undefined) {
            // Only set booking_stage if it's a new booking flow or if there's a valid confirmation
            // Don't restore 'complete' from server if we just reset it locally
            if (data.booking_stage === "complete" && !data.booking_context?.confirmation_id) {
              // Backend has stale 'complete' state but no new confirmation - ignore it
            } else {
              setBookingStage(data.booking_stage);
            }
          }
          if (data.booking_context) {
            setBookingContext(data.booking_context);
          }
          if (data.user_language) {
            setUserLanguage(data.user_language);
          }
          
          // Add assistant message
          const assistantMessage: Message = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: data.message || "",
            englishContent: data.english_message,
            timestamp: new Date(),
            metadata: {
              searchResults: data.search_results,
              bookingStage: data.booking_stage,
              bookingContext: data.booking_context,
            },
          };
          setMessages((prev) => [...prev, assistantMessage]);
        } else if (data.type === "error") {
          setIsTyping(false);
          setMessages((prev) => [
            ...prev,
            {
              id: `error-${Date.now()}`,
              role: "assistant",
              content: data.message || "An error occurred. Please try again.",
              timestamp: new Date(),
            },
          ]);
        }
      },
      // On connect
      () => setIsConnected(true),
      // On disconnect
      () => setIsConnected(false)
    );
    
    ws.connect();
    wsRef.current = ws;
    
    return () => {
      ws.disconnect();
    };
  }, [sessionId]);

  const handleSendMessage = async (content: string) => {
    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Try WebSocket first
    if (wsRef.current?.isConnected) {
      wsRef.current.sendMessage(content);
      return;
    }

    // Fallback to REST
    setIsTyping(true);
    try {
      const response = await sendMessageREST(
        content,
        {
          sessionId,
          userLanguage,
          bookingContext,
          bookingStage,
          searchResults,
          searchContext,
        }
      );
      
      if (response) {
        // Update state
        if (response.searchResults.length > 0) {
          setSearchResults(response.searchResults);
        }
        setSearchContext(response.searchContext);
        setBookingStage(response.bookingStage);
        setBookingContext(response.bookingContext);
        setUserLanguage(response.userLanguage);

        // Add assistant message
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.message,
          englishContent: response.englishMessage,
          timestamp: new Date(),
          metadata: {
            searchResults: response.searchResults,
            bookingStage: response.bookingStage,
            bookingContext: response.bookingContext,
          },
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleBookResult = (result: SearchResult) => {
    const name = result.name || result.airline || result.operator || "this option";
    handleSendMessage(`Book ${name}`);
  };

  const handleNewBooking = () => {
    // Clear all booking state
    setBookingStage(null);
    setBookingContext({});
    setSearchResults([]);
    setSearchContext("unknown");
    // Start fresh conversation
    handleSendMessage("I want to book another trip");
  };

  const handleNewChat = () => {
    // Generate new session ID
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    
    // Reset all state
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content: "👋 Welcome to InviGrid Travel Assistant!\n\nI can help you search for flights, hotels, trains, and buses. Try asking:\n• \"Find flights from Delhi to Mumbai\"\n• \"Search hotels in Goa\"\n• \"Book a train to Chennai\"",
        timestamp: new Date(),
      },
    ]);
    setBookingStage(null);
    setBookingContext({});
    setSearchResults([]);
    setSearchContext("unknown");
    setUserLanguage("English");
    
    // Note: WebSocket will automatically reconnect due to useEffect dependency on sessionId
  };

  const handleBookingFormSubmit = (data: BookingFormData) => {
    // Format the data as a message to send to the backend
    if (bookingStage === "details") {
      const detailsMessage = `Name: ${data.name}, Email: ${data.email}, Phone: ${data.phone}`;
      handleSendMessage(detailsMessage);
    } else if (bookingStage === "payment") {
      handleSendMessage(data.cardDigits || "");
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <Header onNewChat={handleNewChat} />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <ScrollArea className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto py-4">
              <AnimatePresence mode="popLayout">
                {messages.map((message) => (
                  <ChatMessage 
                    key={message.id} 
                    message={message}
                    showEnglishToggle={message.role === "assistant"}
                  />
                ))}
              </AnimatePresence>
              
              {/* Search Results inline */}
              {searchResults.length > 0 && !bookingStage && (
                <SearchResults 
                  results={searchResults}
                  searchContext={searchContext}
                  onBook={handleBookResult} 
                />
              )}
              
              {/* Booking Form for details/payment stages */}
              {(bookingStage === "details" || bookingStage === "payment") && (
                <div className="px-4 py-3">
                  <BookingForm
                    stage={bookingStage}
                    selectedItem={bookingContext.selected_item}
                    onSubmit={handleBookingFormSubmit}
                    isLoading={isTyping}
                  />
                </div>
              )}

              {/* Payment Flow Progress (for confirm stage and complete) */}
              {(bookingStage === "confirm" || bookingStage === "complete") && (
                <PaymentFlow 
                  stage={bookingStage}
                  context={bookingContext}
                  onNewBooking={handleNewBooking}
                />
              )}
              
              {/* Typing Indicator */}
              {isTyping && <TypingIndicator />}
              
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Hide chat input when booking form is shown */}
          {bookingStage !== "details" && bookingStage !== "payment" && (
            <ChatInput 
              onSend={handleSendMessage}
              disabled={isTyping}
              placeholder="Type your message..."
            />
          )}
        </div>
      </div>
      
      {/* Connection Status */}
      <div className="absolute bottom-20 right-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-yellow-500"}`}
          title={isConnected ? "Connected" : "Connecting..."}
        />
      </div>
    </div>
  );
}
