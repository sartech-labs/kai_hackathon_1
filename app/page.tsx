"use client"

import { useReducer, useCallback, useRef } from "react"
import type { DemoPhase, AgentId, AgentProposal, AgentMessage, RoundSummary, ConsensusResult, Order, SSEEvent } from "@/lib/synk/types"
import { DEFAULT_ORDER, VOICE_SCRIPT } from "@/lib/synk/scenario"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable"
import { SynkHeader } from "@/components/synk/header"
import { VoiceAgentPanel } from "@/components/synk/voice-agent-panel"
import { OrchestrationPanel } from "@/components/synk/orchestration-panel"
import type { TranscriptMessage } from "@/components/synk/voice-transcript"

// ─── State ───────────────────────────────────────────────────────────────

export interface CallLog {
  id: string
  customer: string
  product: string
  quantity: number
  outcome: "approved" | "rejected"
  finalPrice?: number
  timestamp: number
}

interface AppState {
  phase: DemoPhase
  backendSource: "unknown" | "backend" | "frontend-fallback"
  backendMessage: string | null
  order: Order
  transcript: TranscriptMessage[]
  activeAgents: Set<AgentId>
  proposals: Map<AgentId, AgentProposal>      // latest per agent (for status strip)
  allProposals: AgentProposal[]                // accumulated across all rounds (for timeline)
  rounds: RoundSummary[]
  consensus: ConsensusResult | null
  agentMessages: AgentMessage[]
  msgCounter: number
  callHistory: CallLog[]
}

type Action =
  | { type: "SET_PHASE"; phase: DemoPhase }
  | { type: "SET_BACKEND_STATUS"; backendSource: "unknown" | "backend" | "frontend-fallback"; backendMessage?: string }
  | { type: "SET_ORDER"; order: Order }
  | { type: "ADD_TRANSCRIPT"; msg: TranscriptMessage }
  | { type: "SET_ACTIVE_AGENTS"; agents: Set<AgentId> }
  | { type: "UPDATE_PROPOSAL"; proposal: AgentProposal }
  | { type: "ADD_ROUND"; round: RoundSummary }
  | { type: "SET_CONSENSUS"; consensus: ConsensusResult }
  | { type: "ADD_AGENT_MESSAGE"; agentMessage: AgentMessage }
  | { type: "CLEAR_PROPOSALS" }
  | { type: "SAVE_CALL_LOG"; log: CallLog }
  | { type: "RESET" }

const initialState: AppState = {
  phase: "idle",
  backendSource: "unknown",
  backendMessage: null,
  order: { ...DEFAULT_ORDER },
  transcript: [],
  activeAgents: new Set(),
  proposals: new Map(),
  allProposals: [],
  rounds: [],
  consensus: null,
  agentMessages: [],
  msgCounter: 0,
  callHistory: [],
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_PHASE":
      return { ...state, phase: action.phase }
    case "SET_BACKEND_STATUS":
      return { ...state, backendSource: action.backendSource, backendMessage: action.backendMessage ?? null }
    case "SET_ORDER":
      return { ...state, order: action.order }
    case "ADD_TRANSCRIPT": {
      const newCounter = state.msgCounter + 1
      return {
        ...state,
        transcript: [...state.transcript, { ...action.msg, id: `msg-${newCounter}` }],
        msgCounter: newCounter,
      }
    }
    case "SET_ACTIVE_AGENTS":
      return { ...state, activeAgents: new Set(action.agents) }
    case "UPDATE_PROPOSAL": {
      const newProposals = new Map(state.proposals)
      newProposals.set(action.proposal.agentId, action.proposal)
      return {
        ...state,
        proposals: newProposals,
        allProposals: [...state.allProposals, action.proposal],
      }
    }
    case "ADD_ROUND":
      return { ...state, rounds: [...state.rounds, action.round] }
    case "SET_CONSENSUS":
      return { ...state, consensus: action.consensus }
    case "ADD_AGENT_MESSAGE":
      return { ...state, agentMessages: [...state.agentMessages, action.agentMessage] }
    case "CLEAR_PROPOSALS":
      return { ...state, proposals: new Map() }
    case "SAVE_CALL_LOG":
      return { ...state, callHistory: [action.log, ...state.callHistory] }
    case "RESET":
      return { ...initialState, order: { ...DEFAULT_ORDER }, callHistory: state.callHistory }
    default:
      return state
  }
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ─── Component ───────────────────────────────────────────────────────────

