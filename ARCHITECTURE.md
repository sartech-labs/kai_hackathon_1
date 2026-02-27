# 🏗️ Architecture & Design Details

## System Architecture Overview

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      INCOMING REQUEST                           │
│  {order_id, product_sku, quantity, customer_location, priority} │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ Manager Agent  │
                    │ (Orchestrator) │
                    └────────┬───────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐         ┌──────────┐       ┌──────────────┐
    │ AGENT 1 │         │ AGENT 2  │       │   AGENT 3    │
    │Procure- │         │Logistics │       │Consolidation│
    │ment     │         │/ Freight │       │(Final Deal) │
    └────┬────┘         └────┬─────┘       └──────┬───────┘
         │                   │                     │
    Check Inventory    Calculate Shipping    Apply Discounts
    Verify Stock       Determine Location    Calculate Price
    Calculate Costs    Estimate Delivery     Generate Summary
         │                   │                     │
         └───────────────────┼─────────────────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │ Consensus Check    │
                    ├────────────────────┤
                    │ All agents OK?     │
                    │ Confidence > 75%?  │
                    │ Valid data?        │
                    └────────┬───────────┘
                             │
                   ┌─────────┴──────────┐
                   │                    │
               ✅ YES                ❌ NO
                   │                    │
                   ▼                    ▼
            ┌────────────┐       ┌──────────────┐
            │ RESPONSE   │       │ ERROR RESP   │
            │ SUCCESS    │       │ FAILURE      │
            └────────────┘       └──────────────┘
```

---

## Agent Interaction Sequence

### Detailed Sequence Diagram

```
Manager    Procurement    Logistics    Consolidation
  │            │             │              │
  │─── request─────→│        │              │
  │                 │        │              │
  │        evaluate()              │              │
  │◄────────response──│        │              │
  │        (availability,      │              │
  │         cost)              │              │
  │                │           │              │
  │───────────request─────────→│              │
  │                │           │              │
  │                │   evaluate()             │
  │                │◄───response──│           │
  │                │  (shipping,  │           │
  │                │   delivery)  │           │
  │                │             │           │
  │────────────────────────request───────────→│
  │                │             │            │
  │                │             │  consolidate()
  │                │             │◄──response──│
  │                │             │  (final_price,
  │                │             │   discount,
  │                │             │   deal_val)
  │                │             │            │
  │ check_consensus()            │            │
  │  (all approved?)             │            │
  │  (avg conf > 75%)            │            │
  │                │             │            │
  └────────────────┴─────────────┴────────────┘
         │
    [Generate Final Response]
         │
    Return to Customer
