import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Helper debug function
const debug = (message, data) => {
  console.log(`[Chatbot Debug] ${message}`, data || '');
};

// Backend API URL - easier to change if needed
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
console.log('Chatbot using API URL:', API_BASE_URL);

export const Chatbot = ({ onEventAdded }) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      text: "Hi! I'm your calendar assistant. Tell me about an event you want to add to your calendar.", 
      sender: 'bot' 
    },
    {
      id: 2,
      text: "Here are some examples of what you can say:\n• \"Schedule a meeting with Mike tomorrow at 2pm\"\n• \"Reschedule my Friday meeting to Monday at 10am\"\n• \"Delete the meeting with Bocheng on Sunday\"\n• \"Cancel my coffee meeting on Friday\"",
      sender: 'bot'
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState('unknown');
  const [apiTestLoading, setApiTestLoading] = useState(false);

  // Check backend health on component mount and set up periodic health checks
  useEffect(() => {
    checkBackendHealth();
    
    // Set up periodic health checks every 10 seconds
    const healthCheckInterval = setInterval(() => {
      if (backendStatus !== 'connected') {
        debug('Attempting automatic reconnection to backend');
        checkBackendHealth();
      }
    }, 10000);
    
    // Clean up the interval on component unmount
    return () => clearInterval(healthCheckInterval);
  }, [backendStatus]);

  const checkBackendHealth = async () => {
    try {
      debug('Checking backend health');
      const response = await axios.get(`${API_BASE_URL}/api/health`, { timeout: 5000 });
      debug('Backend health response', response.data);
      setBackendStatus(response.data.status === 'ok' ? 'connected' : 'error');
      
      // Add a system message about API key if needed
      if (!response.data.api_key_configured) {
        setMessages(prev => [
          ...prev.filter(m => m.sender !== 'system' || !m.text.includes('API key')), 
          { 
            id: Date.now(), 
            text: 'Warning: OpenAI API key is not configured. Please check the backend configuration.', 
            sender: 'system' 
          }
        ]);
      }
    } catch (error) {
      debug('Backend health check failed', error);
      setBackendStatus('disconnected');
      
      let errorMessage = 'Warning: Cannot connect to the backend server. Please ensure it\'s running.';
      
      // Add more detailed error information
      if (error.code === 'ECONNREFUSED') {
        errorMessage = 'Warning: Connection refused. Make sure the backend server is running on port 8000.';
      } else if (error.code === 'ETIMEDOUT') {
        errorMessage = 'Warning: Connection timed out. The backend server might be overloaded.';
      } else if (error.response) {
        errorMessage = `Warning: Backend server error (${error.response.status}). Check the backend logs.`;
      }
      
      setMessages(prev => [
        ...prev.filter(m => m.sender !== 'system' || !m.text.includes('backend server')), 
        { 
          id: Date.now(), 
          text: errorMessage, 
          sender: 'system' 
        }
      ]);
    }
  };

  const testOpenAIAPI = async () => {
    if (apiTestLoading) return;
    
    setApiTestLoading(true);
    debug('Testing OpenAI API connection');
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/test-openai`, { timeout: 10000 });
      debug('OpenAI API test response', response.data);
      
      // Add a system message with the test result
      setMessages(prev => [
        ...prev.filter(m => m.sender === 'system' && !m.text.includes('OpenAI API Test')), 
        { 
          id: Date.now(), 
          text: `OpenAI API Test: ${response.data.status === 'success' ? 
            '✅ Connection successful' : 
            '❌ Connection failed'} - ${response.data.message}`, 
          sender: 'system' 
        }
      ]);
    } catch (error) {
      debug('OpenAI API test failed', error);
      
      // Add error message
      let errorMessage = `OpenAI API Test: ❌ Connection failed - ${error.response?.data?.message || error.message || 'Unknown error'}`;
      
      // Check for quota errors
      if (error.response?.data?.message?.includes('insufficient_quota') || 
          error.response?.data?.message?.includes('exceeded your current quota')) {
        errorMessage = 'OpenAI API Test: ❌ Connection failed - You exceeded your OpenAI API quota. Please check your billing details.';
      }
      // Add more detailed error information
      else if (error.code === 'ECONNREFUSED') {
        errorMessage = 'OpenAI API Test: ❌ Connection failed - Backend server not running';
      } else if (error.code === 'ETIMEDOUT') {
        errorMessage = 'OpenAI API Test: ❌ Connection failed - Request timed out';
      }
      
      setMessages(prev => [
        ...prev.filter(m => m.sender === 'system' && !m.text.includes('OpenAI API Test')), 
        { 
          id: Date.now(), 
          text: errorMessage, 
          sender: 'system' 
        }
      ]);
    } finally {
      setApiTestLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!input.trim()) return;
    
    // Add user message to chat
    const userMessage = { 
      id: messages.length + 1, 
      text: input, 
      sender: 'user' 
    };
    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);
    
    // Scroll to bottom after adding a message
    setTimeout(() => {
      const chatContainer = document.querySelector('.chat-messages');
      if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }
    }, 100);
    
    debug('Sending message to backend', input);
    
    try {
      // Send user message to backend with timeout
      const response = await axios.post(`${API_BASE_URL}/api/chat`, 
        { message: input }, 
        { timeout: 10000 }
      );
      debug('Received response from backend', response.data);
      
      // Add bot response to chat
      const botMessage = { 
        id: messages.length + 2, 
        text: response.data.message, 
        sender: 'bot' 
      };
      setMessages(prev => [...prev, botMessage]);
      
      // If an event was created, notify the parent component
      if (response.data.event) {
        debug('Event operation:', response.data.event);
        
        // Pass both the event and action to the parent
        onEventAdded({
          event: response.data.event,
          action: response.data.action || 'create',
          message: response.data.message
        });
      } else {
        debug('No event created from this message');
      }
    } catch (error) {
      debug('Error sending message', error);
      console.error('Error details:', error.response || error);
      
      // Add error message with more details
      let errorMessage = 'Sorry, there was an error processing your request.';
      
      if (error.response) {
        // The server responded with an error status
        debug('Server responded with error', error.response);
        if (error.response.data && error.response.data.message) {
          errorMessage = error.response.data.message;
        } else {
          errorMessage = `Error ${error.response.status}: ${error.response.statusText}`;
        }
      } else if (error.request) {
        // The request was made but no response was received
        debug('No response received from server', error.request);
        errorMessage = 'No response from server. Please check if the backend is running.';
      }
      
      const errorMsg = { 
        id: messages.length + 2, 
        text: errorMessage, 
        sender: 'bot' 
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  // Ensure scroll to bottom when messages change
  useEffect(() => {
    const chatContainer = document.querySelector('.chat-messages');
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="chatbot">
      <h3 className="mb-3">✨ Calendar Assistant</h3>
      {backendStatus !== 'connected' && (
        <div className="alert alert-warning mb-3">
          Backend status: {backendStatus} 
          <button 
            className="btn btn-sm btn-outline-dark ms-2" 
            onClick={checkBackendHealth}
          >
            Retry 🔄
          </button>
          <button 
            className="btn btn-sm btn-outline-dark ms-2" 
            onClick={testOpenAIAPI}
            disabled={apiTestLoading}
          >
            {apiTestLoading ? 'Testing...' : 'Test API'}
          </button>
        </div>
      )}
      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((message) => (
            <div 
              key={message.id} 
              className={`message ${message.sender === 'user' ? 'user-message' : 
                message.sender === 'system' ? 'system-message' : 'bot-message'}`}
            >
              {message.sender === 'user' && <span className="message-prefix">👤 </span>}
              {message.sender === 'bot' && <span className="message-prefix">💬 </span>}
              {message.text}
            </div>
          ))}
          {isLoading && (
            <div className="message bot-message">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
        </div>
        <form onSubmit={handleSubmit} className="chat-input-container">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            placeholder="Tell me about an event to add..."
            className="chat-input"
            disabled={isLoading || backendStatus === 'disconnected'}
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={isLoading || !input.trim() || backendStatus === 'disconnected'}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}; 