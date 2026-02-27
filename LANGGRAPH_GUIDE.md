# 🤖 LangGraph Integration Guide

## Overview

Your multi-agent order processing system has been enhanced with **LangGraph** and **OpenAI API** integration. This enables LLM-powered intelligent agents that use natural language reasoning instead of hardcoded logic.

---

## 📦 What's New

### Original System vs LangGraph-Enhanced System

| Aspect | Original | LangGraph-Enhanced |
|--------|----------|-------------------|
| Agent Logic | Hardcoded Python | LLM-powered (GPT-3.5) |
| Reasoning | Fixed algorithms | Natural language reasoning |
| Configuration | config.py only | LLM + config.py |
| Extensibility | Manual coding | Prompt-based customization |
| Transparency | Clear rules | Agent explanations |
| Flexibility | Limited | High - LLM adapts |

### Key Improvements

✨ **Intelligent Agents**
- Agents use OpenAI's GPT-3.5-Turbo for reasoning
- Natural language decision-making
- Contextual analysis of orders

✨ **LangGraph Orchestration**
- State machine workflow using LangGraph
- Guaranteed agent execution order
- Consensus mechanism built-in

✨ **Better Transparency**
- Agents explain their reasoning in natural language
- Each agent provides detailed analysis
- Full decision audit trail

✨ **Flexible Configuration**
- Customize agent behavior via prompts
- No code changes needed
- Easy A/B testing

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `langgraph` - Multi-agent workflow framework
- `langchain` - LLM orchestration
- `langchain-openai` - OpenAI integration
- `openai` - OpenAI API client
- `python-dotenv` - Environment variable management

### 2. Set Up OpenAI API Key

**Option A: Using .env file (Recommended)**
```
# .env file
OPEN_AI_API_KEY = "sk-proj-xxxxx..."
```

**Option B: Using environment variable**
```bash
export OPENAI_API_KEY="sk-proj-xxxxx..."
```

### 3. Run the System

**Test Mode (with detailed logging):**
```bash
python langgraph_agents.py
```

**API Server Mode:**
```bash
python api_langgraph.py
```

Server runs on: http://localhost:5000

---

## 📁 New Files

```
c:\Sree\Work\KSUM\kai_hackathon_1\
├── langgraph_agents.py       # LLM-powered agents + LangGraph
├── api_langgraph.py          # Flask API with LangGraph
├── LANGGRAPH_GUIDE.md        # This file
└── .env                       # OpenAI API key (create if not exist)
```

---

## 🔄 System Architecture

### Data Flow

```
HTTP Request
     │
     ▼
api_langgraph.py (Flask)
     │
     ▼
OrderRequest
     │
     ▼
LLMManagerAgent.process_order()
     │
     ▼
LangGraph Workflow
     ├─→ LLMProcurementAgent (Node 1)
     │   └─→ OpenAI API call
     │       └─→ Analyze inventory
     │
     ├─→ LLMLogisticsAgent (Node 2)
     │   └─→ OpenAI API call
     │       └─→ Calculate shipping
     │
     ├─→ LLMConsolidationAgent (Node 3)
     │   └─→ OpenAI API call
     │       └─→ Finalize pricing
     │
     └─→ Consensus Node
         └─→ Check agreement
     │
     ▼
Final Response (JSON)
```

### Agent Prompts

Each agent uses a specialized prompt to guide the LLM:

**Procurement Agent Prompt:**
```
You are a Procurement Agent...
Check inventory and calculate costs for the order.
Return: can_proceed, material_availability, total_cost, confidence
```

**Logistics Agent Prompt:**
```
You are a Logistics Agent...
Classify location, calculate shipping, estimate delivery.
Return: location_type, shipping_cost, delivery_date, confidence
```

**Consolidation Agent Prompt:**
```
You are a Consolidation Agent...
Review other agents' work, apply discounts, calculate final price.
Return: discount_rate, final_price, total_deal_value, confidence
```

---

## 🔧 Configuration

### Environment Variables

**`.env` file:**
```bash
# Required
OPEN_AI_API_KEY = "sk-proj-xxxxx..."

# Optional
OPENAI_MODEL = "gpt-3.5-turbo"  # Default model
OPENAI_TEMP = 0.3              # Temperature (0-1)
```

### Model Selection

To use different OpenAI models, modify `langgraph_agents.py`:

```python
# Line ~200
self.llm = ChatOpenAI(
    api_key=api_key, 
    model="gpt-4",  # Change to gpt-4 or other models
    temperature=0.3
)
```

### Customizing Agent Behavior

Edit the prompts in each agent class to customize behavior:

```python
# Example: Modify Procurement Agent prompt
class LLMProcurementAgent:
    def __init__(self, llm: ChatOpenAI, inventory_manager: InventoryManager):
        self.prompt = ChatPromptTemplate.from_template("""
        Your custom prompt here...
        """)
```

