"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { 
  Plane, 
  Hotel, 
  Train, 
  MessageCircle, 
  ArrowRight,
  Globe,
  Zap,
  Shield
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Header } from "@/components/layout";
import { fadeIn, slideUp, staggerContainer, cardHover } from "@/lib/animations";

const features = [
  {
    icon: Globe,
    title: "Multi-Lingual",
    description: "Chat in Hindi, Tamil, Bengali, or any language. We understand you.",
  },
  {
    icon: Zap,
    title: "Instant Results",
    description: "Get flight, hotel, and train options in seconds with AI-powered search.",
  },
  {
    icon: Shield,
    title: "Secure Booking",
    description: "Safe payment processing with instant confirmation delivered to you.",
  },
];

const travelOptions = [
  { icon: Plane, label: "Flights", color: "from-blue-500 to-cyan-400" },
  { icon: Hotel, label: "Hotels", color: "from-purple-500 to-pink-400" },
  { icon: Train, label: "Trains", color: "from-orange-500 to-yellow-400" },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Background Gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/5 to-transparent pointer-events-none" />
        
        <div className="container px-4 py-20 md:py-32 min-h-[calc(100vh-14rem)] flex flex-col justify-center">
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="max-w-3xl mx-auto text-center"
          >
            <motion.div variants={fadeIn} className="mb-6">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium">
                <Zap className="h-3.5 w-3.5" />
                AI-Powered Travel Assistant
              </span>
            </motion.div>
            
            <motion.h1 
              variants={slideUp}
              className="text-4xl md:text-6xl font-bold tracking-tight mb-6"
            >
              Book Travel in
              <span className="bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
                {" "}Any Language
              </span>
            </motion.h1>
            
            <motion.p 
              variants={slideUp}
              className="text-lg text-muted-foreground mb-8 max-w-xl mx-auto"
            >
              Search flights, hotels, and trains effortlessly. Chat naturally in your 
              preferred language and let our AI handle the rest.
            </motion.p>
            
            <motion.div variants={slideUp} className="flex gap-4 justify-center">
              <Link href="/chat">
                <Button size="lg" className="gap-2 h-12 px-6">
                  <MessageCircle className="h-5 w-5" />
                  Start Booking
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </motion.div>
          </motion.div>
          
          {/* Travel Options */}
          <motion.div 
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="flex justify-center gap-4 mt-16"
          >
            {travelOptions.map((option) => (
              <motion.div
                key={option.label}
                variants={slideUp}
                whileHover={{ y: -5 }}
                className="flex flex-col items-center gap-2"
              >
                <div className={`p-4 rounded-2xl bg-gradient-to-br ${option.color} shadow-lg`}>
                  <option.icon className="h-8 w-8 text-white" />
                </div>
                <span className="text-sm font-medium text-muted-foreground">
                  {option.label}
                </span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 border-t border-border">
        <div className="container px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-12"
          >
            <h2 className="text-3xl font-bold mb-4">Why InviGrid?</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Experience a smarter way to book travel with our AI assistant
            </p>
          </motion.div>
          
          <motion.div 
            variants={staggerContainer}
            initial="initial"
            whileInView="animate"
            viewport={{ once: true }}
            className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto"
          >
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                variants={slideUp}
                whileHover="hover"
              >
                <motion.div variants={cardHover}>
                  <Card className="p-6 h-full hover:border-primary/50 transition-colors">
                    <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                      <feature.icon className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                  </Card>
                </motion.div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-br from-primary/5 to-purple-500/5">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="container px-4 text-center"
        >
          <h2 className="text-3xl font-bold mb-4">Ready to Travel?</h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Start a conversation and book your next adventure in minutes
          </p>
          <Link href="/chat">
            <Button size="lg" className="gap-2">
              <MessageCircle className="h-5 w-5" />
              Chat Now
            </Button>
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-border">
        <div className="container px-4 text-center text-sm text-muted-foreground">
          <p>© 2024 InviGrid. Multi-Lingual Travel Assistant.</p>
        </div>
      </footer>
    </div>
  );
}
