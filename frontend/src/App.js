import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import './App.css';
import LanguageSelector from './components/LanguageSelector';

const API_URL = process.env.REACT_APP_API_URL || `${window.location.protocol}//${window.location.host}`;

function App() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [tools, setTools] = useState([]);
  const [workspaceConfig, setWorkspaceConfig] = useState(null);
  const [llmInfo, setLlmInfo] = useState(null);
  const [connected, setConnected] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [refactorCode, setRefactorCode] = useState('');
  const [refactorInstructions, setRefactorInstructions] = useState('');
  const [completions, setCompletions] = useState([]);
  const [agentRunning, setAgentRunning] = useState(false);
  const [agentLogs, setAgentLogs] = useState([]);
  const [settings, setSettings] = useState({
    llmUrl: 'http://localhost:11434',
    llmModel: 'llama3.2',
    maxTokens: 4096,
    temperature: 0.7,
    autoComplete: false,
    reasoningMode: 'tao',
    provider: 'auto'
  });
  
  const [providers, setProviders] = useState({});
  const [checkingProviders, setCheckingProviders] = useState(false);
  const [expandedProviders, setExpandedProviders] = useState({});
  const [testingProviders, setTestingProviders] = useState({});
  const [providerKeys, setProviderKeys] = useState({});
  const [savingProviders, setSavingProviders] = useState({});
  
  const providerList = [
    { id: 'ollama', name: 'Ollama', placeholder: 'http://localhost:11434' },
    { id: 'openai', name: 'OpenAI', placeholder: 'sk-...' },
    { id: 'anthropic', name: 'Anthropic', placeholder: 'sk-ant-...' },
    { id: 'groq', name: 'Groq', placeholder: 'gsk_...' },
    { id: 'huggingface', name: 'Hugging Face', placeholder: 'hf_...' },
    { id: 'togetherai', name: 'Together AI', placeholder: 'API Key' },
    { id: 'mistral', name: 'Mistral AI', placeholder: 'API Key' },
    { id: 'google', name: 'Google AI', placeholder: 'API Key' }
  ];
  
  const reasoningModes = [
    { value: 'tao', label: 'TAO', desc: 'Thought-Action-Observation (klassisch)' },
    { value: 'tot', label: 'ToT', desc: 'Tree of Thoughts - Verzweigte Pfade' },
    { value: 'got', label: 'GoT', desc: 'Graph of Thoughts - Vernetzt' },
    { value: 'reflexion', label: 'Reflexion', desc: 'Mit Error Memory' },
    { value: 'plan_solve', label: 'Plan-Solve', desc: 'Erst Plan, dann ausführen' },
    { value: 'pot', label: 'PoT', desc: 'Code as Thought' },
    { value: 'voyager', label: 'Voyager', desc: 'Erfahrungsbasiert' }
  ];
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    loadHealthInfo();
    loadTools();
    loadChatHistory();
    loadProviders();
  }, []);
  
  const loadProviders = async () => {
    try {
      const response = await axios.get(`${API_URL}/providers`);
      setProviders(response.data);
    } catch (error) {
      console.error('Error loading providers:', error);
    }
  };
  
  const checkProviders = async () => {
    setCheckingProviders(true);
    try {
      const response = await axios.post(`${API_URL}/providers/check`);
      setProviders(response.data);
    } catch (error) {
      console.error('Error checking providers:', error);
    }
    setCheckingProviders(false);
  };

  const toggleProviderExpand = (providerId) => {
    setExpandedProviders(prev => ({
      ...prev,
      [providerId]: !prev[providerId]
    }));
  };

  const testProviderKey = async (providerId) => {
    const apiKey = providerKeys[providerId];
    if (!apiKey) return;
    
    setTestingProviders(prev => ({ ...prev, [providerId]: true }));
    try {
      const response = await axios.post(`${API_URL}/api/llm/keys/test`, {
        provider_id: providerId,
        api_key: apiKey
      });
      
      if (response.data.valid) {
        setProviders(prev => ({
          ...prev,
          [providerId]: {
            ...prev[providerId],
            status: 'available',
            latencyMs: response.data.latency,
            models: response.data.models,
            hasApiKey: true
          }
        }));
        setProviderKeys(prev => ({ ...prev, [providerId]: '' }));
      } else {
        alert(`Test fehlgeschlagen: ${response.data.error}`);
      }
    } catch (error) {
      alert(`Test fehlgeschlagen: ${error.message}`);
    }
    setTestingProviders(prev => ({ ...prev, [providerId]: false }));
  };

  const saveProviderKey = async (providerId) => {
    const apiKey = providerKeys[providerId];
    if (!apiKey) return;
    
    setSavingProviders(prev => ({ ...prev, [providerId]: true }));
    try {
      const response = await axios.post(`${API_URL}/api/llm/keys`, {
        provider_id: providerId,
        api_key: apiKey
      });
      
      if (response.data.success) {
        setProviders(prev => ({
          ...prev,
          [providerId]: {
            ...prev[providerId],
            status: 'unavailable',
            hasApiKey: true
          }
        }));
        setProviderKeys(prev => ({ ...prev, [providerId]: '' }));
        loadProviders();
      } else {
        alert(`Speichern fehlgeschlagen: ${response.data.error}`);
      }
    } catch (error) {
      alert(`Speichern fehlgeschlagen: ${error.message}`);
    }
    setSavingProviders(prev => ({ ...prev, [providerId]: false }));
  };

  const removeProviderKey = async (providerId) => {
    try {
      const response = await axios.delete(`${API_URL}/api/llm/keys/${providerId}`);
      if (response.data.success) {
        setProviders(prev => ({
          ...prev,
          [providerId]: {
            ...prev[providerId],
            status: 'unconfigured',
            hasApiKey: false,
            latencyMs: null,
            models: []
          }
        }));
      }
    } catch (error) {
      alert(`Entfernen fehlgeschlagen: ${error.message}`);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const savedLang = localStorage.getItem('language') || 'ar';
    setLanguageDirection(savedLang);
  }, []);

  const setLanguageDirection = (lang) => {
    if (lang === 'ar') {
      document.documentElement.dir = 'rtl';
      document.documentElement.lang = 'ar';
    } else {
      document.documentElement.dir = 'ltr';
      document.documentElement.lang = lang;
    }
  };
  
  const changeLanguage = (lang) => {
    localStorage.setItem('language', lang);
    setLanguageDirection(lang);
    window.location.reload();
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadHealthInfo = async () => {
    try {
      const response = await axios.get(`${API_URL}/health`, { timeout: 3000 });
      setWorkspaceConfig(response.data.workspace);
      setLlmInfo(response.data.llm);
      setConnected(response.data.llm?.available || false);
    } catch (error) {
      setConnected(false);
    }
  };

  const loadTools = async () => {
    try {
      const response = await axios.get(`${API_URL}/tools`);
      setTools(response.data);
    } catch (error) {
      console.error('Error loading tools:', error);
    }
  };

  const loadChatHistory = () => {
    const history = localStorage.getItem('chatHistory');
    if (history) {
      setChatHistory(JSON.parse(history));
    }
  };

  const saveChatHistory = (newHistory) => {
    localStorage.setItem('chatHistory', JSON.stringify(newHistory));
    setChatHistory(newHistory);
  };

  const startNewChat = () => {
    const newChat = {
      id: Date.now(),
      title: 'New Chat',
      messages: [],
      timestamp: new Date().toISOString()
    };
    const updated = [newChat, ...chatHistory];
    saveChatHistory(updated);
    setActiveChat(newChat.id);
    setMessages([]);
  };

  const selectChat = (chatId) => {
    const chat = chatHistory.find(c => c.id === chatId);
    if (chat) {
      setActiveChat(chatId);
      setMessages(chat.messages || []);
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputValue('');
    setIsLoading(true);

    const currentChatId = activeChat || Date.now();
    if (!activeChat) {
      setActiveChat(currentChatId);
      const newChat = {
        id: currentChatId,
        title: inputValue.slice(0, 30) + (inputValue.length > 30 ? '...' : ''),
        messages: newMessages,
        timestamp: new Date().toISOString()
      };
      const updated = [newChat, ...chatHistory];
      saveChatHistory(updated);
    } else {
      const updated = chatHistory.map(c => 
        c.id === activeChat 
          ? { ...c, messages: newMessages, timestamp: new Date().toISOString() }
          : c
      );
      saveChatHistory(updated);
    }

    try {
      const response = await axios.post(`${API_URL}/chat`, {
        messages: [userMessage]
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString()
      };

      const finalMessages = [...newMessages, assistantMessage];
      setMessages(finalMessages);

      const updatedHistory = chatHistory.map(c => 
        c.id === currentChatId 
          ? { ...c, messages: finalMessages, timestamp: new Date().toISOString() }
          : c
      );
      saveChatHistory(updatedHistory);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'Error: Could not process your request. Please check the server.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const runAnalysis = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${API_URL}/analyze`, {});
      setAnalysisResult(response.data);
    } catch (error) {
      setAnalysisResult({ summary: 'Error analyzing code', issues: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const runRefactor = async () => {
    if (!refactorCode.trim()) {
      alert('Enter code to refactor');
      return;
    }
    setIsLoading(true);
    try {
      const response = await axios.post(`${API_URL}/refactor`, {
        code: refactorCode,
        instructions: refactorInstructions
      });
      setAnalysisResult({ refactored: response.data.refactored });
    } catch (error) {
      setAnalysisResult({ refactored: 'Error: ' + error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const getCompletions = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${API_URL}/completion`, {});
      setCompletions(response.data.suggestions || []);
    } catch (error) {
      setCompletions(['Error getting completions']);
    } finally {
      setIsLoading(false);
    }
  };

  const startAgent = async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API_URL}/agent/start`, {});
      setAgentRunning(true);
      addAgentLog('Agent started');
    } catch (error) {
      addAgentLog('Error: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const stopAgent = async () => {
    setIsLoading(true);
    try {
      await axios.post(`${API_URL}/agent/stop`, {});
      setAgentRunning(false);
      addAgentLog('Agent stopped');
    } catch (error) {
      addAgentLog('Error: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const addAgentLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    setAgentLogs(prev => [...prev, { timestamp, message }]);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleQuickAction = (action) => {
    setInputValue(action);
    sendMessage();
  };

  const handleRefactorTemplate = (template) => {
    const templates = {
      'extract': 'استخراج هذا الكود إلى دالة منفصلة',
      'rename': 'إعادة تسمية المتغيرات والدوال',
      'inline': 'دمج المتغير المباشر',
      'optimize': 'تحسين الأداء وإزالة الكود المكر',
      'clean': 'تنظيف الكود وإزالة الأسطر غير المستخدمة'
    };
    setRefactorInstructions(templates[template] || '');
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return date.toLocaleDateString();
  };

  const renderMessageContent = (content) => {
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    const parts = content.split(codeBlockRegex);
    
    return parts.map((part, i) => {
      if (i % 3 === 0 && part) {
        return <p key={i}>{part}</p>;
      }
      if (i % 3 === 2) {
        const lang = parts[i - 1] || 'code';
        return (
          <div key={i} className="code-block">
            <div className="code-block-header">
              <span>{lang}</span>
            </div>
            <pre><code>{part}</code></pre>
          </div>
        );
      }
      return null;
    });
  };

  const tabs = [
    { id: 'chat', label: t('nav.chat'), icon: '💬' },
    { id: 'analyze', label: t('nav.analyze'), icon: '🔍' },
    { id: 'refactor', label: t('nav.refactor'), icon: '🔧' },
    { id: 'completion', label: t('nav.completion'), icon: '✨' },
    { id: 'agent', label: t('nav.agent'), icon: '⚡' },
    { id: 'settings', label: t('nav.settings'), icon: '⚙️' },
  ];

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>
          <div className="header-logo">🤖</div>
          {t('app.title')}
        </h1>
        <LanguageSelector />
      </header>

      {/* Navigation Tabs */}
      <nav className="nav-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Config Info */}
      <div className="config-info">
        <span><strong>{t('config.workspace')}:</strong> {workspaceConfig?.workspace_path || t('config.notConfigured')}</span>
        <span><strong>{t('config.model')}:</strong> {llmInfo?.provider || 'N/A'}/{llmInfo?.model || 'N/A'}</span>
        <span><strong>{t('config.tools')}:</strong> {tools.length} {t('config.available')}</span>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>{t('chat.history')}</h2>
            <div className="sidebar-actions">
              <button className="sidebar-btn" onClick={startNewChat}>+ {t('chat.newChat')}</button>
            </div>
          </div>
          <div className="chat-history">
            {chatHistory.length === 0 ? (
              <div className="empty-state">{t('chat.noChats')}</div>
            ) : (
              chatHistory.map(chat => (
                <div 
                  key={chat.id} 
                  className={`chat-history-item ${activeChat === chat.id ? 'active' : ''}`}
                  onClick={() => selectChat(chat.id)}
                >
                  <div className="chat-history-item-title">{chat.title}</div>
                  <div className="chat-history-item-time">{formatTime(chat.timestamp)}</div>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Panel Content */}
        <main className="chat-panel">
          {/* Chat View */}
          {activeTab === 'chat' && (
            <>
              <div className="quick-actions">
                <div className="quick-action" onClick={() => handleQuickAction('Explain this code')}>📖 {t('chat.quickActions.explain')}</div>
                <div className="quick-action" onClick={() => handleQuickAction('Find bugs')}>🐛 {t('chat.quickActions.findBugs')}</div>
                <div className="quick-action" onClick={() => handleQuickAction('Optimize this code')}>⚡ {t('chat.quickActions.optimize')}</div>
                <div className="quick-action" onClick={() => handleQuickAction('Add comments')}>💬 {t('chat.quickActions.addComments')}</div>
              </div>
              <div className="chat-messages">
                {messages.length === 0 && !isLoading && (
                  <div className="empty-state">
                    <div className="empty-state-icon">💬</div>
                    {t('chat.startChat')}
                  </div>
                )}
                {messages.map((message, index) => (
                  <div key={index} className={`message ${message.role}`}>
                    <div className="message-header">
                      <div className="avatar">{message.role === 'user' ? '👤' : '🤖'}</div>
                      <span className="name">{message.role === 'user' ? t('chat.you') : t('chat.ai')}</span>
                    </div>
                    <div className="message-content">
                      {renderMessageContent(message.content)}
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="message assistant">
                    <div className="message-header">
                      <div className="avatar">🤖</div>
                      <span className="name">{t('chat.ai')}</span>
                    </div>
                    <div className="message-content">
                      <div className="loading"><div className="loading-spinner"></div>{t('chat.thinking')}</div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              <div className="input-area">
                <div className="input-wrapper">
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={t('chat.placeholder')}
                  />
                  <button className="send-btn" onClick={sendMessage} disabled={isLoading || !inputValue.trim()}>
                    {isLoading ? '...' : t('chat.send')}
                  </button>
                </div>
              </div>
            </>
          )}

          {/* Analyze View */}
          {activeTab === 'analyze' && (
            <div className="analysis-view">
              {analysisResult ? (
                <>
                  {analysisResult.summary && (
                    <div className="analysis-section">
                      <h3>{t('analyze.summary')}</h3>
                      <p>{analysisResult.summary}</p>
                    </div>
                  )}
                  {analysisResult.issues && (
                    <div className="analysis-section">
                      <h3>{t('analyze.issues')}</h3>
                      <p>{analysisResult.issues}</p>
                    </div>
                  )}
                  {analysisResult.suggestions && (
                    <div className="analysis-section">
                      <h3>{t('analyze.suggestions')}</h3>
                      <p>{analysisResult.suggestions}</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-state">
                  <div className="empty-state-icon">🔍</div>
                  {t('analyze.clickToAnalyze')}
                </div>
              )}
              <button className="action-btn" onClick={runAnalysis} disabled={isLoading}>
                {isLoading ? t('analyze.running') : t('analyze.run')}
              </button>
            </div>
          )}

          {/* Refactor View */}
          {activeTab === 'refactor' && (
            <div className="refactor-view">
              <div className="refactor-templates">
                <div className="refactor-template" onClick={() => handleRefactorTemplate('extract')}>📤 {t('refactor.templates.extract')}</div>
                <div className="refactor-template" onClick={() => handleRefactorTemplate('rename')}>✏️ {t('refactor.templates.rename')}</div>
                <div className="refactor-template" onClick={() => handleRefactorTemplate('inline')}>📥 {t('refactor.templates.inline')}</div>
                <div className="refactor-template" onClick={() => handleRefactorTemplate('optimize')}>⚡ {t('refactor.templates.optimize')}</div>
                <div className="refactor-template" onClick={() => handleRefactorTemplate('clean')}>🧹 {t('refactor.templates.clean')}</div>
              </div>
              <div className="refactor-original">
                <label>{t('refactor.originalCode')}</label>
                <textarea
                  value={refactorCode}
                  onChange={(e) => setRefactorCode(e.target.value)}
                  placeholder={t('refactor.codePlaceholder')}
                />
              </div>
              <div className="refactor-instructions">
                <label>{t('refactor.instructions')}</label>
                <textarea
                  value={refactorInstructions}
                  onChange={(e) => setRefactorInstructions(e.target.value)}
                  placeholder={t('refactor.instructionsPlaceholder')}
                />
              </div>
              {analysisResult?.refactored && (
                <div className="analysis-section">
                  <h3>{t('refactor.result')}</h3>
                  <pre><code>{analysisResult.refactored}</code></pre>
                </div>
              )}
              <button className="action-btn" onClick={runRefactor} disabled={isLoading}>
                {isLoading ? t('refactor.running') : t('refactor.run')}
              </button>
            </div>
          )}

          {/* Completion View */}
          {activeTab === 'completion' && (
            <div className="completion-view">
              <button className="action-btn" onClick={getCompletions} disabled={isLoading}>
                {isLoading ? t('completion.getting') : t('completion.get')}
              </button>
              <div className="completion-suggestions">
                {completions.map((completion, i) => (
                  <div key={i} className="completion-item">
                    <code>{completion}</code>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agent View */}
          {activeTab === 'agent' && (
            <div className="agent-view">
              <div className="agent-status-card">
                <h3>{t('agent.title')}</h3>
                <div className="agent-status-indicator">
                  <span className="status-dot" style={{ background: agentRunning ? 'var(--status-connected)' : 'var(--status-disconnected)' }}></span>
                  <span>{agentRunning ? t('agent.running') : t('agent.stopped')}</span>
                </div>
              </div>
              <div className="agent-actions">
                <button className="action-btn" onClick={startAgent} disabled={isLoading || agentRunning}>
                  {isLoading ? t('agent.starting') : t('agent.start')}
                </button>
                <button className="action-btn secondary" onClick={stopAgent} disabled={isLoading || !agentRunning}>
                  {isLoading ? t('agent.stopping') : t('agent.stop')}
                </button>
              </div>
              <div className="agent-info">
                <div className="agent-info-item">
                  <label>{t('agent.workspace')}:</label>
                  <span>{workspaceConfig?.workspace_path || t('config.notConfigured')}</span>
                </div>
                <div className="agent-info-item">
                  <label>{t('agent.model')}:</label>
                  <span>{llmInfo?.provider || 'N/A'}/{llmInfo?.model || 'N/A'}</span>
                </div>
              </div>
              <div className="agent-logs">
                {agentLogs.length === 0 ? (
                  <div style={{ padding: '16px', color: 'var(--text-secondary)', textAlign: 'center' }}>
                    {t('agent.noLogs')}
                  </div>
                ) : (
                  agentLogs.map((log, i) => (
                    <div key={i} className="agent-log-item">
                      <span className="log-timestamp">[{log.timestamp}]</span> {log.message}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Settings View */}
          {activeTab === 'settings' && (
            <div className="settings-view">
              <div className="settings-section">
                <h3>🧠 Reasoning-Modus</h3>
                <div className="settings-group">
                  <label>Modus:</label>
                  <select 
                    value={settings.reasoningMode}
                    onChange={(e) => setSettings({...settings, reasoningMode: e.target.value})}
                  >
                    {reasoningModes.map(mode => (
                      <option key={mode.value} value={mode.value}>
                        {mode.label} - {mode.desc}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              
              {/* Provider Management */}
              <div className="settings-section">
                <h3>🔑 API Provider</h3>
                <div className="provider-list">
                  {providerList.map(provider => (
                    <div key={provider.id} className={`provider-accordion ${expandedProviders[provider.id] ? 'expanded' : ''}`}>
                      <div className="provider-header" onClick={() => toggleProviderExpand(provider.id)}>
                        <div className="provider-info">
                          <span className="provider-name">{provider.name}</span>
                          <span className={`provider-status ${providers[provider.id]?.status}`}>
                            {providers[provider.id]?.hasApiKey 
                              ? (providers[provider.id]?.status === 'available' ? '✓ Verbunden' : '✗ Nicht verfügbar')
                              : '○ Nicht konfiguriert'}
                          </span>
                        </div>
                        <div className="provider-meta">
                          {providers[provider.id]?.latencyMs && (
                            <span className="provider-latency">{providers[provider.id].latencyMs}ms</span>
                          )}
                          <span className="expand-icon">{expandedProviders[provider.id] ? '▼' : '▶'}</span>
                        </div>
                      </div>
                      {expandedProviders[provider.id] && (
                        <div className="provider-details">
                          <div className="provider-input-row">
                            <label>API Key:</label>
                            <input 
                              type="password"
                              value={providerKeys[provider.id] || ''}
                              onChange={(e) => setProviderKeys(prev => ({ ...prev, [provider.id]: e.target.value }))}
                              placeholder={provider.placeholder}
                            />
                          </div>
                          <div className="provider-buttons">
                            <button 
                              className="btn-test"
                              onClick={() => testProviderKey(provider.id)}
                              disabled={testingProviders[provider.id] || !providerKeys[provider.id]}
                            >
                              {testingProviders[provider.id] ? '⏳ Teste...' : '🧪 Test'}
                            </button>
                            <button 
                              className="btn-save"
                              onClick={() => saveProviderKey(provider.id)}
                              disabled={savingProviders[provider.id] || !providerKeys[provider.id]}
                            >
                              {savingProviders[provider.id] ? '⏳ Speichere...' : '💾 Speichern'}
                            </button>
                            {providers[provider.id]?.hasApiKey && (
                              <button 
                                className="btn-remove"
                                onClick={() => removeProviderKey(provider.id)}
                              >
                                🗑️ Entfernen
                              </button>
                            )}
                          </div>
                          {providers[provider.id]?.models?.length > 0 && (
                            <div className="provider-models">
                              <label>Verfügbare Models:</label>
                              <select>
                                {providers[provider.id].models.map(m => (
                                  <option key={m} value={m}>{m}</option>
                                ))}
                              </select>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <button 
                  className="btn-check-providers"
                  onClick={checkProviders}
                  disabled={checkingProviders}
                >
                  {checkingProviders ? '🔄 Prüfe...' : '🔄 Alle Provider prüfen'}
                </button>
              </div>
              
              <div className="settings-section">
                <h3>⚙️ {t('settings.aiSettings')}</h3>
                <div className="settings-group">
                  <label>LLM Provider:</label>
                  <select 
                    value={settings.provider}
                    onChange={(e) => setSettings({...settings, provider: e.target.value})}
                  >
                    <option value="auto">⚡ Auto (Schnellster)</option>
                    {providerList.filter(p => providers[p.id]?.hasApiKey).map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div className="settings-group">
                  <label>{t('settings.model')}</label>
                  <select 
                    value={settings.llmModel}
                    onChange={(e) => setSettings({...settings, llmModel: e.target.value})}
                  >
                    <option value="llama3.2">Llama 3.2</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                    <option value="llama-3.1-70b-versatile">Llama 3.1 70B</option>
                  </select>
                </div>
              </div>
              <div className="settings-section">
                <h3>⚡ {t('settings.agentSettings')}</h3>
                <div className="settings-group">
                  <label>{t('settings.maxTokens')}</label>
                  <input 
                    type="number" 
                    value={settings.maxTokens}
                    onChange={(e) => setSettings({...settings, maxTokens: parseInt(e.target.value)})}
                    min="512" 
                    max="8192" 
                  />
                </div>
                <div className="settings-group">
                  <label>{t('settings.temperature')}: {settings.temperature}</label>
                  <input 
                    type="range" 
                    min="0" 
                    max="1" 
                    step="0.1" 
                    value={settings.temperature}
                    onChange={(e) => setSettings({...settings, temperature: parseFloat(e.target.value)})}
                  />
                </div>
                <div className="settings-group">
                  <label className="checkbox-label">
                    <input 
                      type="checkbox" 
                      checked={settings.autoComplete}
                      onChange={(e) => setSettings({...settings, autoComplete: e.target.checked})}
                    />
                    {t('settings.autoComplete')}
                  </label>
                </div>
              </div>
              <div className="settings-section">
                <h3>⌨️ {t('settings.shortcuts')}</h3>
                <div className="shortcuts-list">
                  <div className="shortcut-item"><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>C</kbd> <span>{t('settings.shortcutKeys.openChat')}</span></div>
                  <div className="shortcut-item"><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd> <span>{t('settings.shortcutKeys.analyzeCode')}</span></div>
                  <div className="shortcut-item"><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd> <span>{t('settings.shortcutKeys.refactor')}</span></div>
                </div>
              </div>
              <button className="action-btn" onClick={() => alert(t('settings.saved'))}>
                {t('settings.save')}
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Status Bar */}
      <footer className="status-bar">
        <div className={`status-bar-item ${connected ? 'connected' : 'disconnected'}`}>
          <span className="status-dot"></span>
          {connected ? t('status.connected') : t('status.disconnected')}
        </div>
        <div className="status-bar-item">{llmInfo?.provider || 'N/A'}:{llmInfo?.model || 'N/A'}</div>
        <div className="status-bar-item">{workspaceConfig?.workspace_path || t('config.notConfigured')}</div>
        <div className="status-bar-item" style={{ marginLeft: 'auto' }}>{chatHistory.length} {t('status.chats')}</div>
      </footer>
    </div>
  );
}

export default App;