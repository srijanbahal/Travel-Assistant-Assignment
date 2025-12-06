"use client";

import { motion, AnimatePresence } from "framer-motion";
import { BookingCard } from "./BookingCard";
import { staggerContainer } from "@/lib/animations";
import type { SearchResult } from "@/lib/api";

interface SearchResultsProps {
  results: SearchResult[];
  searchContext?: string;
  onBook: (result: SearchResult) => void;
}

export function SearchResults({ results, searchContext, onBook }: SearchResultsProps) {
  if (!results.length) return null;

  // Determine the type from context or first result
  const resultType = searchContext || results[0]?.type || "item";

  return (
    <motion.div
      className="px-4 py-3"
      variants={staggerContainer}
      initial="initial"
      animate="animate"
    >
      <h3 className="text-sm font-medium text-muted-foreground mb-3">
        Found {results.length} options
      </h3>
      
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <AnimatePresence>
          {results.map((result, index) => (
            <BookingCard
              key={result.id}
              result={result}
              index={index}
              onBook={onBook}
            />
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
