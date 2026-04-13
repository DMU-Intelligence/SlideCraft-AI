"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { useEffect, useState, useRef } from "react";

interface BrushLoadingProps {
  message: string;
}

export function BrushLoading({ message }: BrushLoadingProps) {
  const [displayedText, setDisplayedText] = useState("");
  const prevMessage = useRef(message);
  const pathProgress = useMotionValue(0);
  const pathLength = useTransform(pathProgress, [0, 1], [0, 1]);

  // SVG stroke animation — loops
  useEffect(() => {
    const controls = animate(pathProgress, 1, {
      duration: 3,
      ease: "easeInOut",
      repeat: Infinity,
      repeatType: "loop",
      repeatDelay: 0.5,
    });
    return () => controls.stop();
  }, [pathProgress]);

  // Typing animation for the message
  useEffect(() => {
    if (message === prevMessage.current && displayedText === message) return;
    prevMessage.current = message;
    setDisplayedText("");

    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayedText(message.slice(0, i));
      if (i >= message.length) clearInterval(interval);
    }, 40);

    return () => clearInterval(interval);
  }, [message]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.5 }}
      className="flex min-h-screen flex-col items-center justify-center gap-10"
    >
      {/* Brush-drawn slide outline */}
      <div className="relative h-48 w-80">
        <svg
          viewBox="0 0 320 192"
          fill="none"
          className="h-full w-full"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Outer slide rectangle — drawn like a brush stroke */}
          <motion.rect
            x="10"
            y="10"
            width="300"
            height="172"
            rx="6"
            stroke="#2D2D2D"
            strokeWidth="2"
            strokeLinecap="round"
            style={{ pathLength }}
            fill="none"
          />
          {/* Title line */}
          <motion.line
            x1="40"
            y1="50"
            x2="200"
            y2="50"
            stroke="#2D2D2D"
            strokeWidth="2"
            strokeLinecap="round"
            style={{ pathLength }}
          />
          {/* Content lines */}
          <motion.line
            x1="40"
            y1="80"
            x2="280"
            y2="80"
            stroke="#A8A8A8"
            strokeWidth="1.5"
            strokeLinecap="round"
            style={{ pathLength }}
          />
          <motion.line
            x1="40"
            y1="100"
            x2="260"
            y2="100"
            stroke="#A8A8A8"
            strokeWidth="1.5"
            strokeLinecap="round"
            style={{ pathLength }}
          />
          <motion.line
            x1="40"
            y1="120"
            x2="240"
            y2="120"
            stroke="#A8A8A8"
            strokeWidth="1.5"
            strokeLinecap="round"
            style={{ pathLength }}
          />
          {/* Small accent dot */}
          <motion.circle
            cx="40"
            cy="150"
            r="4"
            fill="#4F46E5"
            style={{ opacity: pathLength }}
          />
          <motion.line
            x1="52"
            y1="150"
            x2="160"
            y2="150"
            stroke="#A8A8A8"
            strokeWidth="1.5"
            strokeLinecap="round"
            style={{ pathLength }}
          />
        </svg>
      </div>

      {/* Typing text */}
      <div className="flex items-center gap-0.5 text-lg tracking-tight text-ink-light">
        <span>{displayedText}</span>
        <span className="animate-blink text-accent">|</span>
      </div>
    </motion.div>
  );
}
