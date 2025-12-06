"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Languages, Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { messageVariants } from "@/lib/animations";
import type { Message } from "@/lib/api";

interface ChatMessageProps {
  message: Message;
  showEnglishToggle?: boolean;
}

export function ChatMessage({ message, showEnglishToggle = true }: ChatMessageProps) {
  const [showEnglish, setShowEnglish] = useState(false);
  const isUser = message.role === "user";
  
  const displayContent = showEnglish && message.englishContent 
    ? message.englishContent 
    : message.content;

  return (
    <motion.div
      variants={messageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={cn(
        "flex gap-3 px-4 py-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <Avatar className={cn(
        "h-9 w-9 flex-shrink-0 flex items-center justify-center",
        isUser 
          ? "bg-primary text-primary-foreground" 
          : "bg-gradient-to-br from-blue-500 to-purple-600 text-white"
      )}>
        {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
      </Avatar>

      {/* Message Content */}
      <div className={cn(
        "flex flex-col gap-1.5 max-w-[75%]",
        isUser ? "items-end" : "items-start"
      )}>
        {/* Message Bubble */}
        <div className={cn(
          "rounded-2xl px-4 py-2.5 shadow-sm",
          isUser 
            ? "bg-primary text-primary-foreground rounded-tr-sm" 
            : "bg-card border border-border rounded-tl-sm"
        )}>
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {displayContent}
          </p>
        </div>

        {/* Actions Row */}
        <div className={cn(
          "flex items-center gap-2",
          isUser ? "flex-row-reverse" : "flex-row"
        )}>
          {/* View English Button */}
          {!isUser && showEnglishToggle && message.englishContent && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowEnglish(!showEnglish)}
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
            >
              <Languages className="h-3.5 w-3.5 mr-1" />
              {showEnglish ? "Original" : "English"}
            </Button>
          )}
          
          {/* Timestamp */}
          <span className="text-[10px] text-muted-foreground">
            {formatTime(message.timestamp)}
          </span>

          {/* Booking Stage Badge */}
          {message.metadata?.bookingStage && (
            <Badge variant="secondary" className="text-[10px]">
              {formatBookingStage(message.metadata.bookingStage)}
            </Badge>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

function formatBookingStage(stage: string): string {
  const stages: Record<string, string> = {
    confirm: "Confirming",
    details: "Details",
    payment: "Payment",
    complete: "Booked ✓",
  };
  return stages[stage] || stage;
}
