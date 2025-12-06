"use client";

import { motion } from "framer-motion";
import { 
  Plane, 
  Hotel, 
  Train, 
  Bus,
  Star, 
  Clock, 
  MapPin,
  Wifi,
  Waves,
  Utensils,
  Sparkles
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { cardHover, buttonTap } from "@/lib/animations";
import type { SearchResult } from "@/lib/api";

interface BookingCardProps {
  result: SearchResult;
  index: number;
  onBook: (result: SearchResult) => void;
}

const typeIcons = {
  flight: Plane,
  hotel: Hotel,
  train: Train,
  bus: Bus,
};

const amenityIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  WiFi: Wifi,
  Pool: Waves,
  Spa: Sparkles,
  Restaurant: Utensils,
};

export function BookingCard({ result, index, onBook }: BookingCardProps) {
  // Determine type - fallback to detecting from fields
  const resultType = result.type || 
    (result.airline ? "flight" : 
     result.price_per_night ? "hotel" : 
     result.train_number ? "train" : 
     result.operator ? "bus" : "flight");
  
  const Icon = typeIcons[resultType as keyof typeof typeIcons] || Plane;
  
  // Get display name
  const displayName = result.name || result.airline || result.operator || "Option";
  
  // Get price - handle both price and price_per_night
  const price = result.price || result.price_per_night || 0;
  const priceLabel = result.price_per_night ? "per night" : "per person";
  
  // Get time display
  const timeDisplay = result.departure 
    ? `${result.departure} - ${result.arrival || ""}`
    : result.time || "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      whileHover="hover"
      variants={cardHover}
    >
      <Card className="overflow-hidden border border-border hover:border-primary/50 transition-colors duration-300">
        {/* Gradient Header */}
        <div className={cn(
          "h-2",
          resultType === "flight" && "bg-gradient-to-r from-blue-500 to-cyan-400",
          resultType === "hotel" && "bg-gradient-to-r from-purple-500 to-pink-400",
          resultType === "train" && "bg-gradient-to-r from-orange-500 to-yellow-400",
          resultType === "bus" && "bg-gradient-to-r from-green-500 to-emerald-400",
        )} />
        
        <div className="p-4">
          {/* Header Row */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg",
                resultType === "flight" && "bg-blue-500/10 text-blue-500",
                resultType === "hotel" && "bg-purple-500/10 text-purple-500",
                resultType === "train" && "bg-orange-500/10 text-orange-500",
                resultType === "bus" && "bg-green-500/10 text-green-500",
              )}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">{String(displayName)}</h3>
                {result.flight_number && (
                  <p className="text-xs text-muted-foreground">{String(result.flight_number)}</p>
                )}
                {result.location && (
                  <p className="text-xs text-muted-foreground">{String(result.location)}</p>
                )}
              </div>
            </div>
            
            {/* Price */}
            <div className="text-right">
              <p className="text-lg font-bold text-foreground">
                ₹{price.toLocaleString()}
              </p>
              <p className="text-[10px] text-muted-foreground">{priceLabel}</p>
            </div>
          </div>

          {/* Details */}
          <div className="space-y-2 mb-4">
            {/* Route for flights/trains/buses */}
            {result.origin && result.destination && (
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-medium">{String(result.origin)}</span>
                <span className="text-muted-foreground">→</span>
                <span className="font-medium">{String(result.destination)}</span>
              </div>
            )}
            
            {/* Time */}
            {timeDisplay && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>{String(timeDisplay)}</span>
                {result.date && <span>• {String(result.date)}</span>}
              </div>
            )}

            {/* Rating for hotels */}
            {result.rating && (
              <div className="flex items-center gap-1.5">
                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                <span className="text-sm font-medium">{result.rating.toFixed(1)}</span>
              </div>
            )}

            {/* Amenities */}
            {result.amenities && result.amenities.length > 0 && (
              <div className="flex gap-2 flex-wrap">
                {result.amenities.map((amenity) => {
                  const AmenityIcon = amenityIcons[amenity] || Sparkles;
                  return (
                    <Badge key={amenity} variant="secondary" className="text-[10px] gap-1">
                      <AmenityIcon className="h-3 w-3" />
                      {amenity}
                    </Badge>
                  );
                })}
              </div>
            )}
          </div>

          {/* Book Button */}
          <motion.div variants={buttonTap} whileTap="tap">
            <Button 
              className="w-full" 
              onClick={() => onBook(result)}
            >
              Book Now
            </Button>
          </motion.div>
        </div>
      </Card>
    </motion.div>
  );
}
