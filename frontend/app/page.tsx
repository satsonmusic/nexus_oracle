"use client";

import { useState } from "react";
import Image from "next/image";

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Add user message to UI
    const newMessages = [...messages, { role: "user", content: input }];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      // Send message to FastAPI backend
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input, user_id: "scott_123" }),
      });

      const data = await response.json();

      // Add Jarvis's response to UI
      setMessages([...newMessages, { role: "jarvis", content: data.response }]);
    } catch (error) {
      setMessages([...newMessages, { role: "jarvis", content: "❌ Error connecting to backend. Is your Python server running?" }]);
    }

    setIsLoading(false);
  };

  return (
    <main className="flex flex-col items-center justify-between min-h-screen p-8 bg-gray-950 text-white font-sans">
      <div className="w-full max-w-4xl flex flex-col h-[90vh]">
        
        {/* Header Section */}
        <div className="flex flex-row justify-between items-start pb-6 border-b border-gray-800 mb-4">
          
          {/* Left: Sprite & Title */}
          <div className="flex items-center gap-4">
            <div className="relative w-20 h-20 bg-gray-900 rounded-xl overflow-hidden border border-gray-700 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
              <Image 
                src="/sprite.png" 
                alt="Satyashil Sonecha" 
                fill
                className="object-contain p-1"
                // Fallback text just in case the image isn't in the public folder yet
                unoptimized
              />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-blue-400 tracking-tight drop-shadow-md">J.A.R.V.I.S.</h1>
              <p className="text-gray-400 text-sm mt-1">Autonomous Executive Assistant</p>
            </div>
          </div>

          {/* Right: Custom Signature Block */}
          <div className="relative border border-gray-700 rounded-xl px-8 py-3 bg-gray-900/50 text-center shadow-lg backdrop-blur-sm min-w-[250px]">
            <div className="text-sm font-medium text-gray-400 mb-1">By</div>
            <div className="text-2xl font-bold text-cyan-300 tracking-wide">Satyashil Sonecha</div>
            
            {/* CSS-based decorative stars */}
            <div className="absolute top-2 right-3 text-yellow-400 text-sm">✨</div>
            <div className="absolute top-1/2 left-3 -translate-y-1/2 text-pink-400 text-sm drop-shadow-[0_0_5px_rgba(244,114,182,0.8)]">✦</div>
            <div className="absolute bottom-2 right-4 text-white text-xs opacity-70">✦</div>
          </div>
          
        </div>

        {/* Chat Box */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-20">
              System online. How can I help you today, sir?
            </div>
          )}
          
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`p-4 max-w-[80%] rounded-2xl whitespace-pre-wrap ${
                msg.role === "user" ? "bg-blue-600 text-white shadow-md" : "bg-gray-800 text-gray-200 border border-gray-700 shadow-sm"
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="p-4 rounded-2xl bg-gray-800 text-gray-400 animate-pulse border border-gray-700">
                Processing...
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="pt-4 mt-4 border-t border-gray-800 flex gap-3">
          <input
            type="text"
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-500 transition-colors"
            placeholder="Give Jarvis a command..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-medium transition-colors disabled:opacity-50 shadow-lg shadow-blue-900/20"
          >
            Send
          </button>
        </div>
      </div>
    </main>
  );
}