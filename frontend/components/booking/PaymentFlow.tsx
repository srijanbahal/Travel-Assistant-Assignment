"use client";

import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, CreditCard, User, FileCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { successAnimation, scaleUp } from "@/lib/animations";
import { cn } from "@/lib/utils";
import type { BookingStage, BookingContext } from "@/lib/api";

interface PaymentFlowProps {
  stage: BookingStage;
  context?: BookingContext;
  onNewBooking?: () => void;
}

const stages = [
  { key: "confirm", label: "Confirm", icon: FileCheck },
  { key: "details", label: "Details", icon: User },
  { key: "payment", label: "Payment", icon: CreditCard },
  { key: "complete", label: "Complete", icon: CheckCircle2 },
];

export function PaymentFlow({ stage, context, onNewBooking }: PaymentFlowProps) {
  if (!stage) return null;
  
  const currentIndex = stages.findIndex((s) => s.key === stage);

  return (
    <motion.div
      variants={scaleUp}
      initial="initial"
      animate="animate"
      className="px-4 py-3"
    >
      <Card className="p-4 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-6">
          {stages.map((s, i) => {
            const isActive = s.key === stage;
            const isCompleted = i < currentIndex;
            const Icon = s.icon;
            
            return (
              <div key={s.key} className="flex items-center">
                <motion.div
                  className={cn(
                    "flex flex-col items-center gap-1",
                    isActive && "scale-110",
                  )}
                  animate={{ scale: isActive ? 1.1 : 1 }}
                >
                  <div className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300",
                    isCompleted && "bg-green-500 text-white",
                    isActive && "bg-primary text-primary-foreground ring-4 ring-primary/20",
                    !isCompleted && !isActive && "bg-muted text-muted-foreground",
                  )}>
                    {isCompleted ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  <span className={cn(
                    "text-[10px] font-medium",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )}>
                    {s.label}
                  </span>
                </motion.div>
                
                {/* Connector Line */}
                {i < stages.length - 1 && (
                  <div className={cn(
                    "w-8 h-0.5 mx-2",
                    i < currentIndex ? "bg-green-500" : "bg-muted"
                  )} />
                )}
              </div>
            );
          })}
        </div>

        {/* Success Message */}
        <AnimatePresence>
          {stage === "complete" && Boolean(context?.confirmation_id || context?.confirmationId) && (
            <motion.div
              variants={successAnimation}
              initial="initial"
              animate="animate"
              className="text-center space-y-4"
            >
              <motion.div
                animate={{ 
                  scale: [1, 1.2, 1],
                  rotate: [0, 10, -10, 0]
                }}
                transition={{ duration: 0.5 }}
                className="w-16 h-16 mx-auto bg-green-500 rounded-full flex items-center justify-center"
              >
                <CheckCircle2 className="h-8 w-8 text-white" />
              </motion.div>
              
              <div>
                <h3 className="text-xl font-bold text-green-600">
                  Booking Confirmed!
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Confirmation ID: <span className="font-mono font-bold">{String(context?.confirmation_id || context?.confirmationId || "")}</span>
                </p>
              </div>
              
              {onNewBooking && (
                <Button 
                  variant="outline" 
                  onClick={onNewBooking}
                  className="mt-4"
                >
                  Book Another Trip
                </Button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Current Stage Info - only for confirm stage */}
        {stage === "confirm" && (
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Please confirm your selection to proceed
            </p>
          </div>
        )}
      </Card>
    </motion.div>
  );
}
