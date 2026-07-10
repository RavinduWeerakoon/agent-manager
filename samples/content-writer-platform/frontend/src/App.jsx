import { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:1000';
const CHAT_ENDPOINT = `${API_BASE_URL.replace(/\/$/, '')}/chat`;

function App() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I am your Writing Assistant. Provide me with a topic, and I will write a product announcement and run it through our legal compliance check.',
      status: 'idle'
    }
  ]);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    const userMessage = input.trim();
    setInput('');
    setIsGenerating(true);

    // 1. Add User Message
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;
    
    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', content: userMessage },
      { id: assistantMsgId, role: 'assistant', content: '', status: 'drafting' }
    ]);

    try {
      const response = await fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`Server returned error: ${response.status} ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedDraft = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Save trailing partial line

        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.replace('data: ', '').trim());
              
              if (parsed.type === 'token') {
                accumulatedDraft += parsed.content;
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantMsgId 
                      ? { ...msg, content: accumulatedDraft } 
                      : msg
                  )
                );
              } else if (parsed.type === 'status') {
                const statusText = parsed.content;
                let statusVal = 'idle';
                let finalContent = accumulatedDraft;

                if (statusText === 'APPROVED') {
                  statusVal = 'approved';
                } else {
                  statusVal = 'rejected';
                  finalContent = accumulatedDraft + '\n\n---\n' + statusText;
                }

                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantMsgId 
                      ? { 
                          ...msg, 
                          content: finalContent,
                          status: statusVal 
                        } 
                      : msg
                  )
                );
              }
            } catch (e) {
              console.error('Failed to parse SSE JSON line: ', line, e);
            }
          }
        }
      }
    } catch (error) {
      setMessages(prev => 
        prev.map(msg => 
          msg.id === assistantMsgId 
            ? { 
                ...msg, 
                content: `💥 Error: ${error.message}`,
                status: 'rejected' 
              } 
            : msg
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="app-container">
      <header className="glass">
        <div className="logo">
          <i className="fa-solid fa-file-signature"></i>
          <span>Content Writer Hub</span>
        </div>
        <div className="status-badge">
          <div className="status-dot"></div>
          <span>Connected</span>
        </div>
      </header>

      {/* Main Chat Workspace */}
      <div className="chat-workspace">
        <div className="messages-container">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row ${msg.role}`}>
              <div className="avatar">
                {msg.role === 'user' ? (
                  <i className="fa-solid fa-user"></i>
                ) : (
                  <i className="fa-solid fa-robot"></i>
                )}
              </div>
              <div className={`message-bubble glass ${msg.status || ''}`}>
                <div className="message-content">{msg.content}</div>
                {msg.status === 'drafting' && (
                  <div className="loading-dots">
                    <span>.</span><span>.</span><span>.</span>
                  </div>
                )}
                {msg.status && msg.status !== 'idle' && msg.status !== 'drafting' && (
                  <div className={`compliance-tag ${msg.status}`}>
                    {msg.status === 'approved' ? (
                      <><i className="fa-solid fa-circle-check"></i> Approved</>
                    ) : (
                      <><i className="fa-solid fa-triangle-exclamation"></i> Rejected</>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <form onSubmit={handleSend} className="input-form glass">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a product announcement topic (e.g. 'A new cloud host...')"
            disabled={isGenerating}
          />
          <button type="submit" className="send-btn" disabled={isGenerating || !input.trim()}>
            {isGenerating ? (
              <i className="fa-solid fa-spinner fa-spin"></i>
            ) : (
              <i className="fa-solid fa-paper-plane"></i>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
