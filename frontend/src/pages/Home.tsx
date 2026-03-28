import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [city, setCity] = useState('');
  const [filter, setFilter] = useState('rf');
  const [scope, setScope] = useState('local'); // Added scope state
  const [loading, setLoading] = useState(false);
  const [askAiInput, setAskAiInput] = useState('');
  const [askAiMessages, setAskAiMessages] = useState<any[]>([]);
  const [askAiLoading, setAskAiLoading] = useState(false);
  const [askAiModeHint, setAskAiModeHint] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const CITY_STORAGE_KEY = 'awaaz_user_city';

  useEffect(() => {
    const saved = localStorage.getItem(CITY_STORAGE_KEY);
    if (saved) setCity(saved);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (askAiMessages.length > 0) {
      const lastMsg = askAiMessages[askAiMessages.length - 1];
      if (!lastMsg.isUser) {
        // Scroll to the start of the latest AI response bubble
        const container = document.querySelector('.ask-ai-messages');
        const botWrappers = container?.querySelectorAll('.msg-wrapper--bot');
        const latestBotWrapper = botWrappers?.[botWrappers.length - 1];
        if (latestBotWrapper) {
          latestBotWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
          scrollToBottom();
        }
      } else {
        scrollToBottom();
      }
    }
  }, [askAiMessages]);

  const handleGetNews = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    localStorage.setItem(CITY_STORAGE_KEY, city);

    try {
      const params = new URLSearchParams({ filter, scope });
      if (city.trim()) params.set('city', city.trim());
      
      const response = await fetch(`/api/news?${params.toString()}`);
      const data = await response.json();

      if (data.success) {
        const displayCity = city.trim() || (scope === 'global' ? 'Global' : 'Kashmir');
        navigate('/results', { state: { newsData: data.data, city: displayCity } });
      } else {
        alert('Error: ' + (data.message || 'Failed to fetch news'));
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusFromContent = (content: string) => {
    const upperContent = content.toUpperCase();
    if (upperContent.includes('STATUS: VERIFIED') || upperContent.includes('STATUS:VERIFIED')) return 'verified';
    if (upperContent.includes('STATUS: FAKE_MISLEADING') || upperContent.includes('STATUS: FAKE') || upperContent.includes('STATUS:FAKE')) return 'fake';
    if (upperContent.includes('STATUS: UNVERIFIED') || upperContent.includes('STATUS:UNVERIFIED')) return 'unverified';
    
    // Fallback for non-AI formatted replies or common phrasing
    if (content.includes('✅ Verified') || upperContent.includes('OVERALL: VERIFIED')) return 'verified';
    if (content.includes('Likely False / Misleading') || upperContent.includes('OVERALL: FAKE')) return 'fake';
    if (content.includes('❓ Unverified') || upperContent.includes('OVERALL: UNVERIFIED')) return 'unverified';
    
    // Check if the overall verdict line mentions it without the keyword
    if (upperContent.includes('OVERALL:')) {
      const overall = upperContent.split('OVERALL:')[1];
      if (overall.includes('VERIFIED')) return 'verified';
      if (overall.includes('FAKE') || overall.includes('MISLEADING')) return 'fake';
      if (overall.includes('UNVERIFIED')) return 'unverified';
    }

    return null;
  };

  const appendMessage = (content: string, isUser: boolean, status: string | null = null, headlines: any[] = [], xOffer: boolean = false, headlinesCount: number = 0) => {
    setAskAiMessages(prev => [...prev, { content, isUser, status, headlines, xOffer, headlinesCount }]);
  };

  const handleAskAi = async () => {
    const text = askAiInput.trim();
    if (!text) return;

    setAskAiInput('');
    appendMessage(text, true);
    setAskAiLoading(true);

    try {
      const res = await fetch('/api/ask-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      
        if (data.success && data.reply) {
          const msgStatus = getStatusFromContent(data.reply);
          appendMessage(data.reply, false, msgStatus, data.headlines || [], data.offer_x_search && data.x_search_available, data.headlines_count || 0);
          updateModeHint(data);

        if (data.offer_x_search && data.x_search_available && (data.headlines_count || 0) === 0) {
            appendMessage("Google News had no article matches. Automatically searching on X.com...", false);
            await runXSearch(text, 0);
        }
      } else {
        appendMessage(data.message || 'Something went wrong.', false);
      }
    } catch (e) {
      appendMessage('Network error. Please try again.', false);
    } finally {
      setAskAiLoading(false);
    }
  };

  const runXSearch = async (originalText: string, headlinesCount: number) => {
    setAskAiLoading(true);
    try {
      const xRes = await fetch('/api/ask-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: originalText, 
          search_on_x: true,
          had_google_news_hits: headlinesCount > 0
        }),
      });
      const xData = await xRes.json();
      if (xData.success && xData.reply) {
        const xStatus = getStatusFromContent(xData.reply);
        appendMessage(xData.reply, false, xStatus, xData.headlines || [], false);
        setAskAiModeHint('X.com via Apify — social posts are not proof.');
      } else {
        appendMessage(xData.message || 'X search failed.', false, null, [], false);
      }
    } catch (err) {
      appendMessage('X search request failed.', false);
    } finally {
      setAskAiLoading(false);
    }
  };

  const updateModeHint = (data: any) => {
    if (data.mode === 'google_news+ai') {
      setAskAiModeHint(data.ai_provider === 'gemini' ? 'Google News + Gemini' : 'Google News + AI');
    } else if (data.mode === 'google_news') {
      setAskAiModeHint('Google News RSS');
    } else if (data.mode === 'x_com') {
      setAskAiModeHint('X.com results');
    }
  };

  const renderMessageContent = (content: string) => {
    // Simple markdown-like rendering for bold and links
    return content.split(/(\*\*.*?\*\*|\[.*?\]\(.*?\))/g).map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      const linkMatch = part.match(/\[(.*?)\]\((.*?)\)/);
      if (linkMatch) {
        return <a key={index} href={linkMatch[2]} target="_blank" rel="noopener noreferrer" className="text-primary fw-bold">{linkMatch[1]}</a>;
      }
      return part;
    });
  };

  const [activeTab, setActiveTab] = useState<'briefing' | 'ask'>('briefing');
  const [activeSection, setActiveSection] = useState<'search' | 'ai' | null>(null);

  return (
    <div className="container">
      {/* Mobile Tab Indicator */}
      <div className="mobile-tabs d-flex d-md-none mb-4 mx-auto" style={{ maxWidth: '400px' }}>
        <button 
          className={`tab-btn ${activeTab === 'briefing' ? 'active' : ''}`}
          onClick={() => { setActiveSection(null); setActiveTab('briefing'); }}
        >
          <i className="fas fa-newspaper"></i> Briefing
        </button>
        <button 
          className={`tab-btn ${activeTab === 'ask' ? 'active' : ''}`}
          onClick={() => { setActiveSection(null); setActiveTab('ask'); }}
        >
          <i className="fas fa-robot"></i> Ask AI
        </button>
      </div>

      <div className="row justify-content-center g-5">
        {/* News Briefing Column */}
        <div 
          className={`col-md-6 col-lg-5 interaction-column 
            ${activeTab !== 'briefing' ? 'd-none d-md-block' : 'd-block'}
            ${activeSection === 'search' ? 'is-active' : ''}
            ${activeSection === 'ai' ? 'is-blurred' : ''}
          `}
          onFocus={() => setActiveSection('search')}
          onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setActiveSection(null)}
        >
          <div className="card h-100">
            <div className="card-body">
              <div className="text-center mb-5">
                <div className="bg-icon-circle">
                  <i className="fas fa-search-location map-icon"></i>
                </div>
                <h2 className="card-title text-center">Search News</h2>
                <p className="text-muted">Get verified updates from your region</p>
              </div>

              <form onSubmit={handleGetNews}>
                <div className="mb-4">
                  <label className="form-label">Target City</label>
                  <input 
                    type="text" 
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleGetNews(e))}
                    className="form-control"
                    placeholder="e.g. Srinagar, Anantnag"
                  />
                  <p className="text-lighter small mt-2 mb-0">Preferences are synced locally.</p>
                </div>
                <div className="mb-4">
                  <label className="form-label">News Timeframe</label>
                  <select 
                    className="form-select"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    <option value="rf">Real-time (Last Hour)</option>
                    <option value="dn">Daily Summary</option>
                    <option value="wn">Weekly Review</option>
                    <option value="mn">Monthly Archive</option>
                  </select>
                </div>
                <div className="mb-4">
                  <label className="form-label">News Scope</label>
                  <select 
                    className="form-select"
                    value={scope}
                    onChange={(e) => setScope(e.target.value)}
                  >
                    <option value="local">Jammu & Kashmir (Local)</option>
                    <option value="global">International (Global)</option>
                  </select>
                </div>
                <button type="submit" className="btn btn-primary w-100" disabled={loading}>
                  {loading ? <i className="fas fa-circle-notch fa-spin"></i> : <i className="fas fa-bolt"></i>}
                  <span>{loading ? 'Curating news...' : 'Generate Briefing'}</span>
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Ask AI Column */}
        <div 
          className={`col-md-6 col-lg-5 interaction-column 
            ${activeTab !== 'ask' ? 'd-none d-md-block' : 'd-block'}
            ${activeSection === 'ai' ? 'is-active' : ''}
            ${activeSection === 'search' ? 'is-blurred' : ''}
          `}
          onFocus={() => setActiveSection('ai')}
          onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setActiveSection(null)}
        >
          <div className="card d-flex flex-column h-100">
            <div className="card-body d-flex flex-column" style={{ minHeight: '520px' }}>
              <div className={`ask-ai-header text-center mb-4 ${ (askAiMessages.length > 0 || askAiLoading) ? 'ask-ai-header--hidden' : '' }`}>
                <div className="bg-icon-circle">
                  <i className="fas fa-shield-virus map-icon"></i>
                </div>
                <h2 className="card-title text-center">Ask AI</h2>
                <p className="text-muted">Verify headlines & debunk misinformation</p>
              </div>

              <div 
                className="ask-ai-messages flex-grow-1" 
                style={{ 
                  display: askAiMessages.length > 0 || askAiLoading ? 'flex' : 'none'
                }}
              >
                {askAiMessages.map((msg, i) => (
                  <div 
                    key={i} 
                    className={`msg-wrapper ${msg.isUser ? 'msg-wrapper--user' : 'msg-wrapper--bot'}`}
                  >
                    <div className="msg-author">{msg.isUser ? 'You' : 'Awaaz AI'}</div>
                    <div className={`ask-ai-msg ${msg.isUser ? 'ask-ai-msg--user' : 'ask-ai-msg--bot'}`}>
                      {!msg.isUser && msg.status && (
                        <div className={`status-badge status-badge--${msg.status}`}>
                          {msg.status === 'verified' && <i className="fas fa-circle-check"></i>}
                          {msg.status === 'fake' && <i className="fas fa-triangle-exclamation"></i>}
                          {msg.status === 'unverified' && <i className="fas fa-circle-question"></i>}
                          {msg.status === 'verified' ? 'Verified Source' : msg.status === 'fake' ? 'Potential Misinfo' : 'Unverified Claim'}
                        </div>
                      )}
                      <div style={{ wordBreak: 'break-word' }}>
                        {renderMessageContent(msg.status 
                          ? msg.content.replace(/^(\*\*|)?STATUS:\s*.*?\n/im, '').replace(/\n?Overall:.*$/im, '') 
                          : msg.content)}
                      </div>
                      {!msg.isUser && (msg.status === 'verified' || msg.status === 'fake') && msg.headlines && msg.headlines.length > 0 && (
                        <div className="ask-ai-sources mt-3 pt-3" style={{ borderTop: '1px solid #edf2f7' }}>
                          <p className="small fw-bold text-muted mb-2">
                            <i className={`fas ${msg.status === 'verified' ? 'fa-book-open' : 'fa-info-circle'} me-2`}></i>
                            {msg.status === 'verified' ? 'Corroborating Articles:' : 'Evidence Sources:'}
                          </p>
                          <div className="d-flex flex-column gap-1">
                            {msg.headlines.map((item: any, idx: number) => (
                              <a 
                                key={idx} 
                                href={item.link || item.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="source-link"
                              >
                                <div className="source-title">{item.title || item.text}</div>
                                <div className="source-meta">{item.source || (item.author ? `@${item.author}` : 'Fact-Check Source')}</div>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                      {msg.xOffer && (
                        <div className="ask-ai-x-offer mt-3 shadow-sm border-0" style={{ margin: '0 0 -5px 0' }}>
                          <p className="small text-muted mb-2 fw-medium">
                            <i className="fa-brands fa-x-twitter me-2"></i> 
                            {msg.headlinesCount > 0 
                              ? "Want more perspectives from social media?" 
                              : "No official coverage found. Try social feed?"}
                          </p>
                          <button 
                            className="btn btn-outline-primary btn-sm py-2 px-3"
                            style={{ borderRadius: '10px', fontSize: '0.85rem' }}
                            onClick={() => {
                              // Find the most recent user question before this message
                              const userMsg = [...askAiMessages].reverse().find((m, idx, arr) => {
                                const originalIdx = arr.length - 1 - idx;
                                return originalIdx < askAiMessages.indexOf(msg) && m.isUser;
                              });
                              if (userMsg) runXSearch(userMsg.content, msg.headlinesCount);
                            }}
                          >
                            Investigate on X.com
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {askAiLoading && (
                  <div className="ask-ai-msg ask-ai-msg--bot shadow-sm">
                    <i className="fas fa-microchip fa-fade me-2"></i> Analyzing data points...
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>


              <div className="mt-auto">
                <div className="position-relative">
                  <textarea 
                    className="ask-ai-input"
                    value={askAiInput}
                    onChange={(e) => setAskAiInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleAskAi();
                      }
                    }}
                    placeholder="Verify news ..."
                    style={{ minHeight: '100px', paddingRight: '12px' }}
                  />
                  <div className="text-end mt-2">
                    <button 
                      className="btn-ask-ai" 
                      onClick={handleAskAi} 
                      disabled={askAiLoading}
                      style={{ padding: '12px 24px', borderRadius: '12px' }}
                    >
                      <i className="fas fa-sparkles me-2"></i> Ask AI
                    </button>
                  </div>
                </div>
                <p className="text-lighter text-center small mt-3 mb-0" style={{ fontWeight: 600 }}>
                  <i className="fas fa-info-circle me-1"></i> {askAiModeHint || `Awaaz AI Engine`}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
