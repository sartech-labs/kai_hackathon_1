# 🚀 LangGraph Setup & Quickstart

## ⚡ 5-Minute Setup

### Step 1: Install Dependencies

```bash
cd c:\Sree\Work\KSUM\kai_hackathon_1
pip install -r requirements.txt
```

**What gets installed:**
- ✅ Flask (REST API)
- ✅ LangGraph (Multi-agent workflow)
- ✅ LangChain (LLM orchestration)
- ✅ OpenAI (LLM access)
- ✅ python-dotenv (Environment config)

### Step 2: Verify .env File

Check that `.env` file exists with OpenAI API key:

```bash
cat .env
```

Should show:
```
OPEN_AI_API_KEY = "sk-proj-xxxxx..."
```

✅ If yes: Continue to Step 3
❌ If no: Contact admin for API key, then create/update `.env`

### Step 3: Run the System

**Option A: Test Mode (Recommended)**
```bash
python langgraph_agents.py
```

This runs 2 test cases showing:
- 📊 Agent analysis in real-time
- 💭 LLM reasoning process
- ✅ Success/failure decisions
- 💰 Pricing calculations

**Option B: API Server Mode**
```bash
python api_langgraph.py
```

Server available at: `http://localhost:5000`

Use Postman or curl to send orders.

---

## 📊 Expected Output

When you run `python langgraph_agents.py`, you'll see:

```
[Manager Agent] Processing Order: ORD-001
[Manager Agent] Request: PMP-STD-100 x15 to local city

[STEP 1] Procurement Agent Evaluation
[Procurement Agent] Analysis: Based on inventory...
  Result: Materials appear to be in stock
  Confidence: 95%

[STEP 2] Logistics Agent Evaluation
[Logistics Agent] Analysis: Local delivery is...
  Result: Shipping cost calculated at $40
  Delivery Date: 2026-03-01
  Confidence: 90%

[STEP 3] Consolidation Agent Evaluation
[Consolidation Agent] Analysis: Reviewing both agents...
  Result: Deal consolidation with favorable terms
  Confidence: 95%

[STEP 4] Consensus Check
  All Agents Can Proceed: True
  Average Confidence: 93%
  Consensus Reached: True

FINAL RESPONSE:
{
  "status": "SUCCESS",
  "order_id": "ORD-001",
  "final_price": 160360.0,
  "total_deal_value": 160360.0,
  "delivery_date": "2026-03-01",
  "agent_responses": {
    ...detailed analysis from each agent...
  }
}
```

---

## 🌐 API Testing

### Start API Server
```bash
python api_langgraph.py
```

Output:
```
🚀 Starting LangGraph-based Multi-Agent Order Processing System
📡 Endpoints available at http://localhost:5000
```

### Test Health Check

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Multi-Agent Order Processing System (LangGraph)",
  "llm_available": true
}
```

### Test Agent Info

```bash
curl http://localhost:5000/agent-info
```

Shows info about LLM agents and their capabilities.

### Process an Order

```bash
curl -X POST http://localhost:5000/process_order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-TEST-001",
    "product_sku": "PMP-STD-100",
    "quantity": 15,
    "customer_location": "local city",
    "priority": "normal"
  }'
```

---

## 📁 What Was Added

### New Files:
- `langgraph_agents.py` - LLM-powered agents + LangGraph orchestration
- `api_langgraph.py` - Flask API with LangGraph
- `LANGGRAPH_GUIDE.md` - Detailed documentation

### Updated Files:
- `requirements.txt` - Added new dependencies

### Unchanged:
- Original system still works: `python main.py`
- Original API still works: `python api.py`
- All documentation remains valid

---

## 🎯 Key Changes from Original

| Feature | Original | LangGraph |
|---------|----------|-----------|
| Agent Logic | Hardcoded rules | LLM reasoning |
| Speed | <500ms | 3-5 seconds |
| Cost | Free | ~$0.0005 per order |
| Explanation | Predefined | LLM generated |
| Customization | Code changes | Prompt changes |

---

## ⚙️ Configuration

### Model Selection

Default: `gpt-3.5-turbo` (fast & cheap)

To use GPT-4 (smarter but slower):

Edit `langgraph_agents.py`:
```python
self.llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-4",  # Change from gpt-3.5-turbo
    temperature=0.3
)
```

### Adjust Prompts

Customize agent behavior by editing prompts in agent classes:

```python
class LLMProcurementAgent:
    def __init__(self, llm):
        self.prompt = ChatPromptTemplate.from_template("""
        Your custom prompt here...
        """)
