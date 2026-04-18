import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [tools, setTools] = useState([]);
  const [workspaceConfig, setWorkspaceConfig] = useState(null);
  const [llmInfo, setLlmInfo] = useState(null);

  useEffect(() => {
    // Load available tools and config
    loadTools();
    loadHealthInfo();
  }, []);

  const loadTools = async () => {
    try {
      const response = await axios.get('http://localhost:8000/tools');
      setTools(response.data);
    } catch (error) {
      console.error('Error loading tools:', error);
    }
  };

  const loadHealthInfo = async () => {
    try {
      const response = await axios.get('http://localhost:8000/health');
      setWorkspaceConfig(response.data.workspace);
      setLlmInfo(response.data.llm);
    } catch (error) {
      console.error('Error loading health info:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputValue
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/chat', {
        messages: [userMessage]
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Error: Could not process your request. Please check the server logs.'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Local Agent Tool</h1>
        <p>Ask me to help with file operations, code execution, HTTP requests, and more!</p>
      </header>
      
      <div className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <strong>{message.role === 'user' ? 'You' : 'Agent'}:</strong> {message.content}
            </div>
          ))}
          {isLoading && (
            <div className="message assistant">
              <strong>Agent:</strong> Thinking...
            </div>
          )}
        </div>
        
        <div className="input-container">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here (e.g., '>> hilf mir, CSV zu laden')"
            rows="3"
          />
          <button onClick={sendMessage} disabled={isLoading}>
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>

      <div className="config-section">
        <h2>Configuration</h2>
        {workspaceConfig && (
          <div className="config-card">
            <h3>Workspace</h3>
            <p><strong>Path:</strong> {workspaceConfig.workspace_path}</p>
            <p><strong>Read-only:</strong> {workspaceConfig.read_only ? 'Yes' : 'No'}</p>
            <p><strong>Max File Size:</strong> {workspaceConfig.max_file_size_mb}MB</p>
            <p><strong>Execution Timeout:</strong> {workspaceConfig.execution_timeout}s</p>
          </div>
        )}
        {llmInfo && (
          <div className="config-card">
            <h3>LLM Provider</h3>
            <p><strong>Provider:</strong> {llmInfo.provider}</p>
            <p><strong>Model:</strong> {llmInfo.model}</p>
            <p><strong>Available:</strong> {llmInfo.available ? 'Yes' : 'No'}</p>
          </div>
        )}
      </div>

      <div className="tools-section">
        <h2>Available Tools</h2>
        <div className="tools-grid">
          {tools.map((tool, index) => (
            <div key={index} className="tool-card">
              <h3>{tool.name}</h3>
              <p>{tool.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;