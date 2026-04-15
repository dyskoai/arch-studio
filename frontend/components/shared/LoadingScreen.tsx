"use client";

import { useEffect, useState } from "react";

interface LoadingScreenProps {
  messages: string[];
}

export function LoadingScreen({ messages }: LoadingScreenProps) {
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIndex((i) => (i + 1) % messages.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [messages.length]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-10 px-6">
      {/* Dot grid */}
      <div className="grid grid-cols-8 gap-2">
        {Array.from({ length: 40 }).map((_, i) => (
          <div
            key={i}
            className="dot-grid-dot w-1.5 h-1.5 rounded-full bg-teal-400"
            style={{ animationDelay: `${(i * 0.07) % 1.4}s` }}
          />
        ))}
      </div>

      {/* Cycling message */}
      <p
        className="text-xs tracking-[0.25em] uppercase text-slate-400 transition-opacity duration-500"
        key={msgIndex}
      >
        {messages[msgIndex]}
      </p>

      {/* Progress bar */}
      <div className="w-64 h-px bg-slate-800 relative overflow-hidden">
        <div className="progress-bar absolute inset-y-0 left-0 bg-teal-400" />
      </div>
    </div>
  );
}

export const REFINING_MESSAGES = [
  "reading your idea",
  "sharpening the problem statement",
  "adding specifics",
  "almost ready to review",
];

export const GENERATING_MESSAGES = [
  "parsing problem topology",
  "classifying agent pattern",
  "assigning weight classes",
  "resolving node dependencies",
  "wiring the architecture",
  "rendering blueprint",
];
