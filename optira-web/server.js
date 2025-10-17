const express = require('express');
const cors = require('cors');
const axios = require('axios');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.SERVER_PORT || 3001; // Use 3001 for proxy server

// Optira API Configuration
const OPTIRA_API_ENDPOINT = process.env.OPTIRA_API_ENDPOINT;
const OPTIRA_API_KEY = process.env.OPTIRA_API_KEY;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'build')));

// Logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    apiEndpoint: OPTIRA_API_ENDPOINT,
    port: PORT
  });
});

// Proxy endpoint for Optira API - ALL queries use direct Lambda invocation
app.post('/api/chat', async (req, res) => {
  try {
    const { query } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }

    console.log('Proxying request to Optira API:', query);
    console.log('Using direct Lambda invocation for ALL queries...');
    
    const AWS = require('aws-sdk');
    
    // Configure AWS SDK to use region from environment variable
    AWS.config.update({
      region: process.env.REACT_APP_AWS_REGION || 'us-west-2',
    });
    
    const lambda = new AWS.Lambda();
    
    const params = {
      FunctionName: 'OptiraAgentFunction',
      InvocationType: 'RequestResponse', // Synchronous
      Payload: JSON.stringify({
        body: JSON.stringify({ 
          query: query,
          session_id: `user-${req.headers['user-id'] || 'anonymous'}`
        })
      })
    };
    
    try {
      console.log('Invoking Lambda function directly...');
      const lambdaResponse = await lambda.invoke(params).promise();
      console.log('Lambda response received, status:', lambdaResponse.StatusCode);
      
      const result = JSON.parse(lambdaResponse.Payload);
      console.log('Lambda result parsed successfully');
      
      if (result.statusCode === 200) {
        // Parse the body if it's a string
        let responseBody = result.body;
        if (typeof responseBody === 'string') {
          try {
            responseBody = JSON.parse(responseBody);
          } catch (e) {
            // If it's not JSON, keep as string
          }
        }
        res.json(responseBody);
      } else {
        console.error('Lambda returned error status:', result.statusCode);
        res.status(result.statusCode || 500).json({ error: result.body || 'Lambda error' });
      }
    } catch (lambdaError) {
      console.error('Lambda invocation error:', lambdaError.message);
      console.error('Full error:', lambdaError);
      
      res.status(500).json({ 
        error: 'Lambda invocation failed', 
        details: lambdaError.message
      });
    }

  } catch (error) {
    console.error('Error in chat endpoint:', error.message);
    res.status(500).json({
      error: 'Internal server error',
      details: error.message
    });
  }
});

// Test endpoint to verify API connectivity
app.get('/api/test', async (req, res) => {
  try {
    console.log('Testing Optira API connection...');
    
    const response = await axios.post(OPTIRA_API_ENDPOINT, 
      { query: "How many support cases do we have in total?" },
      {
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': OPTIRA_API_KEY
        },
        timeout: 600000  // 10 minutes
      }
    );

    res.json({
      status: 'success',
      message: 'API connection successful',
      response: response.data
    });

  } catch (error) {
    console.error('API test failed:', error.message);
    res.status(500).json({
      status: 'error',
      message: 'API connection failed',
      error: error.message,
      details: error.response?.data
    });
  }
});

// Serve React app for all other routes (only in production)
if (process.env.NODE_ENV === 'production') {
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'build', 'index.html'));
  });
}

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Server error:', error);
  res.status(500).json({ error: 'Internal server error' });
});

const server = app.listen(PORT, () => {
  console.log(`🚀 Optira Proxy Server running on port ${PORT}`);
  console.log(`📡 Proxying to: ${OPTIRA_API_ENDPOINT}`);
  console.log(`🔗 API endpoints:`);
  console.log(`   Health: http://localhost:${PORT}/api/health`);
  console.log(`   Chat: http://localhost:${PORT}/api/chat`);
  console.log(`   Test: http://localhost:${PORT}/api/test`);
});

// Set server timeout to 10 minutes
server.timeout = 600000; // 10 minutes
server.keepAliveTimeout = 600000; // 10 minutes
server.headersTimeout = 610000; // Slightly higher than keepAliveTimeout

module.exports = app;