```

---

## Agent Responsibility Matrix

### Agent 1: Procurement Agent

**Input:**
- Product SKU
- Order quantity

**Process:**
1. Load product BOM (Bill of Materials)
2. For each material in BOM:
   - Get required quantity = material_qty × order_quantity
   - Check available stock
   - Get unit cost
   - Verify all materials available
3. Calculate total material cost
4. Assess confidence level

**Output:**
```python
AgentResponse(
    agent_name="Procurement Agent",
    can_proceed=True/False,
    reasoning="Based on stock levels",
    details={
        'product_sku': 'PMP-STD-100',
        'quantity': 15,
        'material_availability': {...},
        'total_unit_cost': 9000,
        'total_cost': 135000
    },
    confidence=0.95
)
```

**Confidence Scoring:**
- Base confidence: 0.95
- Reduced to 0.70 if any material short
- Factors: Inventory accuracy, data freshness

---

### Agent 2: Logistics Agent

**Input:**
- Customer location
- Total material cost
- Order quantity
- Priority level

**Process:**
1. Determine location type:
   - Keywords: "local", "city" → local (50 km)
   - Keywords: "state", "region" → regional (300 km)
   - Keywords: "country", "national" → national (1000 km)
   - Others → international (5000 km)

2. Calculate shipping cost:
   - Base = distance_km × $0.50
   - Weight = quantity × 0.5 units
   - Shipping = Base + (Weight × $2)

3. Determine delivery date:
   - Local: 2 days
   - Regional: 5 days
   - National: 7 days
   - International: 14 days
   - Expedited: divide by 2, minimum 1 day

4. Assess confidence

**Output:**
```python
AgentResponse(
    agent_name="Logistics Agent",
    can_proceed=True,
    reasoning="Distance-based shipping calculated",
    details={
        'location_type': 'regional',
        'distance_km': 300,
        'shipping_cost': 350.00,
        'delivery_date': '2026-03-04',
        'lead_time_days': 5,
        'priority': 'normal'
    },
    confidence=0.90
)
```

**Confidence Scoring:**
- Base confidence: 0.90
- Factors: Location ambiguity, shipping reliability

---

### Agent 3: Consolidation Agent

**Input:**
- Procurement Agent response
- Logistics Agent response
- Order quantity

**Process:**
1. Verify both agents can proceed
2. Extract costs:
   - material_cost = from Procurement
   - shipping_cost = from Logistics
   - delivery_date = from Logistics

3. Calculate discount:
   - Lookup quantity in discount_tiers
   - Get discount_rate (0%, 5%, 10%, or 15%)
   - discount_amount = subtotal × discount_rate
   - discounted_subtotal = subtotal - discount_amount

4. Apply profit margin:
   - final_price = discounted_subtotal × 1.25

5. Assess confidence

**Output:**
```python
AgentResponse(
    agent_name="Consolidation Agent",
    can_proceed=True,
    reasoning="Deal consolidated with 5% discount",
    details={
        'material_cost': 135000.00,
        'shipping_cost': 40.00,
        'subtotal': 135040.00,
        'discount_rate': 0.05,
        'discount_amount': 6752.00,
        'discounted_subtotal': 128288.00,
        'profit_margin': 0.25,
        'final_price': 160360.00,
        'total_deal_value': 160360.00,
        'delivery_date': '2026-03-01',
        'quantity': 15
    },
    confidence=0.95
)
```

**Confidence Scoring:**
- Base confidence: 0.95
- Factors: Data accuracy, pricing model reliability

---

## Consensus Algorithm

### Requirements for Order Approval

```
CONSENSUS = (
    (Agent1.can_proceed AND Agent2.can_proceed AND Agent3.can_proceed) AND
    (Average_Confidence > 0.75)
)

Average_Confidence = (Agent1.confidence + Agent2.confidence + Agent3.confidence) / 3

Decision:
  IF CONSENSUS = TRUE:
    Order APPROVED → Generate SUCCESS response
  ELSE:
    Order REJECTED → Generate FAILURE response
```

### Confidence Thresholds

```
Scenario 1: All Agents Approve
┌──────────┬──────────┬──────────────┐
│   Agent  │ Approve? │ Confidence   │
├──────────┼──────────┼──────────────┤
│    1     │   YES    │    0.95      │
│    2     │   YES    │    0.90      │
│    3     │   YES    │    0.95      │
├──────────┼──────────┼──────────────┤
│ AVERAGE  │   YES    │    0.93 (>75%)
└──────────┴──────────┴──────────────┘
Result: ✅ CONSENSUS REACHED

