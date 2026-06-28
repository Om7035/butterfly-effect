#!/bin/bash

echo "🧪 Testing Backend/Frontend Integration"
echo "========================================"
echo ""

# Test 1: Health check
echo "1️⃣  Testing backend health..."
curl -s http://localhost:8000/health | python -m json.tool
echo ""

# Test 2: Economics domain
echo "2️⃣  Testing economics domain (Fed raises rates)..."
curl -s -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"Fed raises rates 100bps"}' \
  | head -n 20
echo ""
echo "..."
echo ""

# Test 3: Geopolitics domain
echo "3️⃣  Testing geopolitics domain (War escalates)..."
curl -s -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"War escalates in Middle East"}' \
  | head -n 20
echo ""
echo "..."
echo ""

# Test 4: Climate domain
echo "4️⃣  Testing climate domain (Hurricane)..."
curl -s -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"Category 5 hurricane hits Miami"}' \
  | head -n 20
echo ""
echo "..."
echo ""

# Test 5: Tech domain
echo "5️⃣  Testing tech domain (ChatGPT)..."
curl -s -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question":"ChatGPT launches to public"}' \
  | head -n 20
echo ""
echo "..."
echo ""

echo "✅ Backend tests complete!"
echo ""
echo "Next steps:"
echo "1. Start frontend: cd frontend && npm run dev"
echo "2. Open http://localhost:3000"
echo "3. Try the example queries"
echo "4. Check demo mode at http://localhost:3000/demo"
