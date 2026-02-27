"use client"

import { useRef, useEffect, useState, useMemo } from "react"
import Image from "next/image"
import type {
  DemoPhase, AgentId, AgentProposal, RoundSummary,
  ConsensusResult, Order, AgentMessage, ActionStep,
} from "@/lib/synk/types"
import { AGENT_CONFIGS } from "@/lib/synk/types"
import { ConsensusCard } from "./consensus-card"
import {
  Zap, Loader2,
  Terminal, Database, Brain, ArrowRight, AlertTriangle, CheckCircle2,
} from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

// ─── Agent avatar map ──────────────────────────────────────────
const AGENT_AVATARS: Record<AgentId | "orchestrator", string> = {
  production: "/agents/production.jpg",
  finance: "/agents/finance.jpg",
  logistics: "/agents/logistics.jpg",
  procurement: "/agents/procurement.jpg",
  sales: "/agents/sales.jpg",
  orchestrator: "/agents/orchestrator.jpg",
}

// ─── Step icons ────────────────────────────────────────────────
const STEP_ICONS: Record<ActionStep["kind"], { Icon: React.ComponentType<{ className?: string }>; bg: string; fg: string; label: string }> = {
  tool_call:   { Icon: Terminal, bg: "bg-blue-50", fg: "text-blue-600", label: "TOOL" },
  tool_result: { Icon: Database, bg: "bg-emerald-50", fg: "text-emerald-600", label: "RESULT" },
  thinking:    { Icon: Brain, bg: "bg-amber-50", fg: "text-amber-600", label: "THINKING" },
  response:    { Icon: ArrowRight, bg: "bg-indigo-50", fg: "text-indigo-600", label: "RESPONSE" },
  objection:   { Icon: AlertTriangle, bg: "bg-red-50", fg: "text-red-600", label: "OBJECTION" },
  agreement:   { Icon: CheckCircle2, bg: "bg-emerald-50", fg: "text-emerald-600", label: "AGREED" },
}

// ─── Layout: agent positions as % of canvas ──────────────────
// Pentagon: Production top-center, Finance top-right, Sales top-left,
// Logistics bottom-right, Procurement bottom-left
interface AgentLayout {
  id: AgentId
  x: number; y: number
  calloutSide: "left" | "right" | "bottom"
}

const AGENT_LAYOUT: AgentLayout[] = [
  { id: "production",  x: 50, y: 8,   calloutSide: "right" },
  { id: "finance",     x: 85, y: 35,  calloutSide: "left" },
  { id: "sales",       x: 15, y: 35,  calloutSide: "right" },
  { id: "logistics",   x: 75, y: 78,  calloutSide: "left" },
  { id: "procurement", x: 25, y: 78,  calloutSide: "right" },
]

const ORCH_POS = { x: 50, y: 48 }

// ─── Props ───────────────────────────────────────────────────
interface OrchestrationPanelProps {
  phase: DemoPhase
  activeAgents: Set<AgentId>
  proposals: Map<AgentId, AgentProposal>
  allProposals: AgentProposal[]
  rounds: RoundSummary[]
  consensus: ConsensusResult | null
  order: Order
  agentMessages: AgentMessage[]
}