Scenario 2: Agent Rejects (Out of Stock)
┌──────────┬──────────┬──────────────┐
│   Agent  │ Approve? │ Confidence   │
├──────────┼──────────┼──────────────┤
│    1     │    NO    │    0.70      │
│    2     │   YES    │    0.90      │
│    3     │    NO    │    0.00      │
├──────────┼──────────┼──────────────┤
│ AVERAGE  │    NO    │    0.53 (<75%)
└──────────┴──────────┴──────────────┘
Result: ❌ CONSENSUS FAILED
```

---

## Data Flow & Structure

### Order Request Structure

```json
{
  "order_id": "ORD-001",           // Unique order identifier
  "product_sku": "PMP-STD-100",    // Product SKU
  "quantity": 15,                  // Number of units
  "customer_location": "local city", // Shipping destination
  "priority": "normal"             // "normal" or "expedited"
}
```

### Agent Response Structure

```json
{
  "agent_name": "Agent Name",
  "can_proceed": true,             // Boolean approval
  "reasoning": "Explanation",      // Human-readable reason
  "details": {                     // Agent-specific data
    "key1": "value1",
    "key2": "value2"
  },
  "confidence": 0.95              // 0.0 to 1.0
}
```

### Final API Response

```json
{
  "status": "SUCCESS",
  "order_id": "ORD-001",
  "product_sku": "PMP-STD-100",
  "quantity": 15,
  "customer_location": "local city",
  "final_price": 160360.00,
  "total_deal_value": 160360.00,
  "delivery_date": "2026-03-01",
  "cost_breakdown": {
    "material_cost": 135000.00,
    "shipping_cost": 40.00,
    "discount_amount": 6752.00,
    "discount_rate": 0.05,
    "profit_margin": 0.25
  },
  "consensus_reached": true,
  "timestamp": "2026-02-27T16:32:52.254303"
}
```

---

## Class Hierarchy

```
┌─────────────────────────────────┐
│        ManagerAgent             │
│ ┌──────────────────────────────┐│
│ │ - procurement_agent          ││
│ │ - logistics_agent            ││
│ │ - consolidation_agent        ││
│ │                              ││
│ │ + process_order()            ││
│ │ + _check_consensus()         ││
│ │ + _generate_final_response() ││
│ └──────────────────────────────┘│
└────┬────────────┬───────────────┘
     │            │
     ▼            ▼
┌──────────┐  ┌──────────┐
│Agent 1   │  │Agent 2   │
│Procure-  │  │Logistics │
│ment      │  │          │
│          │  │          │
│evaluate()│  │evaluate()│
└──────────┘  └──────────┘
              
     ▼
 ┌──────────┐
 │Agent 3   │
 │Consol-   │
 │idation   │
 │          │
 │consolidate()
 └──────────┘

All return: AgentResponse
```

---

## State Machine: Order Processing

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Parse     │
                    │  Request    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌──────────┐         ┌──────────────┐
        │ VALID    │         │  INVALID     │
        └────┬─────┘         └────┬─────────┘
             │                    │
             ▼                    ▼
      ┌──────────┐       ┌──────────────┐
      │ Agent 1  │       │  FAILURE     │
      │ Procure  │       │  RESPONSE    │
      └────┬─────┘       └──────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
 FAIL         PROCEED
   │             │
   │             ▼
   │         ┌──────────┐
   │         │ Agent 2  │
   │         │ Logistics│
   │         └────┬─────┘
   │              │
   │         ┌────┴─────┐
   │         ▼          ▼
   │      FAIL       PROCEED
   │        │           │
   │        │           ▼
   │        │       ┌──────────┐
   │        │       │ Agent 3  │
   │        │       │Consol    │
   │        │       └────┬─────┘
   │        │            │
   │        │       ┌────┴─────┐
   │        │       ▼          ▼
   │        │    FAIL       PROCEED
   │        │      │           │
   └────────┼──────┴───────────┤
            ▼                  ▼
        CONSENSUS          CONSENSUS
        FAILED?            SUCCESS?
            │                  │
            ├─ NO ─┐           │
            │      ▼           ▼
            │   ┌────────┐  ┌────────┐
            └───│FAILURE │  │SUCCESS │
                │RESPONSE│  │RESPONSE│
                └────────┘  └────────┘
                      │          │
                      └────┬─────┘
                           ▼
                        ┌────────┐
                        │  END   │
                        └────────┘
```

---

## Class Interactions

