"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Send, User, Mail, Phone, CreditCard, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { scaleUp } from "@/lib/animations";

interface BookingFormProps {
  stage: "details" | "payment";
  selectedItem?: {
    airline?: string;
    flight_number?: string;
    origin?: string;
    destination?: string;
    price?: number;
    name?: string;
  };
  onSubmit: (data: BookingFormData) => void;
  isLoading?: boolean;
}

export interface BookingFormData {
  name?: string;
  email?: string;
  phone?: string;
  cardDigits?: string;
}

export function BookingForm({ stage, selectedItem, onSubmit, isLoading }: BookingFormProps) {
  const [formData, setFormData] = useState<BookingFormData>({
    name: "",
    email: "",
    phone: "",
    cardDigits: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleChange = (field: keyof BookingFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <motion.div
      variants={scaleUp}
      initial="initial"
      animate="animate"
      className="w-full max-w-md mx-auto"
    >
      <Card className="p-6 border-primary/30 bg-gradient-to-br from-primary/10 to-purple-500/5 backdrop-blur-sm">
        {/* Selected Item Summary */}
        {selectedItem && (
          <div className="mb-4 p-3 rounded-lg bg-background/50 border border-border/50">
            <p className="text-sm font-medium text-muted-foreground">Booking:</p>
            <p className="text-base font-semibold">
              {selectedItem.airline || selectedItem.name} {selectedItem.flight_number || ""}
            </p>
            {selectedItem.origin && selectedItem.destination && (
              <p className="text-sm text-muted-foreground">
                {selectedItem.origin} → {selectedItem.destination}
              </p>
            )}
            {selectedItem.price && (
              <p className="text-lg font-bold text-primary mt-1">
                ₹{String(selectedItem.price).toLocaleString()}
              </p>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {stage === "details" && (
            <>
              <div className="space-y-2">
                <Label htmlFor="name" className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  Full Name
                </Label>
                <Input
                  id="name"
                  placeholder="Enter your full name"
                  value={formData.name}
                  onChange={(e) => handleChange("name", e.target.value)}
                  required
                  className="bg-background/50"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={formData.email}
                  onChange={(e) => handleChange("email", e.target.value)}
                  required
                  className="bg-background/50"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone" className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  Phone Number
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="+91 98765 43210"
                  value={formData.phone}
                  onChange={(e) => handleChange("phone", e.target.value)}
                  required
                  className="bg-background/50"
                />
              </div>
            </>
          )}

          {stage === "payment" && (
            <div className="space-y-2">
              <Label htmlFor="card" className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-muted-foreground" />
                Last 4 Digits of Card
              </Label>
              <Input
                id="card"
                type="text"
                maxLength={4}
                pattern="[0-9]{4}"
                placeholder="1234"
                value={formData.cardDigits}
                onChange={(e) => handleChange("cardDigits", e.target.value.replace(/\D/g, ""))}
                required
                className="bg-background/50 text-center text-2xl tracking-[0.5em] font-mono"
              />
              <p className="text-xs text-muted-foreground text-center mt-2">
                This is a simulated payment for demo purposes
              </p>
            </div>
          )}

          <Button
            type="submit"
            className="w-full bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-700"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                {stage === "details" ? "Continue to Payment" : "Complete Booking"}
              </>
            )}
          </Button>
        </form>
      </Card>
    </motion.div>
  );
}
