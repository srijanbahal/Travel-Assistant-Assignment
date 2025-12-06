/**
 * API Client for communicating with the InviGrid Travel Assistant backend
 * Supports both REST and WebSocket connections
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || API_BASE.replace(/^http/, "ws");

// =============== Types ===============

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  englishContent?: string;
  timestamp: Date;
  metadata?: {
    searchResults?: SearchResult[];
    bookingStage?: BookingStage;
    bookingContext?: BookingContext;
  };
}

export interface SearchResult {
  id?: string;
  type?: "flight" | "hotel" | "train" | "bus";
  // Flight fields
  airline?: string;
  flight_number?: string;
  origin?: string;
  destination?: string;
  date?: string;
  departure?: string;
  arrival?: string;
  // Hotel fields
  name?: string;
  location?: string;
  rating?: number;
  price_per_night?: number;
  amenities?: string[];
  // Train fields
  train_number?: string;
  train_class?: string;
  // Common
  price?: number;
  [key: string]: unknown;
}

export type BookingStage = "confirm" | "details" | "payment" | "complete" | null;

export interface BookingContext {
  session_id?: string;
  selected_item?: SearchResult;
  user_details?: {
    name?: string;
    email?: string;
    phone?: string;
  };
  confirmation_id?: string;
  card_last4?: string;
  [key: string]: unknown;
}

export interface ChatContext {
  sessionId: string;
  userLanguage: string;
  bookingContext: BookingContext;
  bookingStage: BookingStage;
  searchResults: SearchResult[];
  searchContext: string;
}

export interface ChatResponse {
  message: string;
  englishMessage?: string;
  searchResults: SearchResult[];
  searchContext: string;
  bookingStage: BookingStage;
  bookingContext: BookingContext;
  userLanguage: string;
}

// =============== Session Management ===============

export async function createSession(): Promise<string> {
  try {
    const response = await fetch(`${API_BASE}/api/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    
    if (!response.ok) {
      throw new Error("Failed to create session");
    }
    
    const data = await response.json();
    return data.session_id;
  } catch (error) {
    console.error("Session creation error:", error);
    // Fallback to local ID
    return generateSessionId();
  }
}

export function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// =============== REST API ===============

export async function sendMessageREST(
  message: string,
  context: ChatContext
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      context: {
        session_id: context.sessionId,
        user_language: context.userLanguage,
        booking_context: context.bookingContext,
        booking_stage: context.bookingStage,
        search_results: context.searchResults,
        search_context: context.searchContext,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  
  return {
    message: data.message,
    englishMessage: data.english_message,
    searchResults: data.search_results || [],
    searchContext: data.search_context || "unknown",
    bookingStage: data.booking_stage,
    bookingContext: data.booking_context || {},
    userLanguage: data.user_language || "English",
  };
}

// =============== WebSocket Client ===============

export type WebSocketMessageHandler = (data: {
  type: "thinking" | "response" | "error" | "pong";
  message?: string;
  english_message?: string;
  search_results?: SearchResult[];
  search_context?: string;
  booking_stage?: BookingStage;
  booking_context?: BookingContext;
  user_language?: string;
}) => void;

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private onMessage: WebSocketMessageHandler;
  private onConnect: () => void;
  private onDisconnect: () => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;

  constructor(
    sessionId: string,
    onMessage: WebSocketMessageHandler,
    onConnect: () => void = () => {},
    onDisconnect: () => void = () => {}
  ) {
    this.sessionId = sessionId;
    this.onMessage = onMessage;
    this.onConnect = onConnect;
    this.onDisconnect = onDisconnect;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.ws = new WebSocket(`${WS_BASE}/ws/${this.sessionId}`);

      this.ws.onopen = () => {
        console.log("WebSocket connected");
        this.reconnectAttempts = 0;
        this.onConnect();
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch (error) {
          console.error("WebSocket parse error:", error);
        }
      };

      this.ws.onclose = () => {
        console.log("WebSocket disconnected");
        this.stopPing();
        this.onDisconnect();
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    } catch (error) {
      console.error("WebSocket connection failed:", error);
      this.attemptReconnect();
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log("Max reconnect attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  sendMessage(content: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: "message",
        content,
      }));
    } else {
      console.error("WebSocket not connected");
    }
  }

  disconnect(): void {
    this.stopPing();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// =============== Unified Send Function ===============

/**
 * Send a message using WebSocket if available, otherwise fallback to REST
 */
export async function sendMessage(
  sessionId: string,
  message: string,
  context?: Partial<ChatContext>,
  wsClient?: ChatWebSocket
): Promise<ChatResponse | null> {
  // If WebSocket is connected, use it (returns null, response comes via callback)
  if (wsClient?.isConnected) {
    wsClient.sendMessage(message);
    return null;
  }
  
  // Fallback to REST
  const fullContext: ChatContext = {
    sessionId,
    userLanguage: context?.userLanguage || "English",
    bookingContext: context?.bookingContext || { session_id: sessionId },
    bookingStage: context?.bookingStage || null,
    searchResults: context?.searchResults || [],
    searchContext: context?.searchContext || "unknown",
  };
  
  return sendMessageREST(message, fullContext);
}

// =============== Chat History ===============

export async function getChatHistory(sessionId: string): Promise<Message[]> {
  try {
    const response = await fetch(`${API_BASE}/api/session/${sessionId}/history`);
    
    if (!response.ok) {
      return [];
    }
    
    const data = await response.json();
    
    return (data.messages || []).map((msg: { role: string; content: string; timestamp?: string }, index: number) => ({
      id: `history-${index}`,
      role: msg.role as "user" | "assistant",
      content: msg.content,
      timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
    }));
  } catch (error) {
    console.error("Failed to load chat history:", error);
    return [];
  }
}

// =============== Clear Session ===============

export async function clearSession(sessionId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/session/${sessionId}`, {
      method: "DELETE",
    });
  } catch (error) {
    console.error("Failed to clear session:", error);
  }
}