---

## 📊 API Endpoints

### Same as Original API Plus New Endpoint

```bash
# Process Order (Enhanced with LLM)
POST /process_order
{
  "order_id": "ORD-001",
  "product_sku": "PMP-STD-100",
  "quantity": 15,
  "customer_location": "local city",
  "priority": "normal"
}

# Get Products
GET /products

# Get Inventory
GET /inventory

# Get Product Details
GET /product/<SKU>

# Health Check
GET /health

# NEW: Get Agent Information
GET /agent-info
```

### Response Format

The response includes agent-by-agent analysis:

```json
{
  "status": "SUCCESS",
  "order_id": "ORD-001",
  "final_price": 160360.0,
  "total_deal_value": 160360.0,
  "delivery_date": "2026-03-01",
  "consensus_reached": true,
  "agent_responses": {
    "procurement": {
      "can_proceed": true,
      "reasoning": "All materials in stock...",
      "confidence": 0.95,
      "analysis": "Detailed LLM analysis..."
    },
    "logistics": {
      "can_proceed": true,
      "reasoning": "Regional delivery...",
      "confidence": 0.90,
      "analysis": "Detailed LLM analysis..."
    },
    "consolidation": {
      "can_proceed": true,
      "reasoning": "Deal approved with 5% discount...",
      "confidence": 0.95,
      "analysis": "Detailed LLM analysis..."
    }
  },
  "timestamp": "2026-02-27T..."
}
```

---

## 🧪 Testing

### Run LangGraph Tests

```bash
python langgraph_agents.py
```

Output shows:
- Agent-by-agent analysis
- LLM reasoning process
- Consensus decisions
- Full response with prices

### Test via API

**Terminal 1 - Start server:**
```bash
python api_langgraph.py
```

**Terminal 2 - Send request:**
```bash
curl -X POST http://localhost:5000/process_order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-001",
    "product_sku": "PMP-STD-100",
    "quantity": 15,
    "customer_location": "local city"
  }'
```

### Check Agent Info

```bash
curl http://localhost:5000/agent-info
```

---

## 🔑 API Key Management

### ✅ Best Practices

1. **Never commit API keys to git**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment variables in production**
   ```python
   api_key = os.getenv('OPEN_AI_API_KEY')
   ```

3. **Rotate keys regularly**
   - Go to OpenAI dashboard
   - Regenerate API keys monthly

4. **Monitor usage**
   - Check OpenAI dashboard for usage
   - Set up billing alerts

### ⚠️ Troubleshooting API Key

**Error: "OPEN_AI_API_KEY not found"**
- Make sure .env file exists
- Load with `load_dotenv()` before using

**Error: "Invalid API key"**
- Check key in .env file
- Verify no extra spaces/quotes
- Key should start with "sk-proj-"

**Error: "Rate limit exceeded"**
- OpenAI API has rate limits
- Wait before retrying
- Consider upgrading plan

---

## 🎯 Consensus & Decision Making

### How LLM Agents Decide

1. **Agent Analysis Phase**
   - Each agent reads order details
   - Reviews relevant data (inventory, location, etc.)
   - Uses LLM to reason about the problem
   - Provides confidence score

2. **Consensus Phase**
   - Manager collects all agent responses
   - Checks if ALL agents approve
   - Verifies average confidence > 75%
   - Makes final decision

3. **Success Criteria**
   - Procurement: Materials available
   - Logistics: Valid location & delivery possible
   - Consolidation: Pricing acceptable
   - All: Average confidence > 0.75

### Example: Why an Order Might Fail

```
Request: PMP-CHEM-300, Qty: 500

Procurement Agent: ❌ 70% confidence
  "Seal material (SEAL-CHEM) only has 210 in stock,
   but need 2000 units. Cannot proceed."

Logistics Agent: ✅ 90% confidence
  "International shipping possible."

Consolidation Agent: ❌ 0% confidence
  "Cannot proceed due to procurement failure."

Consensus: ❌ FAILED
  Average Confidence: 53% (< 75% threshold)
  
Result: Order REJECTED ❌
```

---

## 📈 Performance Considerations

### API Costs

Each order processes uses OpenAI API:
- ~3 API calls (one per agent)
- ~500-1000 tokens per order
- ~$0.0005 per order at current rates

Monitor costs:
```bash
# Check OpenAI dashboard
# https://platform.openai.com/account/billing/usage
```

### Response Time

- Procurement Agent: 1-2 seconds (API call)
- Logistics Agent: 0.5-1 second
- Consolidation Agent: 1-2 seconds
- Total: ~3-5 seconds per order

### Optimization Tips