```

---

## 🧪 Test Cases Included

### Test 1: Standard Order
```
Product: PMP-STD-100
Quantity: 15
Location: Local city
Expected: ✅ SUCCESS
```

### Test 2: Large Order with Expedited Shipping
```
Product: PMP-HEAVY-200
Quantity: 50
Location: National
Priority: Expedited
Expected: ✅ SUCCESS
```

Both tests run automatically with `python langgraph_agents.py`

---

## 🚨 Troubleshooting

### Problem: "API key not found"
```
Error: OPEN_AI_API_KEY not found in .env file
```

**Solution:**
1. Verify `.env` file exists in project root
2. Check it has the line: `OPEN_AI_API_KEY = "sk-proj-..."`
3. No quotes around the value needed

### Problem: "Module not found: langgraph"
```
ModuleNotFoundError: No module named 'langgraph'
```

**Solution:**
```bash
pip install --upgrade langgraph langchain langchain-openai
```

### Problem: "API returns 401 Unauthorized"
```json
{"error": {"message": "Incorrect API key provided", "type": "invalid_request_error"}}
```

**Solution:**
1. Check API key in .env is correct
2. Verify it starts with `sk-proj-`
3. Regenerate key if needed

### Problem: "Response is slow (5+ seconds)"
**Reason:** Normal for LLM API calls

**Solutions:**
- Use gpt-3.5-turbo (faster than gpt-4)
- Implement response caching
- Batch process multiple orders

### Problem: "Rate limit exceeded"
**Reason:** Too many API calls in short time

**Solution:**
- Wait a few seconds before retrying
- Implement exponential backoff
- Check OpenAI dashboard for limits

---

## 📊 Understanding the Response

### Success Response
```json
{
  "status": "SUCCESS",
  "order_id": "ORD-001",
  "product_sku": "PMP-STD-100",
  "quantity": 15,
  "customer_location": "local city",
  "final_price": 160360.0,
  "total_deal_value": 160360.0,
  "delivery_date": "2026-03-01",
  "consensus_reached": true,
  "agent_responses": {
    "procurement": {
      "can_proceed": true,
      "reasoning": "All materials in stock...",
      "confidence": 0.95,
      "analysis": "Detailed LLM reasoning..."
    },
    "logistics": {
      "can_proceed": true,
      "reasoning": "Local delivery...",
      "confidence": 0.90,
      "analysis": "Detailed LLM reasoning..."
    },
    "consolidation": {
      "can_proceed": true,
      "reasoning": "Deal approved with discount...",
      "confidence": 0.95,
      "analysis": "Detailed LLM reasoning..."
    }
  },
  "timestamp": "2026-02-27T16:32:52"
}
```

### Failure Response
```json
{
  "status": "FAILURE",
  "order_id": "ORD-002",
  "message": "Order cannot be processed. Consensus not reached.",
  "timestamp": "2026-02-27T16:35:00"
}
```

---

## 💡 Next Steps

1. **Understand the Flow**
   - Run: `python langgraph_agents.py`
   - Watch the agent analysis in real-time

2. **Test the API**
   - Run: `python api_langgraph.py`
   - Use curl or Postman to send orders

3. **Explore Agent Prompts**
   - Edit prompts in `langgraph_agents.py`
   - Test how LLM responds to different wordings

4. **Customize Business Rules**
   - Modify discount tiers in prompts
   - Change pricing formulas
   - Add new validation rules

5. **Deploy**
   - Set up in production environment
   - Configure environment variables
   - Monitor API usage and costs

---

## 📚 Documentation

- **LANGGRAPH_GUIDE.md** - Complete LangGraph documentation
- **README.md** - Project overview
- **ARCHITECTURE.md** - System architecture details
- **QUICKSTART.md** - Original system quickstart
- **DOCUMENTATION.md** - Original system documentation

---

## ✅ Verification Checklist

- [ ] .env file created with OPEN_AI_API_KEY
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Can import langgraph: `python -c "import langgraph; print('OK')"`
- [ ] Test mode runs: `python langgraph_agents.py`
- [ ] API server starts: `python api_langgraph.py`
- [ ] Health check passes: `curl http://localhost:5000/health`

---

## 🎉 You're All Set!

Your multi-agent system is now powered by LangGraph and OpenAI!

**To get started:**
```bash
python langgraph_agents.py
```

**Questions?** Check LANGGRAPH_GUIDE.md for detailed documentation.