// ─── Compact Callout ─────────────────────────────────────────
// isLive=true: animate steps one by one (current round)
// isLive=false: show collapsed tool icons, expand on click (past round)
function AgentCallout({ proposal, color, isLive }: { proposal: AgentProposal | undefined; color: string; isLive: boolean }) {
  const [visibleStep, setVisibleStep] = useState(-1)
  const [expanded, setExpanded] = useState(false)

  // Live animation: reveal steps one by one
  useEffect(() => {
    if (!isLive || !proposal?.actions?.length) { setVisibleStep(-1); return }
    setVisibleStep(0)
    let idx = 0
    const iv = setInterval(() => {
      idx++
      if (idx >= proposal.actions.length) { clearInterval(iv); return }
      setVisibleStep(idx)
    }, 700)
    return () => clearInterval(iv)
  }, [isLive, proposal?.actions, proposal?.round])

  if (!proposal?.actions?.length) return null

  const statusBg = proposal.status === "agreed" ? "#dcfce7" : proposal.status === "objecting" ? "#fef2f2" : `${color}15`
  const statusFg = proposal.status === "agreed" ? "#16a34a" : proposal.status === "objecting" ? "#dc2626" : color

  // ── Past round: collapsed icon row, expandable ──
  if (!isLive) {
    return (
      <div className="w-[180px] rounded-xl bg-card border border-border shadow-lg shadow-black/5 overflow-hidden animate-pop-in">
        <div className="h-[2px]" style={{ background: color }} />
        <button
          className="w-full flex items-center gap-1.5 px-2.5 py-2 hover:bg-secondary/50 transition-colors cursor-pointer"
          onClick={() => setExpanded(e => !e)}
        >
          {/* Tool icon row */}
          <div className="flex items-center gap-0.5 flex-1 min-w-0">
            {proposal.actions.map((action, i) => {
              const meta = STEP_ICONS[action.kind]
              return (
                <div
                  key={i}
                  className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 ${meta.bg}`}
                  title={`${meta.label}: ${action.label}`}
                >
                  <meta.Icon className={`w-2.5 h-2.5 ${meta.fg}`} />
                </div>
              )
            })}
          </div>
          <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full shrink-0" style={{ backgroundColor: statusBg, color: statusFg }}>
            {proposal.status === "agreed" ? "OK" : proposal.status === "objecting" ? "OBJ" : "..."}
          </span>
        </button>
        {/* Expanded detail */}
        {expanded && (
          <div className="max-h-[140px] overflow-y-auto px-2 pb-2 space-y-1 border-t border-border">
            {proposal.actions.map((action, i) => {
              const meta = STEP_ICONS[action.kind]
              return (
                <div key={i} className={`rounded-lg p-1.5 ${meta.bg}`}>
                  <div className="flex items-center gap-1 mb-0.5">
                    <meta.Icon className={`w-2.5 h-2.5 shrink-0 ${meta.fg}`} />
                    <span className={`text-[8px] font-bold ${meta.fg}`}>{meta.label}</span>
                    <code className="text-[7px] font-mono text-muted-foreground truncate">{action.label}</code>
                  </div>
                  <p className="text-[8px] leading-snug text-secondary-foreground line-clamp-2">{action.detail}</p>
                  {action.data && Object.keys(action.data).length > 0 && (
                    <div className="flex flex-wrap gap-0.5 mt-0.5">
                      {Object.entries(action.data).slice(0, 3).map(([k, v]) => (
                        <span key={k} className={`text-[7px] font-mono px-1 py-0.5 rounded ${meta.bg} ${meta.fg}`}>
                          {k}: <strong>{String(v)}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  // ── Live round: animate steps ──
  if (visibleStep < 0) return null
  const shownActions = proposal.actions.slice(Math.max(0, visibleStep - 1), visibleStep + 1)

  return (
    <div className="w-[180px] rounded-xl bg-card border border-border shadow-lg shadow-black/5 overflow-hidden animate-pop-in">
      <div className="h-[2px]" style={{ background: color }} />
      <div className="flex items-center justify-between px-2.5 py-1.5">
        <span className="text-[9px] font-mono font-bold text-muted-foreground">R{proposal.round}</span>
        <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full" style={{ backgroundColor: statusBg, color: statusFg }}>
          {proposal.status.toUpperCase()}
        </span>
      </div>
      <div className="max-h-[110px] overflow-y-auto px-2 pb-2 space-y-1">
        {shownActions.map((action, i) => {
          const meta = STEP_ICONS[action.kind]
          const isLatest = i === shownActions.length - 1
          return (
            <div key={`${proposal.round}-${action.kind}-${i}`} className={`rounded-lg p-1.5 ${isLatest ? meta.bg : "bg-secondary/50"}`} style={{ opacity: isLatest ? 1 : 0.6 }}>
              <div className="flex items-center gap-1 mb-0.5">
                <meta.Icon className={`w-2.5 h-2.5 shrink-0 ${meta.fg}`} />
                <span className={`text-[8px] font-bold ${meta.fg}`}>{meta.label}</span>
                {(action.kind === "tool_call" || action.kind === "tool_result") && (
                  <code className="text-[7px] font-mono text-muted-foreground truncate">{action.label}</code>
                )}
              </div>
              <p className="text-[8px] leading-snug text-secondary-foreground line-clamp-2">{action.detail}</p>
              {action.data && Object.keys(action.data).length > 0 && (
                <div className="flex flex-wrap gap-0.5 mt-0.5">
                  {Object.entries(action.data).slice(0, 3).map(([k, v]) => (
                    <span key={k} className={`text-[7px] font-mono px-1 py-0.5 rounded ${meta.bg} ${meta.fg}`}>
                      {k}: <strong>{String(v)}</strong>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}
        {visibleStep < (proposal.actions.length - 1) && (
          <div className="flex items-center gap-1 px-1.5">
            <Loader2 className="w-2.5 h-2.5 animate-spin text-muted-foreground" />
            <span className="text-[8px] text-muted-foreground animate-pulse">Processing...</span>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Main Panel ──────────────────────────────────────────────

export function OrchestrationPanel({
  phase, activeAgents, proposals, allProposals,
  rounds, consensus, order, agentMessages,
}: OrchestrationPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ w: 800, h: 500 })
  const [selectedRound, setSelectedRound] = useState<number>(1)

  const isIdle = phase === "idle" || phase === "incoming-call" || phase === "active-call"
  const isNegotiating = phase.startsWith("round-") || phase === "order-broadcast"
  const isDone = phase === "consensus" || phase === "callback" || phase === "done"
  const currentRound = phase === "round-1" ? 1 : phase === "round-2" ? 2 : phase === "round-3" ? 3 : isDone ? 3 : 0

  // Auto-switch to latest round as negotiation progresses, or Final when done
  useEffect(() => {
    if (consensus) {
      setSelectedRound(0)
    } else if (currentRound > 0) {
      setSelectedRound(currentRound)
    }
  }, [currentRound, consensus])

  // Filter proposals to only the selected round
  const roundProposals = useMemo(() => {
    const map: Partial<Record<AgentId, AgentProposal>> = {}
    for (const p of allProposals) {
      if (p.round === selectedRound) map[p.agentId] = p
    }
    return map
  }, [allProposals, selectedRound])

  // Filter messages to only the selected round
  const roundMessages = useMemo(() => {
    return agentMessages.filter(m => m.round === selectedRound)
  }, [agentMessages, selectedRound])

  // Determine max completed round for tabs
  const maxRound = Math.max(currentRound, rounds.length)

  // Highlight connection on message
  const [activeLink, setActiveLink] = useState<AgentId | null>(null)
  useEffect(() => {
    const lastMsg = agentMessages[agentMessages.length - 1]
    if (!lastMsg) return
    const id = lastMsg.from === "orchestrator" ? (lastMsg.to as AgentId) : (lastMsg.from as AgentId)
    setActiveLink(id)
    const t = setTimeout(() => setActiveLink(null), 800)
    return () => clearTimeout(t)
  }, [agentMessages])

  // Measure container
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const e = entries[0]
      if (e) setDims({ w: e.contentRect.width, h: e.contentRect.height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const px = (layout: { x: number; y: number }) => ({
    x: (layout.x / 100) * dims.w,
    y: (layout.y / 100) * dims.h,
  })
  const orchPx = px(ORCH_POS)

  const recentMsgs = roundMessages.slice(-4)

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">Agent Orchestration</span>
        </div>
        {!isIdle && (
          <div className="flex items-center gap-3">
            {isNegotiating && (
              <span className="flex items-center gap-1.5 text-[10px] font-semibold text-primary">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                LIVE
              </span>
            )}
            <span className="text-[10px] font-mono text-muted-foreground">
              {currentRound > 0 ? `Round ${Math.min(currentRound, 3)}/3` : "Initializing"}
            </span>
          </div>
        )}
      </div>

      {/* Round Tabs -- always visible once negotiation starts */}
      {maxRound > 0 && (
        <div className="shrink-0 border-b border-border bg-card px-4 py-1.5 flex items-center gap-1">
          {[1, 2, 3].map(r => {
            const isAvailable = r <= maxRound
            const isSelected = r === selectedRound
            const isLive = r === currentRound && isNegotiating
            return (
              <button
                key={r}
                onClick={() => isAvailable && setSelectedRound(r)}
                disabled={!isAvailable}
                className={`
                  flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all
                  ${isSelected
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : isAvailable
                      ? "bg-secondary text-secondary-foreground hover:bg-accent"
                      : "text-muted-foreground/40 cursor-not-allowed"
                  }
                `}
              >
                {isLive && <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />}
                Round {r}
                {rounds[r - 1] && !isLive && (
                  <CheckCircle2 className="w-3 h-3 opacity-60" />
                )}
              </button>
            )
          })}
          {consensus && (
            <button
              onClick={() => setSelectedRound(0)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ml-auto
                ${selectedRound === 0 ? "bg-emerald-600 text-white shadow-sm" : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"}`}
            >
              <CheckCircle2 className="w-3 h-3" />
              Consensus
            </button>
          )}
        </div>
      )}

      {/* Network Canvas */}
      <div ref={containerRef} className="flex-1 relative min-h-0 overflow-hidden">
        {/* Consensus overlay -- shown when Final tab selected or auto at end */}
        {consensus && selectedRound === 0 && (
          <div className="absolute inset-0 z-30 bg-background/90 backdrop-blur-sm overflow-y-auto p-6">
            <ConsensusCard consensus={consensus} order={order} />
          </div>
        )}

        {/* SVG layer: grid + connection lines */}
        <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 1 }}>
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#94a3b8" strokeWidth="0.3" opacity="0.1" />
            </pattern>
          </defs>

          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Connection lines */}
          {AGENT_LAYOUT.map(layout => {
            const config = AGENT_CONFIGS.find(c => c.id === layout.id)!
            const agentPx = px(layout)
            const isActive = activeAgents.has(layout.id)
            const isHighlighted = activeLink === layout.id
            return (
              <g key={layout.id}>
                <line
                  x1={orchPx.x} y1={orchPx.y} x2={agentPx.x} y2={agentPx.y}
                  stroke={config.color} strokeWidth={isHighlighted ? 2.5 : 1}
                  opacity={isHighlighted ? 0.4 : isActive ? 0.12 : 0.05}
                  strokeLinecap="round"
                />
                {isActive && isNegotiating && (
                  <line
                    x1={orchPx.x} y1={orchPx.y} x2={agentPx.x} y2={agentPx.y}
                    stroke={config.color} strokeWidth={1.5}
                    strokeDasharray="4 8" className="animate-dash-flow"
                    opacity={isHighlighted ? 0.5 : 0.12}
                    strokeLinecap="round"
                  />
                )}
                {isHighlighted && (
                  <circle r="4" fill={config.color} opacity="0.8">
                    <animateMotion dur="0.5s" fill="freeze" path={`M${orchPx.x},${orchPx.y} L${agentPx.x},${agentPx.y}`} />
                    <animate attributeName="opacity" from="0.8" to="0" dur="0.5s" fill="freeze" />
                  </circle>
                )}
              </g>
            )
          })}
        </svg>

        {/* HTML layer: agent avatar nodes + callouts */}
        <div className="absolute inset-0" style={{ zIndex: 2, pointerEvents: "none" }}>
          {/* Orchestrator node */}
          <div
            className="absolute flex flex-col items-center"
            style={{ left: `${ORCH_POS.x}%`, top: `${ORCH_POS.y}%`, transform: "translate(-50%, -50%)" }}
          >
            <div className={`w-14 h-14 rounded-full bg-card border-2 shadow-lg overflow-hidden ${isNegotiating ? "border-primary shadow-primary/20" : "border-border"}`}>
              <Image src={AGENT_AVATARS.orchestrator} alt="Orchestrator" width={56} height={56} className="object-cover w-full h-full" />
            </div>
            <span className="text-[9px] font-semibold text-muted-foreground mt-1.5 tracking-wide">ORCHESTRATOR</span>
          </div>

          {/* Agent nodes + callouts */}
          {AGENT_LAYOUT.map(layout => {
            const config = AGENT_CONFIGS.find(c => c.id === layout.id)!
            const isActive = activeAgents.has(layout.id)
            const proposal = roundProposals[layout.id]

            // Callout position offset
            const calloutX = layout.calloutSide === "right" ? 42 : layout.calloutSide === "left" ? -222 : -90
            const calloutY = layout.calloutSide === "bottom" ? 42 : -30

            return (
              <div key={layout.id}>
                {/* Avatar node */}
                <div
                  className="absolute flex flex-col items-center"
                  style={{ left: `${layout.x}%`, top: `${layout.y}%`, transform: "translate(-50%, -50%)" }}
                >
                  {/* Pulse ring when active */}
                  {isActive && isNegotiating && (
                    <div className="absolute w-16 h-16 rounded-full animate-ring-pulse" style={{ border: `2px solid ${config.color}30` }} />
                  )}
                  {/* Avatar circle */}
                  <div
                    className="w-12 h-12 rounded-full bg-card border-2 shadow-md overflow-hidden transition-all"
                    style={{
                      borderColor: isActive ? config.color : "#e2e8f0",
                      boxShadow: isActive ? `0 4px 14px ${config.color}25` : undefined,
                    }}
                  >
                    <Image src={AGENT_AVATARS[layout.id]} alt={config.name} width={48} height={48} className="object-cover w-full h-full" />
                  </div>
                  {/* Name + role */}
                  <span className="text-[9px] font-bold mt-1" style={{ color: isActive ? config.color : "#94a3b8" }}>
                    {config.name}
                  </span>
                  <span className="text-[7px] text-muted-foreground">{config.role}</span>

                  {/* Status dot */}
                  {proposal && (
                    <div
                      className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-card"
                      style={{ backgroundColor: proposal.status === "agreed" ? "#16a34a" : proposal.status === "objecting" ? "#dc2626" : config.color }}
                    />
                  )}
                </div>

                {/* Callout popup */}
                {proposal && (
                  <div
                    className="absolute"
                    style={{
                      left: `${layout.x}%`, top: `${layout.y}%`,
                      transform: `translate(${calloutX}px, ${calloutY}px)`,
                      pointerEvents: "auto",
                    }}
                  >
                    <AgentCallout proposal={proposal} color={config.color} isLive={selectedRound === currentRound && isNegotiating} />
                  </div>
                )}

                {/* Analyzing spinner */}
                {!proposal && isActive && isNegotiating && (
                  <div
                    className="absolute flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-card border border-border shadow-sm"
                    style={{
                      left: `${layout.x}%`, top: `${layout.y}%`,
                      transform: `translate(${layout.calloutSide === "right" ? 36 : -100}px, -8px)`,
                    }}
                  >
                    <Loader2 className="w-3 h-3 animate-spin" style={{ color: config.color }} />
                    <span className="text-[9px] font-medium text-muted-foreground">Analyzing...</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Idle overlay */}
        {isIdle && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60 backdrop-blur-sm">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mx-auto mb-4">
                <Image src={AGENT_AVATARS.orchestrator} alt="Orchestrator" width={48} height={48} className="rounded-full" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">Waiting for order submission</p>
              <p className="text-xs text-muted-foreground/60 mt-1">Submit an order to activate agents</p>
            </div>
          </div>
        )}
      </div>

      {/* Bottom: Agent Comms Feed -- visible on round tabs, hidden on consensus tab */}
      {recentMsgs.length > 0 && selectedRound > 0 && (
        <div className="shrink-0 border-t border-border bg-card">
          <ScrollArea className="max-h-20">
            <div className="px-4 py-1.5 space-y-1">
              {recentMsgs.map((msg) => {
                const fromConfig = AGENT_CONFIGS.find(a => a.id === msg.from)
                const c = fromConfig?.color || "#6366f1"
                return (
                  <div key={msg.id} className="flex items-start gap-2 text-[10px]">
                    <div className="w-4 h-4 rounded-full overflow-hidden shrink-0 mt-0.5">
                      <Image
                        src={AGENT_AVATARS[msg.from as AgentId] || AGENT_AVATARS.orchestrator}
                        alt={String(msg.from)} width={16} height={16}
                        className="object-cover w-full h-full"
                      />
                    </div>
                    <div className="min-w-0">
                      <span className="font-bold" style={{ color: c }}>
                        {fromConfig?.name || "Orchestrator"}
                      </span>
                      <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full ml-1.5" style={{
                        backgroundColor: `${c}10`, color: c,
                      }}>
                        {msg.type.toUpperCase()}
                      </span>
                      <p className="text-muted-foreground truncate">{msg.message}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  )
}
