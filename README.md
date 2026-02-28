# SYNK

SYNK is a multi-agent manufacturing intelligence demo built for order intake, internal negotiation, and customer callback.

The system captures an order through a voice call, converts that into a structured order, sends it through multiple backend agents, and then calls the customer back with the final decision.

## What The Project Does

The project has two main parts:

1. Frontend
- Shows the voice-agent flow
- Displays agent orchestration visually
- Lets the user watch order negotiation round by round

2. Backend
- Starts the outbound customer call
- Extracts order details from voice/transcript data
- Runs specialized agents for procurement, production, logistics, finance, and sales
- Uses an orchestrator to combine agent decisions
- Calls the customer back with approval or rejection

## How The Flow Works

1. The system calls the customer
2. The customer shares the order details
3. The backend converts the conversation into a structured order
4. The order is submitted to the agent network
5. Agents evaluate feasibility, pricing, delivery, and commercial viability
6. The orchestrator checks consensus across agents
7. The customer receives a callback with the result

## Main Agents

- Procurement: checks materials, BOM, supplier availability
- Production: checks capacity, scheduling, and delivery feasibility
- Logistics: checks shipping mode, timelines, and transport cost
- Finance: checks margin, viable pricing, and deal economics
- Sales: checks customer fit and likely acceptance of revised terms
- Orchestrator: coordinates the flow and final decision

## Tech Stack

- Frontend: Next.js
- Backend: Flask
- Agent orchestration: LangGraph
- LLMs: OpenAI
- Voice calls: Vapi

## Key Capabilities

- Voice-based order intake
- Structured order extraction from transcript
- Multi-agent reasoning with tool usage
- Round-based negotiation in the UI
- Final callback to customer with decision

## Project Structure

Important backend files:

- [api_langgraph.py](c:/Users/PC%20User/Desktop/KAI_hackathon/kai_hackathon_1/api_langgraph.py): backend entrypoint
- [api_langgraph_app](c:/Users/PC%20User/Desktop/KAI_hackathon/kai_hackathon_1/api_langgraph_app): Flask app, routes, services, agents
- [outbound_call_agent.py](c:/Users/PC%20User/Desktop/KAI_hackathon/kai_hackathon_1/outbound_call_agent.py): Vapi voice call handling, transcript fallback, callback calls
- [data](c:/Users/PC%20User/Desktop/KAI_hackathon/kai_hackathon_1/data): inventory, materials, production, logistics, finance, and sales data

Frontend lives in the separate `kai_frontend` repository.

## Running The Backend

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
python api_langgraph.py
```

Backend runs at:

```txt
http://localhost:5000/api
```

## Team

This project was built by the team from Sartech Labs:

- Sreehari
- Rex Mathew
- Anjana
- Gauri
- Vishnu

## Summary

SYNK is a demo of how voice, LLMs, structured tools, and multi-agent orchestration can be combined into a single manufacturing order workflow.
