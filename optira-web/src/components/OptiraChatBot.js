import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '../chatbot.css';

const OptiraChatBot = ({ currentAgent = 'orchestrator', user }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connected');
  const messagesEndRef = useRef(null);

  // Use proxy server to avoid CORS issues
  const API_ENDPOINT = process.env.NODE_ENV === 'production' 
    ? '/api/chat' 
    : 'http://localhost:3001/api/chat';

  // Agent names mapping
  const agentNames = {
    'orchestrator': 'Orchestrator',
    'rag-agent': 'Support Case Knowledge-base (RAG) Agent',
    'aggregator-agent': 'Support Case Query Aggregator Agent'
  };

  // Exact queries provided by the user (removed the 3 specified queries)
  const basicQueries = [
    "Total count of support cases in jan 2025",
    "Give me OpenSearch Support cases in Jan 2025",
    "Can you provide OpenSearch case distribution based on severity?"
  ];

  const advancedQueries = [
    "Find accounts with frequent high-priority support cases since January 2024, excluding limit increase requests. For each account and AWS service combination, show the total number of cases and how many different days had issues. Only include results where there were more than 3 cases, and sort results by the highest number of cases first.",
    
    "Find accounts that experienced high-severity issues across multiple AWS services since January 2024, excluding limit increase requests. Show how many different services were involved, total number of cases, and the number of unique days with issues. Only include accounts that had problems with more than 2 different services, and sort results by the number of services involved (highest first), then by total cases.",
    
    "For high-severity support cases since January 1, 2024, show the number of total cases and after-hours cases for each account and service combination. Define after-hours as before 1 PM UTC, after 1 AM UTC, or any time on weekends. Only include results with more than 3 after-hours cases. Sort by the highest number of after-hours cases. Exclude limit increase requests."
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Add welcome message when agent changes
    const agentName = agentNames[currentAgent] || 'ES OPTIRA Agent';
    setMessages([
      {
        id: Date.now(),
        type: 'assistant',
        content: `Hello! I'm the **${agentName}** from ES OPTIRA. I'm part of the Agentic AI system for support. I can help you analyze AWS support cases, identify. Ask me to analyze patterns, identify problems, and help plan fixes!`,
        timestamp: new Date()
      }
    ]);

    // Test API connection on load
    testConnection();
  }, [currentAgent]);

  const testConnection = async () => {
    try {
      console.log('Testing API connection...');
      console.log('API Endpoint:', API_ENDPOINT);
      
      // Test health endpoint first
      const healthEndpoint = API_ENDPOINT.replace('/chat', '/health');
      const healthResponse = await axios.get(healthEndpoint, { timeout: 5000 });
      
      console.log('Health check successful:', healthResponse.data);
      setConnectionStatus('connected');
      
    } catch (error) {
      console.error('Connection test failed:', error);
      setConnectionStatus('error');
      
      // Add a system message about connection issues
      const systemMessage = {
        id: Date.now(),
        type: 'error',
        content: 'Warning: Unable to connect to the ES OPTIRA system. Make sure the proxy server is running on port 3001.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, systemMessage]);
    }
  };

  const sendMessage = async (query) => {
    if (!query.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: query,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      console.log('Sending request to proxy server:', API_ENDPOINT);
      console.log('Query:', query);
      console.log('Current Agent:', agentNames[currentAgent]);
      
      const response = await axios.post(API_ENDPOINT, 
        { 
          query: query,
          agent: currentAgent // Include current agent context
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'user-id': user?.username || 'anonymous'
          },
          timeout: 600000 // 10 minutes timeout
        }
      );

      console.log('Response received:', response);

      let responseContent = '';
      if (response.data) {
        // Handle different response formats
        if (typeof response.data === 'string') {
          responseContent = response.data;
        } else if (response.data.response) {
          responseContent = response.data.response;
        } else if (response.data.message) {
          responseContent = response.data.message;
        } else if (response.data.body) {
          responseContent = response.data.body;
        } else if (response.data.result) {
          responseContent = response.data.result;
        } else {
          responseContent = JSON.stringify(response.data, null, 2);
        }
      } else {
        responseContent = 'I received your query but got an unexpected response format.';
      }

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: responseContent,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
      setConnectionStatus('connected');
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      let errorMessage = 'Sorry, I encountered an error while processing your request.';
      
      if (error.response) {
        // Server responded with error status
        console.log('Error response:', error.response);
        const errorData = error.response.data;
        
        if (errorData && errorData.error) {
          errorMessage = `Error: ${errorData.error}`;
          if (errorData.details) {
            errorMessage += ` (${errorData.details})`;
          }
        } else {
          errorMessage = `Error ${error.response.status}: ${error.response.statusText}`;
        }
        
        setConnectionStatus('error');
      } else if (error.request) {
        // Request was made but no response received
        console.log('No response received:', error.request);
        errorMessage = 'Unable to connect to the proxy server. Make sure it\'s running on port 3001.';
        setConnectionStatus('error');
      } else {
        // Something else happened
        console.log('Request setup error:', error.message);
        errorMessage = `Request failed: ${error.message}`;
      }

      const errorMessageObj = {
        id: Date.now() + 1,
        type: 'error',
        content: errorMessage,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessageObj]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  const handleExampleClick = (example) => {
    setInputValue(example);
  };

  const formatTimestamp = (timestamp) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Clean and normalize markdown content
  const cleanMarkdownContent = (content) => {
    if (!content) return '';
    
    // Remove "result: " prefix if it exists
    let cleaned = content.replace(/^result:\s*/i, '');
    
    // Normalize line endings
    cleaned = cleaned.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // Fix bullet points - ensure they have proper spacing
    cleaned = cleaned.replace(/^(\s*)([•·-])\s*/gm, '$1- ');
    
    // Fix numbered lists
    cleaned = cleaned.replace(/^(\s*)(\d+\.)\s*/gm, '$1$2 ');
    
    // Ensure proper spacing around headers
    cleaned = cleaned.replace(/^(#{1,6})\s*(.+)$/gm, '\n$1 $2\n');
    
    // Fix multiple consecutive newlines
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
    
    // Ensure lists have proper spacing
    cleaned = cleaned.replace(/^(\s*[-*+]|\s*\d+\.)\s*(.+)$/gm, (match, bullet, text) => {
      return `${bullet} ${text}`;
    });
    
    return cleaned.trim();
  };

  const renderMessageContent = (message) => {
    if (message.type === 'assistant') {
      const cleanedContent = cleanMarkdownContent(message.content);
      
      return (
        <div className="markdown-content">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              // Custom styling for different markdown elements
              table: ({node, ...props}) => (
                <table className="markdown-table" {...props} />
              ),
              th: ({node, ...props}) => (
                <th className="markdown-th" {...props} />
              ),
              td: ({node, ...props}) => (
                <td className="markdown-td" {...props} />
              ),
              h1: ({node, ...props}) => (
                <h1 className="markdown-h1" {...props} />
              ),
              h2: ({node, ...props}) => (
                <h2 className="markdown-h2" {...props} />
              ),
              h3: ({node, ...props}) => (
                <h3 className="markdown-h3" {...props} />
              ),
              h4: ({node, ...props}) => (
                <h4 className="markdown-h4" {...props} />
              ),
              ul: ({node, ...props}) => (
                <ul className="markdown-ul" {...props} />
              ),
              ol: ({node, ...props}) => (
                <ol className="markdown-ol" {...props} />
              ),
              li: ({node, ...props}) => (
                <li className="markdown-li" {...props} />
              ),
              p: ({node, ...props}) => (
                <p className="markdown-p" {...props} />
              ),
              strong: ({node, ...props}) => (
                <strong className="markdown-strong" {...props} />
              ),
              em: ({node, ...props}) => (
                <em className="markdown-em" {...props} />
              ),
              code: ({node, inline, ...props}) => (
                inline ? (
                  <code className="markdown-code-inline" {...props} />
                ) : (
                  <pre className="markdown-pre">
                    <code className="markdown-code-block" {...props} />
                  </pre>
                )
              ),
              blockquote: ({node, ...props}) => (
                <blockquote className="markdown-blockquote" {...props} />
              ),
              hr: ({node, ...props}) => (
                <hr className="markdown-hr" {...props} />
              )
            }}
          >
            {cleanedContent}
          </ReactMarkdown>
        </div>
      );
    } else {
      return <div className="content">{message.content}</div>;
    }
  };

  const currentAgentName = agentNames[currentAgent] || 'ES OPTIRA Agent';

  return (
    <div className="optira-chatbot">
      <div className="chatarea">
        <div className="messages">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              {renderMessageContent(message)}
              <div className="timestamp" style={{ fontSize: '11px', opacity: 0.7, marginTop: '4px' }}>
                {formatTimestamp(message.timestamp)}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message loading">
              <div className="content">🤖 {currentAgentName} is analyzing and processing your request...</div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="input-area">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={`Ask the ${currentAgentName} to analyze optimize your AWS infrastructure...`}
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !inputValue.trim()}>
            {isLoading ? 'Processing...' : 'Send'}
          </button>
        </form>

        {messages.length <= 2 && (
          <div className="examples">
            <div className="title">💡 Try these queries with the {currentAgentName}</div>
            
            <div style={{ marginBottom: '16px' }}>
              <div className="category-title">📊 Basic Analytics</div>
              <div>
                {basicQueries.map((example, index) => (
                  <span
                    key={`basic-${index}`}
                    className="example"
                    onClick={() => handleExampleClick(example)}
                  >
                    {example}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div className="category-title">🚀 Advanced Remediation Analysis</div>
              <div>
                {advancedQueries.map((example, index) => (
                  <div
                    key={`advanced-${index}`}
                    className="advanced-example"
                    onClick={() => handleExampleClick(example)}
                  >
                    <strong>Query {index + 1}:</strong> {example}
                    <div className="query-preview">Click to use this advanced remediation analysis query</div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="pro-tip">
              💡 <strong>{currentAgentName}:</strong> I'm part of the ES OPTIRA Agentic AI system. I can analyze support case patterns, 
              identify issues.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OptiraChatBot;
