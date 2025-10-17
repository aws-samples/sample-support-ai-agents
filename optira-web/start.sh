#!/bin/bash

echo "🚀 Starting Optira Web Chatbot Interface"
echo "========================================"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🔧 Starting proxy server and React app..."
echo ""
echo "The application will be available at:"
echo "  🌐 React App: http://localhost:3000"
echo "  🔗 Proxy API: http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start both the proxy server and React app
npm run dev
