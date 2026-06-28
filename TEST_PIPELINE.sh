#!/bin/bash

# Quick test to see pipeline logging in real-time

echo "========================================"
echo "🚀 BUTTERFLY-EFFECT LOGGING TEST"
echo "========================================"
echo ""

echo "Starting server in background..."
cd backend
python -m uvicorn butterfly.main:app --reload --host 127.0.0.1 --port 8000 > /tmp/butterfly_server.log 2>&1 &
SERVER_PID=$!

echo "Server PID: $SERVER_PID"
sleep 3

echo ""
echo "Making analysis request..."
echo "Query: 'How do interest rate changes affect mortgage markets?'"
echo ""
echo "Watch the terminal for real-time logs showing:"
echo "  ✅ PARSE stage (LLM event parsing)"
echo "  ✅ FETCH stage (evidence from 3 sources)"
echo "  ✅ GRAPH stage (causal graph building)"
echo "  ✅ SIMULATE stage (agent swarm simulation)"
echo "  ✅ INSIGHTS stage (LLM insights + SNN verification)"
echo ""

# Stream response while tailing logs
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do interest rate changes affect mortgage markets?"
  }' \
  --no-buffer 2>/dev/null | head -c 500

echo ""
echo ""
echo "========================================"
echo "📋 Server Log (last 50 lines):"
echo "========================================"
tail -50 /tmp/butterfly_server.log

echo ""
echo "Cleaning up..."
kill $SERVER_PID 2>/dev/null || true

echo "Done! Full log available at: /tmp/butterfly_server.log"
