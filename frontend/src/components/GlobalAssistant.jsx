import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Bot, X, Send, Loader2 } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8000/api/v1`;

const GlobalAssistant = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const toggleChat = () => {
    setIsOpen(!isOpen);
    if (!isOpen && messages.length === 0) {
      setMessages([
        { role: 'assistant', content: 'Hello! I am your AI assistant. Ask me any doubts about financial concepts, formulas, or general company information.' }
      ]);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input.trim() };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/assistant/ask`, {
        query: userMessage.content,
        history: messages.map(m => ({ role: m.role, content: m.content }))
      });

      setMessages([...newMessages, { role: 'assistant', content: response.data.answer }]);
    } catch (error) {
      console.error("Failed to fetch assistant response:", error);
      setMessages([...newMessages, { role: 'assistant', content: '**Error**: Failed to connect to the assistant. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col items-end">
      {isOpen && (
        <div className="mb-4 w-80 sm:w-96 brutalist-panel border-4 border-brutalist-dark shadow-[6px_6px_0px_0px_#1A1A1A] bg-[#FDFBF7] flex flex-col h-[450px] transition-all duration-300 origin-bottom-right">
          {/* Header */}
          <div className="bg-[#1A1A1A] text-white p-3 font-black uppercase tracking-widest border-b-4 border-brutalist-dark flex justify-between items-center shrink-0">
            <div className="flex items-center gap-2">
              <Bot size={20} className="text-[#FF6B6B]" />
              <span>Ask AI</span>
            </div>
            <button 
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-[#FF6B6B] transition-colors rounded-none border-2 border-transparent hover:border-white"
            >
              <X size={18} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-stone-50">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`p-3 max-w-[85%] border-2 border-black font-mono text-xs sm:text-sm shadow-[2px_2px_0px_0px_#000000] ${msg.role === 'user' ? 'bg-[#FF6B6B] text-white' : 'bg-white text-black'}`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="p-3 border-2 border-black font-mono text-sm shadow-[2px_2px_0px_0px_#000000] bg-white text-black flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin" /> Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSend} className="border-t-4 border-black p-3 bg-white flex gap-2 shrink-0">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a doubt..."
              className="flex-1 border-2 border-black px-3 py-2 font-mono text-sm outline-none focus:bg-stone-100 placeholder:text-stone-400"
            />
            <button 
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-brutalist-dark text-white p-2 border-2 border-black hover:bg-[#FF6B6B] hover:border-[#FF6B6B] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      )}

      {/* Toggle Button */}
      <button
        onClick={toggleChat}
        className={`group flex items-center justify-center w-14 h-14 border-4 border-brutalist-dark shadow-[4px_4px_0px_0px_#1A1A1A] transition-all hover:-translate-y-1 hover:-translate-x-1 hover:shadow-[6px_6px_0px_0px_#1A1A1A] ${isOpen ? 'bg-[#FF6B6B] text-white' : 'bg-[#FF6B6B] text-white'}`}
      >
        {isOpen ? <X size={28} strokeWidth={3} /> : <Bot size={28} strokeWidth={2.5} />}
        
        {/* Tooltip for collapsed state */}
        {!isOpen && (
          <div className="absolute right-full mr-4 bg-white border-2 border-brutalist-dark text-brutalist-dark font-black font-mono text-xs uppercase px-3 py-2 shadow-[2px_2px_0px_0px_#1A1A1A] opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
            Ask a Doubt!
          </div>
        )}
      </button>
    </div>
  );
};

export default GlobalAssistant;
