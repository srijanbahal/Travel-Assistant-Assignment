"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Menu, Moon, Sun, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";

interface HeaderProps {
  onNewChat?: () => void;
}

export function Header({ onNewChat }: HeaderProps) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Check initial theme
    const dark = document.documentElement.classList.contains("dark");
    setIsDark(dark);
  }, []);

  const toggleTheme = () => {
    document.documentElement.classList.toggle("dark");
    setIsDark(!isDark);
  };

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
    >
      <div className="container flex h-14 items-center justify-between px-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <motion.div
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring" as const, stiffness: 400, damping: 17 }}
            className="relative"
          >
            {/* Custom Logo Icon */}
            <svg
              viewBox="0 0 32 32"
              className="h-8 w-8"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#6366f1" />
                  <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
              <circle cx="16" cy="16" r="14" fill="url(#logoGradient)" />
              <path
                d="M10 18L16 10L22 18M12 16H20"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="16" cy="21" r="1.5" fill="white" />
            </svg>
          </motion.div>
          <div className="flex flex-col">
            <span className="font-semibold text-base tracking-tight text-foreground leading-none">
              InviGrid
            </span>
            <span className="text-[9px] text-muted-foreground tracking-wide uppercase">
              Travel Assistant
            </span>
          </div>
        </Link>

        {/* Nav */}
        <nav className="hidden md:flex items-center gap-6">
          <Link 
            href="/" 
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Home
          </Link>
          <Link 
            href="/chat" 
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Book Travel
          </Link>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-4">
          {onNewChat && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onNewChat}
              className="hidden md:flex gap-2"
            >
              <PlusCircle className="h-4 w-4" />
              New Chat
            </Button>
          )}

          <Button variant="ghost" size="icon" onClick={toggleTheme} className="rounded-full">
            {isDark ? (
              <Sun className="h-5 w-5 text-yellow-500 transition-all" />
            ) : (
              <Moon className="h-5 w-5 text-gray-700 transition-all" />
            )}
            <span className="sr-only">Toggle theme</span>
          </Button>

          {/* Mobile Menu */}
          <Button variant="ghost" size="icon" className="md:hidden">
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </motion.header>
  );
}
