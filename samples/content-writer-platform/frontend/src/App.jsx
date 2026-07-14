import { useState, useEffect, useRef } from 'react';
import { useThunderID, SignedIn, SignedOut, Loading, SignInButton, UserDropdown } from '@thunderid/react';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:1000';
const CHAT_ENDPOINT = `${API_BASE_URL.replace(/\/$/, '')}/chat`;
const API_KEY = import.meta.env.VITE_API_KEY || '';

function App() {
  const { getAccessToken } = useThunderID();
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I am your Brand Writing Assistant for ABC Company. You can ask me to help with formatting, typo editing, brainstorming ideas, or drafting public content like announcements and blogs. Public content will automatically be reviewed against our brand compliance guidelines!',
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

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;
    
    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', content: userMessage },
      { id: assistantMsgId, role: 'assistant', content: '', status: 'drafting' }
    ]);

    try {
      // Get OAuth access token from Thunder
      let token = '';
      try {
        token = await getAccessToken();
      } catch (authError) {
        console.warn("Could not retrieve access token:", authError);
      }

      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      };
      if (API_KEY) {
        headers['X-API-Key'] = API_KEY;
      }

      const response = await fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: headers,
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
        buffer = lines.pop();

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
                } else if (statusText === 'BYPASSED' || !statusText) {
                  statusVal = 'idle';
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
    <>
      {/* 1. Loading screen */}
      <Loading>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: '1rem', background: 'var(--bg-gradient)', color: 'var(--text-main)' }}>
          <i className="fa-solid fa-circle-notch fa-spin" style={{ fontSize: '3rem', color: 'var(--primary)' }}></i>
          <p>Loading session information from Thunder...</p>
        </div>
      </Loading>

      {/* 2. Unauthenticated Login screen */}
      <SignedOut>
        <div className="app-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div className="login-box glass" style={{ padding: '3rem', maxWidth: '450px', width: '100%', display: 'flex', flexDirection: 'column', gap: '2rem', textAlign: 'center' }}>
            <div className="logo" style={{ fontSize: '2rem', justifyContent: 'center' }}>
              <i className="fa-solid fa-file-signature"></i>
              <span>Content Writer Hub</span>
            </div>
            <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>
              Welcome to the AI Content Writer Platform. Please log in using the Thunder Identity Provider to access the chatbot.
            </p>
            <SignInButton className="btn" style={{ width: '100%', display: 'flex', gap: '0.5rem', justifyContent: 'center', alignItems: 'center' }}>
              <i className="fa-solid fa-right-to-bracket"></i>
              <span>Log in with Thunder</span>
            </SignInButton>
          </div>
        </div>
      </SignedOut>

      {/* 3. Authenticated Chat Workspace */}
      <SignedIn>
        <div className="app-container">
          <header className="glass">
            <div className="logo">
              <i className="fa-solid fa-file-signature"></i>
              <span>Content Writer Hub</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
              <div className="status-badge">
                <div className="status-dot"></div>
                <span>Authenticated</span>
              </div>
              <UserDropdown />
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
                placeholder="Ask me anything, or draft an announcement (e.g. 'Draft an announcement for a new cloud host...')"
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
      </SignedIn>
    </>
  );
}

export default App;