```
┌──────────────────────────────────────────────────────┐
│            Manager Agent                            │
│                                                      │
│  1. Receives Order Request                          │
│  2. Creates instances/calls Agent 1                 │
│  3. Gets Agent 1 Response                           │
│  4. Calls Agent 2 with context                      │
│  5. Gets Agent 2 Response                           │
│  6. Calls Agent 3 with both responses               │
│  7. Gets Agent 3 Response                           │
│  8. Checks Consensus across all 3                   │
│  9. Generates Final Response                        │
│  10. Returns to Caller                              │
└──────────────────────────────────────────────────────┘
            │              │              │
            ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Agent 1     │  │  Agent 2     │  │  Agent 3     │
│ Procurement  │  │ Logistics    │  │ Consolidation│
│              │  │              │  │              │
│ Depends on:  │  │ Depends on:  │  │ Depends on:  │
│ - Inventory  │  │ - Location   │  │ - Agent 1 OK │
│ - Materials  │  │ - Distance   │  │ - Agent 2 OK │
│ - Stock      │  │ - Priority   │  │ - Pricing    │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Configuration Flow

```
┌────────────────┐
│  config.py     │
│  Defines:      │
│ - Profit margin│
│ - Discounts    │
│ - Shipping     │
│ - Lead times   │
│ - Features     │
└────────┬───────┘
         │
    ┌────┴────┬────────┬─────────┐
    │          │        │         │
    ▼          ▼        ▼         ▼
 Agent 1     Agent 2  Agent 3   Manager
 Uses:       Uses:    Uses:     Reads:
 -           Distance Discount  All
 Profit      Rates    Config
 Margin      Lead
            Times
```

---

## Error Handling Flow

```
Request Validations:
├─ JSON parsing
├─ Required fields check
├─ Type validation (quantity > 0)
├─ SKU existence check
└─ Location validation

Agent Validations:
├─ Inventory availability check
├─ Stock sufficiency check
├─ Pricing calculations
├─ Delivery date generation
└─ Discount tier determination

Consensus Validations:
├─ can_proceed checks
├─ Confidence threshold
├─ Logic consistency
└─ Data completeness

Response Generation:
├─ SUCCESS path: Include pricing
├─ FAILURE path: Include reason
└─ Always include timestamp
```

---

## Performance Characteristics

```
Operation              Time        Scalability
─────────────────────────────────────────────
Load JSON Data        ~5ms        O(n) materials
Validate Order        <1ms        O(1)
Agent 1 Process       ~30ms       O(m) materials
Agent 2 Process       ~20ms       O(1)
Agent 3 Process       ~25ms       O(1)
Consensus Check       <5ms        O(1)
Response Gen          ~10ms       O(1)
─────────────────────────────────────────────
Total Per Order       <100ms      Highly scalable
Throughput            100+        Orders/second
Parallelization       No          Sequential
Memory Usage          ~1MB        Per request
```

---

## Integration Points

```
External Systems
      │
      ├─→ [REST API Endpoint]
      │   ├─→ HTTP POST
      │   ├─→ JSON Request
      │   └─→ JSON Response
      │
      ├─→ [Database] (Future)
      │   ├─→ Inventory DB
      │   ├─→ Order History
      │   └─→ Customer Data
      │
      ├─→ [Message Queue] (Future)
      │   ├─→ RabbitMQ
      │   ├─→ Kafka
      │   └─→ SQS
      │
      └─→ [Analytics] (Future)
          ├─→ Order Metrics
          ├─→ Agent Performance
          └─→ Cost Analysis
```

---

## Security Considerations

```
Current Implementation:
✓ Input validation
✓ Type checking
✓ Error handling
✓ No SQL injection (JSON only)

Future Enhancements:
□ Authentication
□ Authorization
□ Rate limiting
□ CORS configuration
□ HTTPS enforcement
□ API key validation
□ Request signing
□ Audit logging
```

---

## Extensibility Points

```
Easy to Add:
├─ New Agents (follow Agent pattern)
├─ New Products (edit materials.json)
├─ New Materials (edit inventory.json)
├─ New Pricing Rules (edit config.py)
├─ New Discount Tiers (edit config.py)
└─ New Locations (edit LogisticsAgent)

Medium Difficulty:
├─ Multiple Suppliers
├─ Alternative Logistics Providers
├─ Price Negotiation Logic
├─ Real-time Inventory Updates
└─ Customer Preferences

Hard to Add:
├─ Database Integration
├─ Complex Pricing Models
├─ Supply Chain Optimization
├─ Predictive Analytics
└─ Third-party API Integration
```

---

This architecture provides a solid foundation for an intelligent, scalable, and maintainable multi-agent order processing system.
