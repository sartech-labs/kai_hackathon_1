# Quick Start Guide - Multi-Agent Order Processing System

## 🚀 Quick Setup (2 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run the System

#### Option A: Test Mode (View Agent Interactions)
```bash
python main.py
```
This runs 5 comprehensive test cases showing:
- ✅ Successful orders
- ❌ Failed orders due to stock limitations
- 📊 Agent reasoning and confidence scores
- 💬 Consensus decision making

#### Option B: API Server Mode
```bash
python api.py
```
- Server starts on: `http://localhost:5000`
- Press `Ctrl+C` to stop

---

## 📋 Understanding the Output

### When Running Tests (`python main.py`)

You'll see output like:

```
[Manager Agent] Processing Order: ORD-001
[Manager Agent] Request: PMP-STD-100 x15 to local city

[STEP 1] Procurement Agent Evaluation
  Result: All materials are in stock
  Confidence: 95%

[STEP 2] Logistics Agent Evaluation
  Result: Shipping to local location - 50km distance
  Delivery Date: 2026-03-01
  Confidence: 90%

[STEP 3] Consolidation Agent Evaluation
  Result: Deal consolidated with 5% volume discount
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
  ...
}
```

### Key Fields Explained:

| Field | Meaning |
|-------|---------|
| `status` | SUCCESS or FAILURE |
| `final_price` | Customer price (includes profit margin) |
| `total_deal_value` | Total revenue (same as final_price) |
| `delivery_date` | Expected delivery in YYYY-MM-DD format |
| `Confidence` | Agent's certainty (0.0 - 1.0) |
| `Consensus Reached` | All agents agreed? |

---

## 🌐 Using the API Server

### 1. Start the Server
```bash
python api.py
```

### 2. Send an Order Request

**Using cURL:**
```bash
curl -X POST http://localhost:5000/process_order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-100",
    "product_sku": "PMP-STD-100",
    "quantity": 25,
    "customer_location": "regional state",
    "priority": "normal"
  }'
```

**Using Python:**
```python
import requests

order = {
    "order_id": "ORD-100",
    "product_sku": "PMP-STD-100",
    "quantity": 25,
    "customer_location": "regional state",
    "priority": "normal"
}

response = requests.post(
    'http://localhost:5000/process_order',
    json=order
)

print(response.json())
```

**Using JavaScript/Node.js:**
```javascript
const order = {
  order_id: "ORD-100",
  product_sku: "PMP-STD-100",
  quantity: 25,
  customer_location: "regional state",
  priority: "normal"
};

fetch('http://localhost:5000/process_order', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(order)
})
.then(res => res.json())
.then(data => console.log(data));
```

### 3. Available Products

To see what products are available:
```bash
curl http://localhost:5000/products
```

Response:
```json
{
  "status": "SUCCESS",
  "products": [
    {
      "sku": "PMP-STD-100",
      "materials": {
        "MAT-STEEL-A": 50,
        "MAT-MOTOR-100": 1,
        "MAT-SEAL-A": 2
      }
    },
    ...
  ]
}
```

### 4. Check Inventory
```bash
curl http://localhost:5000/inventory
```

### 5. Get Product Details
```bash
curl http://localhost:5000/product/PMP-STD-100
```

---

## 🎯 Test Cases

The system includes 5 test cases demonstrating different scenarios:

| # | Test Case | Expected Result | Purpose |
|---|-----------|-----------------|---------|
| 1 | Standard order (15 units, local) | ✅ SUCCESS | Normal flow |
| 2 | Large order (50 units, expedited) | ✅ SUCCESS | Volume discount + speedier delivery |
| 3 | Bulk order (120 units, regional) | ❌ FAILURE | Out of stock (Seal material) |
| 4 | Huge order (500 units) | ❌ FAILURE | Extreme shortage |
| 5 | Invalid SKU | ❌ FAILURE | Product doesn't exist |

---

## 📊 Pricing Breakdown Example

For Order: PMP-STD-100, Qty: 15 units, Local delivery

```
Material Cost        = $135,000.00  (50 units steel × $70 + 1 motor × $4500 + 2 seals × $500)
Shipping Cost        = $40.00       (50km × $0.50 + weight factor)
─────────────────────────────────
Subtotal             = $135,040.00
Discount (5%)        = -$6,752.00   (Medium volume tier: 11-50 units)
─────────────────────────────────
Discounted Subtotal  = $128,288.00
Profit Margin (25%)  = +$32,072.00
─────────────────────────────────
Final Price          = $160,360.00
```

---

## 🔧 Customization

### Change Profit Margin
Edit `config.py`:
```python
CONSOLIDATION_AGENT = {
    'profit_margin': 0.30,  # Change from 0.25 to 0.30 (30%)
}
```

### Change Shipping Cost
Edit `config.py`:
```python
LOGISTICS_AGENT = {
    'base_shipping_cost_per_km': 0.75,  # Was 0.50
}
```

### Change Discount Tiers
Edit `config.py`:
```python
'discount_tiers': {
    'small': {'min': 0, 'max': 5, 'discount': 0.0},
    'medium': {'min': 6, 'max': 25, 'discount': 0.05},
    'large': {'min': 26, 'max': 50, 'discount': 0.10},
    'bulk': {'min': 51, 'max': float('inf'), 'discount': 0.20},
}
```

---

## ❓ FAQ

**Q: What happens if materials are out of stock?**
A: The Procurement Agent returns `can_proceed: False`, consensus fails, and the order is rejected.

**Q: Can I order from different locations?**
A: Yes! Specify any location string. The system automatically categorizes it as local/regional/national/international.

**Q: What's the difference between final_price and total_deal_value?**
A: In this system, they're the same. `final_price` is what the customer pays, and `total_deal_value` is the company's revenue.

**Q: How fast are orders processed?**
A: <500ms per order through all 3 agents.

**Q: Can I add new products?**
A: Yes! Add to `data/materials.json` with the BOM, and ensure materials exist in `data/inventory.json`.

**Q: What's the "Consensus" mechanism?**
A: All 3 agents must approve + average confidence must be >75%. Orders fail if any agent disapproves.

---

## 🐛 Troubleshooting

### Python not found
```bash
python --version
```
If error: Install Python from python.org

### Flask not found
```bash
pip install flask
```

### Port 5000 already in use
```bash
python api.py  # Will try port 5000
# Or change port in api.py: app.run(port=5001)
```

### JSON decode error
Ensure POST request has valid JSON:
```bash
curl -X POST http://localhost:5000/process_order \
  -H "Content-Type: application/json" \
  -d '...'  # Must be valid JSON
```

---

## 📚 Learn More

- **Full Documentation**: See `DOCUMENTATION.md`
- **Code Comments**: Check `main.py` for detailed comments
- **Configuration**: Adjust behavior in `config.py`

Happy exploring! 🚀