1. **Use cheaper models**
   - gpt-3.5-turbo (current, fast & cheap)
   - gpt-4 (slower but smarter)

2. **Cache responses**
   - Store previous analyses
   - Reuse for similar orders

3. **Batch processing**
   - Process multiple orders in parallel
   - Reduce per-order overhead

---

## 🔍 Debugging

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Agent Responses

Look for this in logs:
```
[Procurement Agent] Analysis: ...
[Logistics Agent] Analysis: ...
[Consolidation Agent] Analysis: ...
```

### Understand LLM Decisions

LLM explanations are in:
- `response['agent_responses'][agent_name]['analysis']`
- Full natural language reasoning
- Shows LLM's thought process

---

## 🚀 Advanced Usage

### Custom Agent Prompts

Modify prompts for specific business rules:

```python
self.prompt = ChatPromptTemplate.from_template("""
You are a Procurement Agent.
Consider these business rules:
- Minimum order quantity: {min_qty}
- Preferred suppliers: {suppliers}
- Lead time requirements: {lead_time}

Analyze the order and provide assessment.
""")
```

### Multi-Model Setup

Use different models for different agents:

```python
procurement_llm = ChatOpenAI(model="gpt-4")  # Smarter
logistics_llm = ChatOpenAI(model="gpt-3.5-turbo")  # Faster
```

### Custom Consensus Logic

Modify `_consensus_node()` to change approval criteria:

```python
# Require 2 out of 3 agents approve instead of all 3
consensus_reached = sum([
    procurement.can_proceed,
    logistics.can_proceed,
    consolidation.can_proceed
]) >= 2
```

---

## 📚 Additional Resources

### LangGraph Documentation
- https://langchain.com/langgraph
- GitHub: https://github.com/langchain-ai/langgraph

### OpenAI API Documentation
- https://platform.openai.com/docs
- Models: https://platform.openai.com/docs/models

### LangChain Documentation
- https://python.langchain.com

---

## ✅ Comparison: Original vs LangGraph

### Original System

```python
# Fixed logic
def evaluate(self, product_sku, quantity):
    bom = self.get_product_bom(product_sku)
    for material_id, qty in bom.items():
        if not self.has_stock(material_id, qty * quantity):
            return False  # Out of stock
    return True  # All in stock
```

**Pros:**
- Fast & reliable
- No API calls
- Completely deterministic

**Cons:**
- Cannot handle edge cases
- Fixed business logic
- No natural explanation

### LangGraph System

```python
# LLM-powered reasoning
def invoke(self, order, inventory, materials):
    prompt = f"Analyze this order: {order}..."
    response = self.llm.invoke(prompt)
    # LLM reads inventory
    # LLM understands context
    # LLM explains reasoning
    return {
        'can_proceed': analysis.get('can_proceed'),
        'reasoning': analysis.get('reasoning'),
        'analysis': response.content
    }
```

**Pros:**
- Intelligent analysis
- Contextual understanding
- Human-like reasoning
- Natural explanations

**Cons:**
- Requires API calls (3-5 second latency)
- Costs money per request
- Non-deterministic (LLM varies)

---

## 🎓 Learn More

### Understanding LangGraph

LangGraph creates a computational graph where:
- **Nodes** = Agent functions or decision points
- **Edges** = Data flow between nodes
- **State** = Shared data passed between agents
- **END** = Terminal node (workflow complete)

Our workflow:
```
START → Procurement → Logistics → Consolidation → Consensus → END
```

### Why LangGraph?

✓ Explicit control flow
✓ State management
✓ Easy to debug
✓ Perfect for multi-agent systems
✓ Human-readable workflow
✓ Deterministic order of execution

---

## 🆘 Common Issues & Solutions

### Issue: "No module named 'langgraph'"
**Solution:**
```bash
pip install langgraph langchain langchain-openai
```

### Issue: "OPEN_AI_API_KEY not found"
**Solution:**
- Create `.env` file in project root
- Add: `OPEN_AI_API_KEY = "sk-proj-xxxxx"`
- Run: `python -c "from dotenv import load_dotenv; load_dotenv()"`

### Issue: "API returns 503 Service Unavailable"
**Solution:**
- Check OpenAI API is up: https://status.openai.com
- Verify API key is valid
- Check rate limits not exceeded

### Issue: "Slow response (5+ seconds)"
**Solution:**
- Normal for LLM
- Use gpt-3.5-turbo (faster than gpt-4)
- Implement request caching

---

## 📞 Support

For issues with:
- **LangGraph**: Check langgraph GitHub
- **OpenAI API**: Check OpenAI docs
- **This system**: Review code comments in `langgraph_agents.py`

---

**You now have an intelligent, LLM-powered multi-agent system!** 🎉

Start with: `python langgraph_agents.py`
Or: `python api_langgraph.py`