export default function SynkDemo() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const abortRef = useRef<AbortController | null>(null)

  const addTranscript = useCallback(
    (sender: "customer" | "agent", text: string) => {
      dispatch({ type: "ADD_TRANSCRIPT", msg: { id: "", sender, text } })
    },
    []
  )

  // ─── Phase 1: Incoming Call
  const handleStartDemo = useCallback(async () => {
    dispatch({ type: "RESET" })
    dispatch({ type: "SET_PHASE", phase: "incoming-call" })
  }, [])

  // ─── Phase 2: Accept call -> play voice transcript
  const handleAcceptCall = useCallback(async () => {
    if (state.phase === "idle") {
      handleStartDemo()
      return
    }

    dispatch({ type: "SET_PHASE", phase: "active-call" })

    // Interleave customer and agent messages as a natural conversation
    const customerMsgs = VOICE_SCRIPT.customerMessages
    const agentMsgs = VOICE_SCRIPT.agentResponses
    const maxLen = Math.max(customerMsgs.length, agentMsgs.length)

    for (let i = 0; i < maxLen; i++) {
      if (i < customerMsgs.length) {
        addTranscript("customer", customerMsgs[i])
        await delay(1200)
      }
      if (i < agentMsgs.length) {
        addTranscript("agent", agentMsgs[i])
        await delay(1000)
      }
    }
  }, [state.phase, handleStartDemo, addTranscript])

  // ─── SSE event handler
  const processSSEEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case "backend_status":
          if (event.data.backendSource) {
            dispatch({
              type: "SET_BACKEND_STATUS",
              backendSource: event.data.backendSource,
              backendMessage: event.data.backendMessage,
            })
            if (event.data.backendSource === "frontend-fallback") {
              addTranscript("agent", event.data.backendMessage || "Backend unavailable. Showing frontend dummy data.")
            }
          }
          break

        case "phase_change":
          if (event.data.phase) {
            dispatch({ type: "SET_PHASE", phase: event.data.phase })
          }
          break

        case "agent_update":
          if (event.data.proposal) {
            dispatch({ type: "UPDATE_PROPOSAL", proposal: event.data.proposal })
          }
          break

        case "agent_message":
          if (event.data.agentMessage) {
            dispatch({ type: "ADD_AGENT_MESSAGE", agentMessage: event.data.agentMessage })
          }
          break

        case "round_complete":
          if (event.data.roundSummary) {
            dispatch({ type: "ADD_ROUND", round: event.data.roundSummary })
          }
          break

        case "consensus_reached":
          if (event.data.consensus) {
            dispatch({ type: "SET_CONSENSUS", consensus: event.data.consensus })
            dispatch({ type: "SAVE_CALL_LOG", log: {
              id: `call-${Date.now()}`,
              customer: state.order.customer,
              product: state.order.product,
              quantity: state.order.quantity,
              outcome: event.data.consensus.approved ? "approved" : "rejected",
              finalPrice: event.data.consensus.finalPrice,
              timestamp: Date.now(),
            }})
          }
          break

        case "callback_start":
          addTranscript("agent", "Calling back customer...")
          break

        case "callback_message":
          if (event.data.message) {
            addTranscript("agent", event.data.message)
          }
          break

        case "done":
          break
      }
    },
    [addTranscript]
  )

  // ─── Phase 3+: Submit order -> SSE stream
  const handleSubmitOrder = useCallback(async () => {
    dispatch({ type: "SET_PHASE", phase: "order-broadcast" })

    const allAgents: AgentId[] = ["production", "finance", "logistics", "procurement", "sales"]
    dispatch({ type: "SET_ACTIVE_AGENTS", agents: new Set(allAgents) })

    abortRef.current = new AbortController()

    try {
      const orderParam = encodeURIComponent(JSON.stringify(state.order))
      const response = await fetch(`/api/orchestrate?order=${orderParam}`, {
        signal: abortRef.current.signal,
      })

      if (!response.body) return

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          const dataLine = line.replace(/^data: /, "").trim()
          if (!dataLine) continue

          try {
            const event: SSEEvent = JSON.parse(dataLine)
            processSSEEvent(event)
          } catch {
            // Skip malformed events
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        console.error("SSE stream error:", err)
      }
    }
  }, [state.order, processSSEEvent])

  const handleOrderChange = useCallback((order: Order) => {
    dispatch({ type: "SET_ORDER", order })
  }, [])

  const handleNewCall = useCallback(() => {
    dispatch({ type: "RESET" })
    dispatch({ type: "SET_PHASE", phase: "incoming-call" })
  }, [])

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <SynkHeader
        phase={state.phase}
        backendSource={state.backendSource}
        backendMessage={state.backendMessage || undefined}
      />

      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left: Voice Agent */}
        <ResizablePanel defaultSize={33} minSize={25} maxSize={45}>
          <VoiceAgentPanel
            phase={state.phase}
            order={state.order}
            transcript={state.transcript}
            consensus={state.consensus}
            callHistory={state.callHistory}
            onAcceptCall={handleAcceptCall}
            onOrderChange={handleOrderChange}
            onSubmitOrder={handleSubmitOrder}
            onNewCall={handleNewCall}
          />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Right: Agent Orchestration */}
        <ResizablePanel defaultSize={67} minSize={45}>
          <OrchestrationPanel
            phase={state.phase}
            activeAgents={state.activeAgents}
            proposals={state.proposals}
            allProposals={state.allProposals}
            rounds={state.rounds}
            consensus={state.consensus}
            order={state.order}
            agentMessages={state.agentMessages}
          />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
