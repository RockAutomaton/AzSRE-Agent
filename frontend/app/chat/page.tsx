'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Bot, User, Sparkles, ArrowLeft, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Link from 'next/link';
import useSWR from 'swr';
import { API_URL } from '../lib/config';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AlertEntity {
  RowKey: string;
  PartitionKey: string;
  RuleName: string;
  Severity: string;
  ReportSummary: string;
  CreatedAt: string;
}

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Fetch recent alerts for dynamic prompts
  const { data: alerts } = useSWR<AlertEntity[]>(`${API_URL}/api/history`, fetcher);
  
  // Generate dynamic prompts based on recent alerts
  const suggestedPrompts = useMemo(() => {
    if (!alerts || alerts.length === 0) {
      return [
        "Summarize recent alerts",
        "What are the most common incident types?",
        "What trends do you see in the alert history?",
        "How can I prevent similar incidents?",
      ];
    }
    
    const prompts: Set<string> = new Set();
    
    // Add general summary prompt
    prompts.add("Summarize the last 5 alerts");
    
    // Get unique alerts by RuleName to avoid duplicates
    const uniqueAlerts = Array.from(
      new Map(alerts.map(alert => [alert.RuleName, alert])).values()
    ).slice(0, 2);
    
    // Add prompts for unique recent alerts
    uniqueAlerts.forEach(alert => {
      if (prompts.size < 4) {
        prompts.add(`What caused the "${alert.RuleName}" incident?`);
      }
    });
    
    // Get unique alert types
    const alertTypes = Array.from(new Set(alerts.map(a => a.PartitionKey)));
    
    // Add classification-based prompts
    if (alertTypes.length > 0 && prompts.size < 4) {
      const type = alertTypes[0];
      prompts.add(`What are the common patterns in ${type} alerts?`);
    }
    
    // Fill remaining slots with general prompts
    const generalPrompts = [
      "What are the most critical incidents?",
      "What trends do you see in the alert history?",
      "How can I prevent similar incidents?",
      "Which alerts require immediate attention?",
    ];
    
    for (const prompt of generalPrompts) {
      if (prompts.size >= 4) break;
      prompts.add(prompt);
    }
    
    return Array.from(prompts).slice(0, 4);
  }, [alerts]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg = text.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) throw new Error("No response body");

      // Add placeholder for assistant response
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        assistantResponse += chunk;
        
        // Update the last message
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].content = assistantResponse;
          return newMessages;
        });
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = error instanceof Error 
        ? `⚠️ Error: ${error.message}` 
        : "⚠️ Error: Could not connect to agent. Please check if the backend is running on port 8000.";
      setMessages(prev => {
        // Remove the placeholder if it exists
        const newMessages = [...prev];
        if (newMessages.length > 0 && newMessages[newMessages.length - 1].role === 'assistant' && newMessages[newMessages.length - 1].content === '') {
          newMessages[newMessages.length - 1].content = errorMessage;
        } else {
          newMessages.push({ role: 'assistant', content: errorMessage });
        }
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const clearChat = () => {
    setMessages([]);
    setInput('');
  };

  return (
    <div className="min-h-screen p-8 bg-slate-50 dark:bg-slate-900">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* Back Button */}
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
        </Link>
        
        <div className="h-[calc(100vh-200px)] flex flex-col bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 rounded-t-xl">
          <div className="flex items-center justify-between">
            <div>
          <h2 className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2">
            <Bot className="h-5 w-5 text-blue-600 dark:text-blue-400" /> Investigator Chat
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">AI-powered SRE Assistant with access to alert history.</p>
            </div>
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600"
                title="Start a new chat"
              >
                <RotateCcw className="w-3 h-3" />
                New Chat
              </button>
            )}
          </div>
        </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6 py-12">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-100 dark:bg-blue-900/20 rounded-full blur-2xl opacity-50"></div>
              <Bot className="h-20 w-20 text-blue-500 dark:text-blue-400 relative z-10" />
            </div>
            <div className="space-y-2 max-w-md">
              <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                How can I help you today?
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                I can help investigate alerts and explain findings from your incident history.
              </p>
            </div>
            
            <div className="w-full max-w-2xl space-y-3 mt-4">
              <p className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
                Suggested Questions
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {suggestedPrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(prompt)}
                    disabled={isLoading}
                    className="group w-full text-left p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all duration-200 flex items-start gap-3 text-slate-700 dark:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-sm"
                    title={prompt}
                  >
                    <div className="shrink-0 mt-0.5">
                      <Sparkles className="w-4 h-4 text-blue-500 dark:text-blue-400 group-hover:scale-110 transition-transform" />
                    </div>
                    <span className="flex-1 leading-relaxed text-sm font-medium">{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 shadow-sm ring-2 ring-white dark:ring-slate-800
              ${msg.role === 'user' 
                ? 'bg-gradient-to-br from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 text-white' 
                : 'bg-gradient-to-br from-orange-400 to-orange-500 dark:from-orange-500 dark:to-orange-600 text-white'}`}>
              {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
            </div>
            
            <div className={`px-4 py-3 rounded-2xl max-w-[80%] text-sm overflow-hidden shadow-sm
              ${msg.role === 'user' 
                ? 'bg-blue-600 dark:bg-blue-700 text-white rounded-tr-sm' 
                : 'bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-600 rounded-tl-sm prose prose-sm prose-slate dark:prose-invert max-w-none'}`}>
              
              {msg.role === 'user' ? (
                msg.content
              ) : (
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Custom styling for markdown elements
                    p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2" {...props} />,
                    ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2" {...props} />,
                    li: ({node, ...props}) => <li className="mb-1" {...props} />,
                    code: ({node, ...props}) => (
                      <code className="bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 px-1 py-0.5 rounded text-xs font-mono" {...props} />
                    ),
                    pre: ({node, ...props}) => (
                      <pre className="bg-slate-800 dark:bg-slate-900 text-slate-100 p-3 rounded-lg overflow-x-auto my-2 text-xs border border-slate-700" {...props} />
                    ),
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
          </div>
        ))}
        {isLoading && messages.length > 0 && (
          <div className="flex gap-3">
            <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 shadow-sm bg-gradient-to-br from-orange-400 to-orange-500 dark:from-orange-500 dark:to-orange-600 text-white">
              <Bot size={18} />
            </div>
            <div className="px-4 py-3 rounded-2xl bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 shadow-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 rounded-b-xl">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your infrastructure..."
              className="w-full px-4 py-3 pr-12 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 transition-all"
              disabled={isLoading}
            />
          </div>
          <button 
            type="submit" 
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-blue-600 dark:bg-blue-500 text-white rounded-xl hover:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-sm hover:shadow-md disabled:hover:shadow-sm"
          >
            <Send size={18} />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
      </div>
    </div>
    </div>
  );
}
