"""
╔══════════════════════════════════════════════════════════════════════════════╗
║       WALMART ENTERPRISE AGENT ORCHESTRATION ENGINE v2.0                    ║
║                                                                              ║
║  LangGraph-style execution graph with:                                       ║
║    • Typed shared state across all agent boundaries                          ║
║    • Event-driven A2A (Agent-to-Agent) messaging bus                        ║
║    • Parallel + sequential execution layers                                  ║
║    • Human-in-the-loop gate with SLA tracking                               ║
║    • Per-agent episodic + semantic memory                                    ║
║    • Full ReAct + CoT reasoning traces                                       ║
║    • Confidence-weighted decision fusion                                     ║
║    • Structured tool-use simulation                                          ║
║    • Kafka event publishing                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
#  TYPED STATE SCHEMA  (shared across all agents via the execution graph)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentMessage:
    """Typed inter-agent message — the A2A communication primitive."""
    msg_id:       str
    from_agent:   str
    to_agent:     str           # agent name, "BROADCAST", or "ORCHESTRATOR"
    msg_type:     str           # CONTEXT | ALERT | DATA_REQUEST | DATA_RESPONSE | DECISION
    payload:      Dict[str, Any]
    priority:     int = 5       # 1=critical  ↑↓  10=informational
    ttl_seconds:  int = 300
    requires_ack: bool = False
    timestamp:    str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acked:        bool = False


@dataclass
class TraceStep:
    """Single step in agent reasoning trace (CoT + ReAct)."""
    ts:          str
    agent:       str
    step_type:   str            # THOUGHT | ACTION | OBSERVATION | DECISION | FINAL
    content:     str
    tool_name:   Optional[str] = None
    tool_input:  Optional[Dict] = None
    tool_output: Optional[Any] = None
    duration_ms: Optional[int] = None


@dataclass
class HITLFlag:
    """Human-in-the-loop review request."""
    flag_id:     str
    agent:       str
    reason:      str
    severity:    str
    payload:     Dict[str, Any]
    sla_hours:   int
    created_ts:  str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved:    bool = False
    reviewer:    Optional[str] = None


@dataclass
class AgentState:
    """
    Central execution state — passed through the orchestration graph.
    Immutable-by-convention: agents return a new/mutated copy, never modify in-place.
    """
    run_id:           str
    trigger:          str                        # SCHEDULED | USER_QUERY | ALERT | KAFKA_EVENT
    trigger_payload:  Dict[str, Any]
    context:          Dict[str, Any]             # raw data from ingestion layer
    agent_outputs:    Dict[str, Any]             # keyed by agent name
    messages:         List[AgentMessage]         # A2A message queue
    trace:            List[TraceStep]            # full execution trace
    decisions:        List[Dict[str, Any]]       # finalized decisions
    alerts:           List[Dict[str, Any]]       # surfaced operational alerts
    hitl_queue:       List[HITLFlag]             # items requiring human review
    metadata:         Dict[str, Any]             # timing, tokens, costs, graph info
    status:           str = "RUNNING"            # RUNNING | COMPLETED | AWAITING_HITL | FAILED
    error:            Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT MEMORY  (episodic + semantic per agent)
# ─────────────────────────────────────────────────────────────────────────────

class AgentMemory:
    """
    Two-tier memory store:
    - Episodic:  recent decisions (ring-buffer, capacity-bounded)
    - Semantic:  keyword-indexed fact store (simplified vector search proxy)
    """
    def __init__(self, agent_name: str, episodic_capacity: int = 500):
        self.agent_name = agent_name
        self._episodic: deque = deque(maxlen=episodic_capacity)
        self._semantic: Dict[str, Dict] = {}
        self._lock = threading.RLock()

    def remember(self, content: str, tags: List[str] = None, importance: float = 0.5) -> None:
        entry = {
            "ts":         datetime.utcnow().isoformat(),
            "agent":      self.agent_name,
            "content":    content,
            "tags":       tags or [],
            "importance": importance,
        }
        with self._lock:
            self._episodic.append(entry)
            for tag in (tags or []):
                self._semantic[tag] = entry

    def recall_recent(self, n: int = 10) -> List[Dict]:
        with self._lock:
            return list(self._episodic)[-n:]

    def recall_by_tag(self, tag: str) -> Optional[Dict]:
        with self._lock:
            return self._semantic.get(tag)

    def working_set(self) -> List[Dict]:
        """Return top-10 most important recent memories."""
        with self._lock:
            items = list(self._episodic)
            return sorted(items, key=lambda x: x["importance"], reverse=True)[:10]


# ─────────────────────────────────────────────────────────────────────────────
#  TOOL REGISTRY  (simulated enterprise tool-use layer)
# ─────────────────────────────────────────────────────────────────────────────

class ToolResult:
    def __init__(self, tool: str, output: Any, duration_ms: int, cached: bool = False):
        self.tool = tool
        self.output = output
        self.duration_ms = duration_ms
        self.cached = cached


def _simulated_tool(name: str, inputs: Dict) -> ToolResult:
    """Proxy for real tool-use — simulates latency and returns structured outputs."""
    latency = random.randint(80, 1200)
    time.sleep(latency / 20_000)  # scaled-down for demo
    outputs = {
        "demand_forecast_api":   {"forecast_ready": True, "mape": round(random.uniform(4.2, 9.8), 2)},
        "inventory_scanner":     {"scan_complete": True, "records_processed": random.randint(5000, 180000)},
        "risk_scoring_engine":   {"model": "gradient_boost_v3", "features_used": 42},
        "route_optimizer":       {"routes_evaluated": random.randint(50, 800), "improvement_pct": round(random.uniform(3, 18), 1)},
        "price_elasticity_api":  {"model": "econometric_v2", "r_squared": round(random.uniform(0.72, 0.94), 3)},
        "rag_retriever":         {"docs_retrieved": random.randint(3, 8), "avg_relevance": round(random.uniform(0.75, 0.96), 3)},
        "vector_search":         {"index": "pinecone-walmart-ops", "results": random.randint(5, 20)},
        "graph_rag":             {"nodes_traversed": random.randint(12, 80), "paths_found": random.randint(3, 15)},
        "anomaly_detector":      {"anomalies_found": random.randint(0, 25), "model": "isolation_forest_v4"},
        "executive_synthesizer": {"kpis_computed": 24, "narrative_tokens": random.randint(800, 2400)},
    }
    return ToolResult(name, outputs.get(name, {"status": "ok"}), latency)


# ─────────────────────────────────────────────────────────────────────────────
#  BASE AGENT
# ─────────────────────────────────────────────────────────────────────────────

class EnterpriseAgent:
    """
    Abstract base for all Walmart AI agents.
    Provides: CoT reasoning, ReAct loop, A2A messaging, tool-use, memory.
    Concrete agents override `_execute()`.
    """

    def __init__(self, name: str, description: str,
                 tools: List[str], model: str = "claude-3-haiku-20240307"):
        self.name        = name
        self.description = description
        self.tools       = tools
        self.model       = model
        self.memory      = AgentMemory(name)
        # Stats
        self._total_calls   = 0
        self._total_tokens  = 0
        self._total_cost    = 0.0
        self._total_latency = 0
        self._errors        = 0

    # ── Tracing helpers ────────────────────────────────────────────────────

    def _think(self, state: AgentState, thought: str) -> TraceStep:
        step = TraceStep(
            ts=datetime.utcnow().isoformat(), agent=self.name,
            step_type="THOUGHT", content=thought,
        )
        state.trace.append(step)
        return step

    def _act(self, state: AgentState, tool: str, inputs: Dict) -> ToolResult:
        result = _simulated_tool(tool, inputs)
        step = TraceStep(
            ts=datetime.utcnow().isoformat(), agent=self.name,
            step_type="ACTION", content=f"Calling tool: {tool}",
            tool_name=tool, tool_input=inputs, tool_output=result.output,
            duration_ms=result.duration_ms,
        )
        state.trace.append(step)
        return result

    def _observe(self, state: AgentState, observation: str) -> TraceStep:
        step = TraceStep(
            ts=datetime.utcnow().isoformat(), agent=self.name,
            step_type="OBSERVATION", content=observation,
        )
        state.trace.append(step)
        return step

    def _decide(self, state: AgentState, decision: str,
                severity: str = "Medium", confidence: float = 0.88) -> TraceStep:
        step = TraceStep(
            ts=datetime.utcnow().isoformat(), agent=self.name,
            step_type="DECISION", content=decision,
        )
        state.trace.append(step)
        return step

    # ── A2A messaging ─────────────────────────────────────────────────────

    def _send(self, state: AgentState, to: str, msg_type: str,
              payload: Dict, priority: int = 5) -> AgentMessage:
        msg = AgentMessage(
            msg_id=str(uuid.uuid4())[:8].upper(),
            from_agent=self.name, to_agent=to,
            msg_type=msg_type, payload=payload, priority=priority,
        )
        state.messages.append(msg)
        return msg

    def _receive(self, state: AgentState, from_agent: str = None,
                 msg_type: str = None) -> List[AgentMessage]:
        return [
            m for m in state.messages
            if (not from_agent or m.from_agent == from_agent)
            and (not msg_type or m.msg_type == msg_type)
            and (m.to_agent == self.name or m.to_agent == "BROADCAST")
        ]

    # ── LLM call simulation ───────────────────────────────────────────────

    def _llm_call(self, prompt_tokens: int, output_tokens: int) -> Dict:
        cost_map = {
            "claude-3-haiku-20240307":     (0.00025, 0.00125),
            "claude-3-5-sonnet-20241022":  (0.003,   0.015),
        }
        in_rate, out_rate = cost_map.get(self.model, (0.001, 0.005))
        cost    = (prompt_tokens * in_rate + output_tokens * out_rate) / 1000
        latency = random.randint(150, 3500)
        time.sleep(latency / 15_000)
        self._total_calls   += 1
        self._total_tokens  += (prompt_tokens + output_tokens)
        self._total_cost    += cost
        self._total_latency += latency
        return {
            "model": self.model, "latency_ms": latency,
            "tokens_in": prompt_tokens, "tokens_out": output_tokens,
            "cost_usd": round(cost, 6),
        }

    # ── HITL gate ─────────────────────────────────────────────────────────

    def _flag_hitl(self, state: AgentState, reason: str,
                   severity: str, payload: Dict, sla_hours: int = 4) -> HITLFlag:
        flag = HITLFlag(
            flag_id=f"HITL-{uuid.uuid4().hex[:6].upper()}",
            agent=self.name, reason=reason,
            severity=severity, payload=payload, sla_hours=sla_hours,
        )
        state.hitl_queue.append(flag)
        return flag

    # ── Alert emission ────────────────────────────────────────────────────

    def _alert(self, state: AgentState, alert_type: str,
               severity: str, description: str, data: Dict = None) -> None:
        state.alerts.append({
            "alert_id":     f"ALT-{uuid.uuid4().hex[:8].upper()}",
            "ts":           datetime.utcnow().isoformat(),
            "source_agent": self.name,
            "alert_type":   alert_type,
            "severity":     severity,
            "description":  description,
            "data":         data or {},
        })

    # ── Main entrypoint ───────────────────────────────────────────────────

    def run(self, state: AgentState) -> AgentState:
        self._think(state, f"Initializing {self.name}. Trigger: {state.trigger}. Run: {state.run_id}")
        t0 = time.perf_counter()
        try:
            state = self._execute(state)
        except Exception as exc:
            self._errors += 1
            state.trace.append(TraceStep(
                ts=datetime.utcnow().isoformat(), agent=self.name,
                step_type="FINAL", content=f"ERROR: {exc}",
            ))
            state.agent_outputs[self.name] = {"status": "FAILED", "error": str(exc)}
            return state
        elapsed = round((time.perf_counter() - t0) * 1000)
        state.metadata.setdefault("agent_timing_ms", {})[self.name] = elapsed
        return state

    def _execute(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    @property
    def stats(self) -> Dict:
        return {
            "name":          self.name,
            "model":         self.model,
            "calls":         self._total_calls,
            "tokens":        self._total_tokens,
            "cost_usd":      round(self._total_cost, 6),
            "avg_latency_ms":int(self._total_latency / max(1, self._total_calls)),
            "errors":        self._errors,
            "memory_size":   len(self.memory._episodic),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT 1: DEMAND FORECASTING
# ─────────────────────────────────────────────────────────────────────────────

class DemandForecastAgent(EnterpriseAgent):
    """
    Operates over POS streams, demand signals, and seasonal models.
    Detects velocity anomalies, predicts demand events, drives upstream cascade.
    """
    def __init__(self):
        super().__init__(
            "DemandForecastAgent",
            "Predicts demand spikes, seasonal trends, and purchase-behavior anomalies.",
            ["demand_forecast_api", "anomaly_detector", "rag_retriever"],
        )

    def _execute(self, state: AgentState) -> AgentState:
        pos = state.context.get("pos")
        signals = state.context.get("demand_signals")

        # CoT
        self._think(state, "Reviewing POS transaction stream for velocity patterns and demand signals.")
        self._think(state, f"Input: {len(pos):,} txns, {len(signals):,} forward demand signals.")

        # Tool: demand forecasting model
        r1 = self._act(state, "demand_forecast_api", {"horizon": 14, "model": "ensemble"})
        self._observe(state, f"Forecast API → MAPE {r1.output['mape']:.1f}%. 14-day horizon computed.")

        # Tool: anomaly detection
        r2 = self._act(state, "anomaly_detector", {"stream": "pos", "window_hrs": 24})
        anomaly_count = r2.output["anomalies_found"]
        self._observe(state, f"Anomaly detector → {anomaly_count} anomalous transactions in 24h window.")

        # LLM synthesis
        llm = self._llm_call(2_100, 780)

        # Compute real insights from data
        findings = []
        anomalies = []

        if pos is not None and len(pos) > 0:
            by_dept = pos.groupby("department")["total_revenue"].sum().sort_values(ascending=False)
            top_dept = by_dept.index[0]
            top_rev  = float(by_dept.iloc[0])
            findings.append({
                "type": "TOP_REVENUE_DRIVER",
                "insight": f"{top_dept} is the #1 revenue department at ${top_rev:,.0f} over the period.",
                "confidence": 0.98,
                "recommended_action": "PRIORITIZE_REPLENISHMENT",
                "impact_usd": round(top_rev * 0.06, 2),
            })

            # Velocity analysis per category
            by_cat = pos.groupby("category")["qty"].sum().sort_values(ascending=False)
            for cat, qty in by_cat.head(5).items():
                findings.append({
                    "type": "VELOCITY_SIGNAL",
                    "category": cat,
                    "insight": f"{cat}: {qty:,} total units sold. Velocity class: HIGH.",
                    "confidence": round(random.uniform(0.82, 0.97), 3),
                    "recommended_action": "MONITOR_STOCK_LEVELS",
                    "impact_usd": round(random.uniform(10_000, 800_000), 2),
                })

            if "is_anomaly" in pos.columns:
                anom_rate = float(pos["is_anomaly"].mean() * 100)
                anom_ct   = int(pos["is_anomaly"].sum())
                anomalies.append({
                    "type": "SALES_ANOMALY",
                    "rate_pct": anom_rate,
                    "count": anom_ct,
                    "description": f"{anom_ct:,} anomalous transactions detected ({anom_rate:.2f}% rate).",
                    "severity": "High" if anom_rate > 2.5 else "Medium",
                })

        # Seasonal alerts from demand signals
        seasonal_alerts = []
        if signals is not None and len(signals) > 0:
            high_mult = signals[signals["demand_multiplier"] > 1.8]
            for dept in high_mult["department"].unique()[:4]:
                dept_rows = high_mult[high_mult["department"] == dept]
                max_mult  = float(dept_rows["demand_multiplier"].max())
                seasonal_alerts.append({
                    "department": dept,
                    "peak_multiplier": round(max_mult, 2),
                    "event": dept_rows["demand_event"].dropna().iloc[0] if dept_rows["demand_event"].dropna().any() else "Seasonal",
                    "recommended_stock_increase_pct": round((max_mult - 1) * 100, 0),
                })

        state.agent_outputs["DemandForecastAgent"] = {
            "status":          "COMPLETED",
            "findings":        findings,
            "anomalies":       anomalies,
            "seasonal_alerts": seasonal_alerts,
            "forecast_mape":   r1.output["mape"],
            "anomaly_count":   anomaly_count,
            "llm_metadata":    llm,
            "skus_analyzed":   int(pos["sku_id"].nunique()) if pos is not None and len(pos) > 0 else 0,
            "stores_analyzed": int(pos["store_id"].nunique()) if pos is not None and len(pos) > 0 else 0,
        }

        # A2A: broadcast to InventoryOptAgent and PricingPromoAgent
        self._send(state, "BROADCAST", "CONTEXT", {
            "demand_findings":   findings[:5],
            "anomaly_signals":   anomalies,
            "seasonal_alerts":   seasonal_alerts,
        }, priority=3)

        # Alert on critical anomalies
        for a in anomalies:
            if a["severity"] in ("Critical", "High"):
                self._alert(state, "DEMAND_ANOMALY", a["severity"], a["description"], a)

        self.memory.remember(
            f"Analyzed {len(findings)} demand signals. Anomaly rate: {anomalies[0]['rate_pct']:.2f}% if anomalies else 'N/A'.",
            tags=["demand", "anomaly"],
            importance=0.7,
        )
        self._think(state, f"DemandForecastAgent complete. {len(findings)} findings, {len(anomalies)} anomaly signals.")
        return state


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT 2: INVENTORY OPTIMIZATION
# ─────────────────────────────────────────────────────────────────────────────

class InventoryOptAgent(EnterpriseAgent):
    def __init__(self):
        super().__init__(
            "InventoryOptAgent",
            "Evaluates stock levels, predicts replenishment needs, identifies over/understock.",
            ["inventory_scanner", "rag_retriever"],
        )

    def _execute(self, state: AgentState) -> AgentState:
        inv  = state.context.get("inventory")
        msgs = self._receive(state, msg_type="CONTEXT")  # ingest from DemandForecastAgent

        self._think(state, f"Processing inventory snapshot: {len(inv):,} store-SKU records.")
        self._think(state, f"A2A context received from {len(msgs)} upstream agents.")

        r1 = self._act(state, "inventory_scanner", {"scope": "all_stores", "include_dc": True})
        self._observe(state, f"Inventory scan: {r1.output['records_processed']:,} records processed.")

        llm = self._llm_call(1_900, 720)

        summary = {}
        pos_list = []
        overstock = []
        stockout_risks = []

        if inv is not None and len(inv) > 0:
            status_cts = inv["status"].value_counts().to_dict()
            summary = {
                "total_records":    len(inv),
                "stores_covered":   int(inv["store_id"].nunique()),
                "skus_covered":     int(inv["sku_id"].nunique()),
                "stockout_count":   int(status_cts.get("Stockout", 0)),
                "critical_count":   int(status_cts.get("Critical", 0)),
                "below_rop_count":  int(status_cts.get("Below Reorder", 0)),
                "healthy_count":    int(status_cts.get("Healthy", 0)),
                "overstock_count":  int(status_cts.get("Overstock", 0) + status_cts.get("Excess", 0)),
                "total_inv_value":  float(inv["inventory_value"].sum()),
                "total_retail_val": float(inv["retail_value"].sum()),
                "avg_dos":          float(inv["days_of_supply"].mean()),
                "stockout_rate_pct":round(status_cts.get("Stockout", 0) / len(inv) * 100, 3),
                "fill_rate_avg":    float(inv["fill_rate_30d"].mean()),
            }

            # PO generation for critical items
            critical = inv[inv["status"].isin(["Stockout", "Critical"])].head(35)
            for _, row in critical.iterrows():
                po_qty = int(row["reorder_qty"])
                pos_list.append({
                    "po_id":       f"PO-{uuid.uuid4().hex[:8].upper()}",
                    "store_id":    row["store_id"],
                    "region":      row["region"],
                    "sku_id":      row["sku_id"],
                    "product_name":row["product_name"],
                    "department":  row["department"],
                    "vendor_id":   row["vendor_id"],
                    "vendor_name": row["vendor_name"],
                    "quantity":    po_qty,
                    "on_hand":     int(row["on_hand_units"]),
                    "days_of_supply":float(row["days_of_supply"]),
                    "unit_cost":   float(row["unit_cost"]),
                    "po_value":    round(po_qty * float(row["unit_cost"]), 2),
                    "lead_days":   int(row["lead_time_days"]),
                    "urgency":     "EMERGENCY" if row["status"] == "Stockout" else "URGENT",
                    "auto_approved":row["status"] == "Stockout",
                })

            # Overstock flags
            over = inv[inv["status"].isin(["Overstock", "Excess"])].head(20)
            for _, row in over.iterrows():
                excess = int(row["on_hand_units"] - row["reorder_point"] * 2.5)
                overstock.append({
                    "store_id":      row["store_id"],
                    "sku_id":        row["sku_id"],
                    "product_name":  row["product_name"],
                    "excess_units":  max(0, excess),
                    "excess_value":  round(max(0, excess) * float(row["unit_price"]), 2),
                    "is_perishable": bool(row["is_perishable"]),
                    "days_of_supply":float(row["days_of_supply"]),
                    "action":        "EXPEDITED_MARKDOWN" if row["is_perishable"] else random.choice([
                        "INTER_STORE_TRANSFER", "MARKDOWN_10PCT", "RETURN_TO_VENDOR", "CROSS_DOCK",
                    ]),
                })

        state.agent_outputs["InventoryOptAgent"] = {
            "status":               "COMPLETED",
            "summary":              summary,
            "replenishment_orders": pos_list,
            "overstock_flags":      overstock,
            "stockout_risks":       stockout_risks,
            "llm_metadata":         llm,
        }

        # A2A → LogisticsCoordAgent (route the POs)
        if pos_list:
            self._send(state, "LogisticsCoordAgent", "DATA_REQUEST", {
                "type": "ROUTE_REPLENISHMENT",
                "po_count": len(pos_list),
                "po_sample": pos_list[:5],
            }, priority=2)

        # A2A → ExecutiveInsightAgent (critical inventory risk)
        if summary.get("stockout_count", 0) > 10:
            self._send(state, "ExecutiveInsightAgent", "ALERT", {
                "type": "MASS_STOCKOUT_RISK",
                "count": summary["stockout_count"],
                "financial_exposure": round(summary.get("total_retail_val", 0) * 0.15, 2),
            }, priority=1)
            self._alert(state, "MASS_STOCKOUT", "Critical",
                        f"{summary['stockout_count']} stockout SKUs across {summary['stores_covered']} stores",
                        summary)

        # HITL for large PO batches
        if len(pos_list) > 20:
            self._flag_hitl(state, "Large replenishment batch requires supply-chain lead approval",
                            "High", {"po_count": len(pos_list), "total_po_value": sum(p["po_value"] for p in pos_list)},
                            sla_hours=4)

        self.memory.remember(f"Generated {len(pos_list)} POs. Overstock: {len(overstock)}.",
                             tags=["inventory", "replenishment"], importance=0.8)
        return state


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT 3: VENDOR RISK
# ─────────────────────────────────────────────────────────────────────────────

class VendorRiskAgent(EnterpriseAgent):
    def __init__(self):
        super().__init__(
            "VendorRiskAgent",
            "Analyzes vendor delivery performance, flags supply disruptions, recommends alternates.",
            ["risk_scoring_engine", "rag_retriever", "graph_rag"],
        )

    def _execute(self, state: AgentState) -> AgentState:
        events  = state.context.get("vendor_events")
        vendors = state.context.get("vendors")

        self._think(state, f"Loading {len(events):,} vendor events across {len(vendors)} active suppliers.")

        r1 = self._act(state, "risk_scoring_engine", {"vendors": len(vendors), "window_days": 90})
        r2 = self._act(state, "graph_rag", {"query": "vendor SLA breach protocol", "hops": 3})
        self._observe(state, f"Risk engine: {r1.output['features_used']} features. Graph RAG: {r2.output['nodes_traversed']} nodes traversed.")

        llm = self._llm_call(2_200, 850)

        risk_scores = []
        high_risk   = []
        alt_recs    = []

        if vendors is not None and events is not None and len(events) > 0:
            for _, v in vendors.iterrows():
                v_events  = events[events["vendor_id"] == v["id"]]
                delays    = v_events[v_events["event_type"] == "SHIPMENT_DELAYED"]
                quality   = v_events[v_events["event_type"] == "QUALITY_REJECTION"]
                force_maj = v_events[v_events["event_type"] == "FORCE_MAJEURE"]

                base_risk    = int((1 - float(v["otd_pct"])) * 100)
                delay_risk   = min(35, len(delays) * 3)
                quality_risk = min(25, len(quality) * 8)
                fm_risk      = min(20, len(force_maj) * 20)
                total_risk   = min(100, max(0, base_risk + delay_risk + quality_risk + fm_risk + random.randint(-5, 8)))

                rec = {
                    "vendor_id":        v["id"],
                    "vendor_name":      v["name"],
                    "tier":             int(v["tier"]),
                    "risk_score":       total_risk,
                    "risk_level":       "Critical" if total_risk > 75 else "High" if total_risk > 50 else "Medium" if total_risk > 25 else "Low",
                    "otd_pct":          round(float(v["otd_pct"]) * 100, 2),
                    "delay_events_90d": len(delays),
                    "quality_events":   len(quality),
                    "force_majeure":    len(force_maj),
                    "avg_lead_days":    int(v["lead_days"]),
                    "contract_value_m": float(v["contract_value_m"]),
                    "country":          v["country"],
                    "integration":      v["integration"],
                    "recommended_action": self._risk_action(total_risk),
                    "alt_vendor_identified": total_risk > 50,
                }
                risk_scores.append(rec)

                if total_risk > 50:
                    high_risk.append(rec)
                    alt_vend = vendors[vendors["id"] != v["id"]].sample(1).iloc[0]
                    alt_recs.append({
                        "primary_vendor":   v["name"],
                        "primary_risk":     total_risk,
                        "alt_vendor":       alt_vend["name"],
                        "alt_lead_days":    int(alt_vend["lead_days"]),
                        "lead_delta_days":  int(alt_vend["lead_days"]) - int(v["lead_days"]),
                        "cost_delta_pct":   round(random.uniform(-8, 15), 1),
                        "approval_required": total_risk > 75,
                    })

        state.agent_outputs["VendorRiskAgent"] = {
            "status":         "COMPLETED",
            "risk_scores":    risk_scores,
            "high_risk":      high_risk,
            "alt_vendor_recs":alt_recs,
            "total_vendors":  len(risk_scores),
            "high_risk_count":len(high_risk),
            "llm_metadata":   llm,
        }

        # A2A alerts
        for rec in high_risk[:3]:
            self._alert(state, "VENDOR_RISK_ELEVATED", rec["risk_level"],
                        f"{rec['vendor_name']} risk score {rec['risk_score']}/100 — {rec['recommended_action']}", rec)

        if any(r["risk_score"] > 75 for r in risk_scores):
            self._send(state, "ExecutiveInsightAgent", "ALERT", {
                "type": "CRITICAL_VENDOR_RISK",
                "critical_vendors": [r["vendor_name"] for r in high_risk if r["risk_score"] > 75],
            }, priority=1)
            self._flag_hitl(state, "Critical vendor risk — VP Procurement approval needed",
                            "Critical", {"high_risk_vendors": [r["vendor_name"] for r in high_risk]},
                            sla_hours=2)

        self.memory.remember(f"Scored {len(risk_scores)} vendors. High-risk: {len(high_risk)}.",
                             tags=["vendor", "risk"], importance=0.9)
        return state

    def _risk_action(self, score: int) -> str:
        if score > 75: return "IMMEDIATE_ESCALATION + ACTIVATE_CONTINGENCY_PLAN"
        if score > 50: return "PROCUREMENT_REVIEW + DAILY_MONITORING"
        if score > 25: return "WATCHLIST + BI-WEEKLY_REVIEW"
        return "STANDARD_SLA_MONITORING"


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT 4: LOGISTICS COORDINATION
# ─────────────────────────────────────────────────────────────────────────────

class LogisticsCoordAgent(EnterpriseAgent):
    def __init__(self):
        super().__init__(
            "LogisticsCoordAgent",
            "Optimizes DC routing, monitors warehouse throughput, predicts fulfillment SLA risk.",
            ["route_optimizer", "inventory_scanner"],
        )

    def _execute(self, state: AgentState) -> AgentState:
        telemetry = state.context.get("telemetry")
        inv_msgs  = self._receive(state, from_agent="InventoryOptAgent", msg_type="DATA_REQUEST")

        self._think(state, f"Loading {len(telemetry):,} DC telemetry records across all distribution centers.")
        self._think(state, f"Received {len(inv_msgs)} replenishment routing requests from InventoryOptAgent.")

        r1 = self._act(state, "route_optimizer", {"stores": 4200, "dcs": 24, "algorithm": "vrp_milp"})
        self._observe(state, f"Route optimizer: evaluated {r1.output['routes_evaluated']} routes, "
                              f"{r1.output['improvement_pct']:.1f}% improvement vs baseline.")

        llm = self._llm_call(1_700, 680)

        dc_health  = []
        bottlenecks = []
        route_opts  = []

        if telemetry is not None and len(telemetry) > 0:
            by_dc = telemetry.groupby("dc_id").agg({
                "throughput_units_hr":  "mean",
                "dock_utilization_pct": "mean",
                "picker_efficiency_pct":"mean",
                "mhe_fault_count":      "sum",
                "orders_pending":       "mean",
                "orders_completed_hr":  "mean",
                "alert_flag":           "sum",
                "safety_incidents":     "sum",
                "power_draw_kw":        "mean",
            }).reset_index()

            for _, dc in by_dc.iterrows():
                util   = float(dc["dock_utilization_pct"])
                pick   = float(dc["picker_efficiency_pct"])
                faults = int(dc["mhe_fault_count"])
                health = int(
                    max(0, 100
                        - max(0, util - 80) * 1.5
                        - faults * 2
                        + (pick - 85) * 0.5
                    )
                )
                dc_health.append({
                    "dc_id":               dc["dc_id"],
                    "dock_utilization_pct":round(util, 2),
                    "throughput_units_hr": int(dc["throughput_units_hr"]),
                    "picker_efficiency_pct":round(pick, 2),
                    "mhe_faults":          faults,
                    "orders_pending":      int(dc["orders_pending"]),
                    "orders_per_hr":       int(dc["orders_completed_hr"]),
                    "health_score":        health,
                    "status":              "CRITICAL" if util > 95 else "STRESSED" if util > 88 else "HEALTHY",
                    "alert_count":         int(dc["alert_flag"]),
                    "safety_incidents":    int(dc["safety_incidents"]),
                    "power_draw_kw":       int(dc["power_draw_kw"]),
                })
                if util > 88:
                    bottlenecks.append({
                        "dc_id":        dc["dc_id"],
                        "utilization":  round(util, 2),
                        "severity":     "Critical" if util > 95 else "High",
                        "recommended":  "AUTHORIZE_OVERTIME + REDIRECT_20PCT_VOLUME" if util > 95 else "SCHEDULE_OVERTIME",
                        "est_recovery_hrs": random.randint(4, 24),
                    })

            # Route optimizations for PO fulfillment
            po_msgs = [m.payload.get("po_sample", []) for m in inv_msgs]
            for po_batch in po_msgs:
                for po in po_batch:
                    route_opts.append({
                        "po_id":           po.get("po_id"),
                        "store_id":        po.get("store_id"),
                        "optimized_via":   f"DC-{random.choice(['SE','NE','MW'])}-{random.randint(1,4):02d}",
                        "est_transit_hrs": random.randint(6, 48),
                        "carrier":         random.choice(["Walmart Fleet","J.B. Hunt","XPO Logistics"]),
                        "fuel_saved_pct":  round(r1.output["improvement_pct"] * random.uniform(0.7, 1.3), 1),
                        "co2_kg_saved":    round(random.uniform(8, 120), 1),
                    })

        state.agent_outputs["LogisticsCoordAgent"] = {
            "status":       "COMPLETED",
            "dc_health":    dc_health,
            "bottlenecks":  bottlenecks,
            "route_opts":   route_opts,
            "network_util": round(sum(d["dock_utilization_pct"] for d in dc_health) / max(1, len(dc_health)), 2),
            "llm_metadata": llm,
        }

        for b in bottlenecks:
            self._alert(state, "DC_CAPACITY_BOTTLENECK", b["severity"],
                        f"DC {b['dc_id']} at {b['utilization']:.1f}% — {b['recommended']}", b)

        self.memory.remember(f"DC health: {len(dc_health)} centers. Bottlenecks: {len(bottlenecks)}.",
                             tags=["logistics", "dc"], importance=0.75)
        return state


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT 5: PRICING & PROMOTION
# ─────────────────────────────────────────────────────────────────────────────

class PricingPromoAgent(EnterpriseAgent):
    def __init__(self):
        super().__init__(
            "PricingPromoAgent",
            "Evaluates competitive pricing gaps, predicts campaign ROI, optimizes markdown timing.",
            ["price_elasticity_api", "rag_retriever"],
        )

    def _execute(self, state: AgentState) -> AgentState:
        pricing  = state.context.get("pricing")
        inv_out  = state.agent_outputs.get("InventoryOptAgent", {})
        dem_msgs = self._receive(state, msg_type="CONTEXT")

        self._think(state, f"Loading {len(pricing):,} SKU pricing records. Checking for competitive gaps.")

        r1 = self._act(state, "price_elasticity_api", {"method": "econometric", "sample": min(500, len(pricing))})
        self._observe(state, f"Elasticity model: R² = {r1.output['r_squared']:.3f}. Ready for optimization.")

        llm = self._llm_call(1_600, 640)

        price_gaps = []
        promo_analysis = []
        markdown_recs = []
        architecture_violations = []

        if pricing is not None and len(pricing) > 0:
            gap_items = pricing[abs(pricing["price_gap_pct"]) > 4].sort_values(
                "price_gap_pct", key=abs, ascending=False
            )
            for _, row in gap_items.head(20).iterrows():
                rev_impact = abs(float(row["price_gap_pct"])) / 100 * float(row.get("projected_unit_lift_pct", 10)) * 1000
                price_gaps.append({
                    "sku_id":          row["sku_id"],
                    "product_name":    row["product_name"],
                    "department":      row["department"],
                    "current_price":   float(row["current_price"]),
                    "competitor_price":float(row["competitor_a_price"]),
                    "gap_pct":         float(row["price_gap_pct"]),
                    "elasticity":      float(row["price_elasticity"]),
                    "action":          row["recommended_action"],
                    "ai_confidence":   float(row["ai_confidence"]),
                    "revenue_impact_wk":round(rev_impact, 2),
                    "margin_pct":      float(row["margin_pct"]),
                })

            active_promos = pricing[pricing["promo_active"] == True]
            for _, row in active_promos.head(15).iterrows():
                lift = abs(float(row["price_elasticity"])) * float(row["promo_discount_pct"]) / 100
                promo_analysis.append({
                    "sku_id":        row["sku_id"],
                    "product_name":  row["product_name"],
                    "department":    row["department"],
                    "promo_type":    row["promo_type"],
                    "discount_pct":  float(row["promo_discount_pct"]),
                    "est_unit_lift": round(lift * 100, 1),
                    "margin_impact": float(row["projected_margin_delta"]),
                    "recommendation":random.choice(["EXTEND_2WK", "END_AS_PLANNED", "DEEPEN_5PCT"]),
                })

            # Markdowns from overstock
            overstock = inv_out.get("overstock_flags", [])
            for item in overstock[:15]:
                excess_val = item.get("excess_value", 0)
                md_pct = 25 if item.get("is_perishable") else random.choice([10, 15, 20])
                markdown_recs.append({
                    "sku_id":            item.get("sku_id"),
                    "product_name":      item.get("product_name"),
                    "excess_units":      item.get("excess_units", 0),
                    "excess_value":      excess_val,
                    "markdown_pct":      md_pct,
                    "recovery_pct":      100 - md_pct,
                    "recovery_value":    round(excess_val * (1 - md_pct / 100), 2),
                    "clearance_days":    random.randint(7, 45),
                    "is_perishable":     item.get("is_perishable", False),
                    "recommended_channel":random.choice(["In-Store Endcap","Online Clearance","Sam's Club Redirect"]),
                })

            # Price architecture violations
            below_cost = pricing[pricing["current_price"] < pricing["current_price"] * (1 - pricing["margin_pct"] * 2)]
            if len(below_cost) > 0:
                for _, row in below_cost.head(3).iterrows():
                    architecture_violations.append({
                        "sku_id": row["sku_id"],
                        "product_name": row["product_name"],
                        "current_price": float(row["current_price"]),
                        "severity": "Critical",
                        "required_action": "PRICING_EXCEPTION_APPROVAL",
                    })

        state.agent_outputs["PricingPromoAgent"] = {
            "status":                  "COMPLETED",
            "price_gaps":              price_gaps,
            "promo_analysis":          promo_analysis,
            "markdown_recs":           markdown_recs,
            "architecture_violations": architecture_violations,
            "llm_metadata":            llm,
        }

        for v in architecture_violations:
            self._alert(state, "PRICE_ARCHITECTURE_VIOLATION", "Critical",
                        f"SKU {v['sku_id']} selling below cost — SVP approval required.", v)
            self._flag_hitl(state, "Price below cost requires SVP Merchandising approval.",
                            "Critical", v, sla_hours=2)

        self.memory.remember(f"Pricing: {len(price_gaps)} gaps, {len(markdown_recs)} markdown recs.",
                             tags=["pricing", "promo"], importance=0.7)
        return state


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT 6: EXECUTIVE INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────

class ExecutiveInsightAgent(EnterpriseAgent):
    def __init__(self):
        super().__init__(
            "ExecutiveInsightAgent",
            "Synthesizes all downstream outputs into executive operational intelligence.",
            ["executive_synthesizer", "rag_retriever"],
            model="claude-3-5-sonnet-20241022",
        )

    def _execute(self, state: AgentState) -> AgentState:
        # Ingest all upstream agent outputs
        demand  = state.agent_outputs.get("DemandForecastAgent",   {})
        inv     = state.agent_outputs.get("InventoryOptAgent",      {})
        vendor  = state.agent_outputs.get("VendorRiskAgent",        {})
        log     = state.agent_outputs.get("LogisticsCoordAgent",    {})
        pricing = state.agent_outputs.get("PricingPromoAgent",      {})

        self._think(state, "Synthesizing outputs from 5 domain agents into executive intelligence package.")
        self._think(state, f"Active alerts: {len(state.alerts)}. HITL queue: {len(state.hitl_queue)}.")

        r1 = self._act(state, "executive_synthesizer", {"agents": 5, "depth": "deep"})
        self._observe(state, f"Synthesizer: {r1.output['kpis_computed']} KPIs computed, {r1.output['narrative_tokens']} narrative tokens.")

        llm = self._llm_call(4_500, 1_800)   # Sonnet — higher token budget

        # Aggregate KPIs
        pos = state.context.get("pos")
        inv_sum = inv.get("summary", {})
        total_rev = float(pos["total_revenue"].sum()) if pos is not None and len(pos) > 0 else 0
        total_pos = len(pos) if pos is not None else 0
        po_value  = sum(p.get("po_value", 0) for p in inv.get("replenishment_orders", []))

        kpis = {
            "revenue_period_usd":    round(total_rev, 2),
            "total_transactions":    total_pos,
            "avg_basket_usd":        round(total_rev / max(1, total_pos), 2),
            "inventory_value_usd":   round(inv_sum.get("total_inv_value", 0), 2),
            "retail_value_usd":      round(inv_sum.get("total_retail_val", 0), 2),
            "stockout_rate_pct":     round(inv_sum.get("stockout_rate_pct", 0), 3),
            "fill_rate_pct":         round(inv_sum.get("fill_rate_avg", 0) * 100, 2),
            "vendor_health_score":   round(100 - vendor.get("high_risk_count", 0) / max(1, vendor.get("total_vendors", 1)) * 100, 1),
            "dc_avg_utilization_pct":log.get("network_util", 0),
            "replenishment_pos":     len(inv.get("replenishment_orders", [])),
            "po_value_usd":          round(po_value, 2),
            "active_alerts":         len(state.alerts),
            "hitl_pending":          len(state.hitl_queue),
            "price_gap_opps":        len(pricing.get("price_gaps", [])),
        }

        # Strategic risk assessment
        strategic_risks = []
        if inv_sum.get("stockout_count", 0) > 15:
            strategic_risks.append({
                "risk_id":   "SR-001",
                "category":  "INVENTORY",
                "title":     "Mass Stockout Event Risk",
                "severity":  "Critical",
                "impact":    f"${round(total_rev * 0.02 / 90, 0):,.0f}/day revenue leakage",
                "driver":    f"{inv_sum['stockout_count']} stockout SKUs",
                "action":    "Emergency replenishment cascade activated",
            })
        if vendor.get("high_risk_count", 0) > 4:
            strategic_risks.append({
                "risk_id":   "SR-002",
                "category":  "SUPPLY_CHAIN",
                "title":     "Multi-Vendor Disruption Cluster",
                "severity":  "High",
                "impact":    f"{vendor['high_risk_count']} tier-1/2 vendors at risk of supply disruption",
                "driver":    "Correlated delivery delays and capacity constraints",
                "action":    "Activate contingency sourcing — board-level awareness recommended",
            })
        if log.get("network_util", 0) > 88:
            strategic_risks.append({
                "risk_id":   "SR-003",
                "category":  "LOGISTICS",
                "title":     "DC Network Capacity Saturation",
                "severity":  "High",
                "impact":    "Fulfillment SLA breach risk within 48h",
                "driver":    f"Network avg utilization {log['network_util']:.1f}%",
                "action":    "Authorize overtime + volume redistribution across DCs",
            })

        # Executive narrative
        now_str = datetime.now().strftime("%B %d, %Y %H:%M CST")
        narrative = f"""
WALMART SUPPLY CHAIN INTELLIGENCE — {now_str}

REVENUE: ${total_rev:,.0f} ({total_pos:,} transactions) over the analysis period.
Avg basket: ${kpis['avg_basket_usd']:.2f} | Fill rate: {kpis['fill_rate_pct']:.1f}%

INVENTORY: {inv_sum.get('stockout_count',0)} active stockouts across {inv_sum.get('stores_covered',0)} stores.
{len(inv.get('replenishment_orders',[]))} emergency POs auto-generated (${po_value:,.0f} total value).
Overstock exposure: ${inv_sum.get('total_inv_value',0) * 0.12:,.0f} (est. 12% overstock premium).

VENDOR ECOSYSTEM: {vendor.get('total_vendors',0)} active suppliers scored.
{vendor.get('high_risk_count',0)} vendors in High/Critical tier — procurement escalation initiated.

LOGISTICS: Network avg utilization {log.get('network_util',0):.1f}%.
{len(log.get('bottlenecks',[]))} distribution centers in stressed/critical state.

PRICING: {len(pricing.get('price_gaps',[]))} competitive price gap opportunities identified.
{len(pricing.get('markdown_recs',[]))} markdown recommendations to recover overstock value.

RISK SUMMARY: {len(strategic_risks)} strategic risks. {len(state.alerts)} operational alerts. {len(state.hitl_queue)} HITL items pending.
        """.strip()

        state.agent_outputs["ExecutiveInsightAgent"] = {
            "status":           "COMPLETED",
            "kpis":             kpis,
            "strategic_risks":  strategic_risks,
            "narrative":        narrative,
            "llm_metadata":     llm,
            "decisions_made":   len(state.decisions),
            "alerts_surfaced":  len(state.alerts),
        }

        # Final decisions
        state.decisions.extend([
            {"decision": "Activate emergency replenishment for all Stockout SKUs", "priority": 1, "status": "AUTO_APPROVED", "agent": self.name},
            {"decision": f"Escalate {vendor.get('high_risk_count',0)} high-risk vendors to VP Procurement", "priority": 2, "status": "PENDING_HITL", "agent": self.name},
            {"decision": "Authorize DC overtime for utilization >88%", "priority": 2, "status": "AUTO_APPROVED", "agent": self.name},
            {"decision": "Initiate competitive price matching for flagged SKUs", "priority": 3, "status": "PENDING_HITL", "agent": self.name},
            {"decision": f"Clear {len(pricing.get('markdown_recs',[]))} overstock SKUs via markdown cascade", "priority": 3, "status": "AUTO_APPROVED", "agent": self.name},
        ])

        # Change status if HITL items exist
        if state.hitl_queue:
            state.status = "AWAITING_HITL"
        else:
            state.status = "COMPLETED"

        self.memory.remember(f"Executive synthesis: {len(strategic_risks)} risks, {len(state.alerts)} alerts.",
                             tags=["executive", "synthesis"], importance=1.0)
        return state


# ─────────────────────────────────────────────────────────────────────────────
#  AGENT 7: CONVERSATIONAL AI  (RAG-grounded)
# ─────────────────────────────────────────────────────────────────────────────

class ConversationalAgent(EnterpriseAgent):
    """
    Enterprise conversational AI interface.
    RAG-grounded using simulated Pinecone + Neo4j Graph retrieval.
    Supports multi-turn context with episodic memory.
    """

    KNOWLEDGE_BASE: Dict[str, Dict] = {
        "vendor_sop": {
            "title": "Vendor Management SOP v4.3 (WMT-VMS-004)",
            "content": "Tier-1 vendors must maintain ≥97% on-time delivery (OTD). Breaches: 1st offense = formal notice; 2nd = financial penalty (0.5% contract value); 3rd = contract review by VP Procurement. Risk scores >75 trigger automatic escalation to C-suite.",
            "tags": ["vendor", "sla", "otd", "risk", "contract"],
        },
        "replenishment_policy": {
            "title": "Replenishment Policy WMT-INV-003 v2.1",
            "content": "Safety stock = 1.5× lead-time demand (μ×LT) + 1.5σ_LT. Reorder point = μ_daily × lead_days + safety_stock. Max stock = reorder_point + reorder_qty. Exception: perishable items use 30% lower safety stock with 2× reorder frequency.",
            "tags": ["inventory", "replenishment", "safety_stock", "reorder"],
        },
        "stockout_protocol": {
            "title": "Stockout Response Protocol WMT-OPS-017 v3.0",
            "content": "Zero on-hand triggers: (1) Auto-PO within 4 hours; (2) Regional manager notification; (3) Substitution scan for adjacent SKUs; (4) DC emergency pick if 48h SLA breached. Revenue leakage reporting mandatory for stockouts >24h.",
            "tags": ["stockout", "emergency", "protocol", "replenishment"],
        },
        "markdown_policy": {
            "title": "Markdown Authorization Policy WMT-PRICE-009",
            "content": "Days 1-30 overstock: store discretion up to 10%. Days 31-60: automated 15% markdown. Days 61-90: 25% + inter-store transfer. Day 90+: 35% + liquidation channel. Perishable items follow 3-day markdown cascade: 15% → 25% → 40%.",
            "tags": ["markdown", "overstock", "clearance", "pricing"],
        },
        "dc_operations": {
            "title": "DC Operations Manual WMT-DC-001 v5.2",
            "content": "Target dock utilization: ≤82% (normal ops). 83-90%: alert + 4hr operational review. 91-95%: overtime authorization automatic. >95%: emergency reroute protocol + VP Operations notification. MHE faults >10/shift trigger maintenance escalation.",
            "tags": ["dc", "warehouse", "utilization", "operations", "logistics"],
        },
        "vendor_risk_framework": {
            "title": "Vendor Risk Assessment Framework WMT-VRF-2024",
            "content": "Risk score 0-25: Low (standard monitoring). 26-50: Medium (weekly review). 51-75: High (daily monitoring + procurement review). 76-100: Critical (C-suite notification, contingency sourcing activation, contract review). Scores updated weekly using 42-feature ML model.",
            "tags": ["vendor", "risk", "scoring", "procurement"],
        },
        "demand_forecasting_sop": {
            "title": "AI Demand Forecasting SOP WMT-AI-007 v2.4",
            "content": "Ensemble model: XGBoost v4 (40% weight) + LightGBM v3 (30%) + Prophet v2 (20%) + DeepAR (10%). Retrained weekly using 52-week rolling window. MAPE target: <6% Tier-A, <9% Tier-B, <12% Tier-C SKUs. Seasonal override manual triggers available for store managers.",
            "tags": ["demand", "forecast", "model", "ai", "accuracy"],
        },
        "incident_response": {
            "title": "Supply Chain Incident Response Playbook v3.1",
            "content": "P1 (Critical): Revenue impact >$1M/day — CEO + Board notified within 2hrs. P2 (High): >$100K/day — SVP Supply Chain + CFO within 4hrs. P3 (Medium): >$10K/day — VP Operations within 8hrs. All incidents require post-mortem within 5 business days.",
            "tags": ["incident", "escalation", "response", "emergency"],
        },
    }

    INTENT_KEYWORDS = {
        "inventory": ["stock", "inventory", "on-hand", "onhand", "stockout", "shortage", "rop", "reorder", "replenish", "overstock", "excess"],
        "vendor":    ["vendor", "supplier", "delivery", "shipment", "late", "delay", "sla", "otd", "on-time", "risk", "contract"],
        "demand":    ["demand", "forecast", "predict", "sales", "velocity", "surge", "trend", "anomaly", "seasonal", "mape"],
        "logistics": ["warehouse", "dc", "distribution", "route", "fulfillment", "throughput", "bottleneck", "carrier", "transit"],
        "pricing":   ["price", "promo", "promotion", "markdown", "clearance", "competitor", "margin", "elasticity", "discount"],
        "executive": ["summary", "kpi", "health", "performance", "overview", "status", "board", "executive", "risk"],
        "incident":  ["incident", "emergency", "crisis", "escalate", "critical", "alert", "p1", "p2"],
    }

    def __init__(self):
        super().__init__(
            "ConversationalAgent",
            "Enterprise RAG conversational AI, grounded on operational data and internal SOPs.",
            ["rag_retriever", "vector_search", "graph_rag"],
            model="claude-3-5-sonnet-20241022",
        )
        self._conversation_history: List[Dict] = []

    def chat(self, query: str, state: AgentState) -> Dict:
        """Main conversational entry point."""
        self._conversation_history.append({"role": "user", "content": query, "ts": datetime.utcnow().isoformat()})

        # ReAct loop
        trace = self._react(query, state)

        # RAG retrieval
        rag_docs  = self._retrieve(query)
        intent    = self._classify_intent(query)

        # Generate grounded response
        response  = self._respond(query, intent, state, rag_docs)
        llm_meta  = self._llm_call(3_200, 1_100)

        result = {
            "response":         response["text"],
            "citations":        response["citations"],
            "intent":           intent,
            "react_trace":      trace,
            "rag_docs":         rag_docs,
            "confidence":       round(random.uniform(0.88, 0.99), 4),
            "llm_metadata":     llm_meta,
            "ts":               datetime.utcnow().isoformat(),
            "turn":             len(self._conversation_history),
        }
        self._conversation_history.append({"role": "assistant", "content": response["text"], "ts": datetime.utcnow().isoformat()})
        self.memory.remember(f"Q: {query[:60]} | Intent: {intent}", tags=[intent], importance=0.6)
        return result

    def _classify_intent(self, query: str) -> str:
        q = query.lower()
        best, score = "general", 0
        for intent, keywords in self.INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in q)
            if hits > score:
                best, score = intent, hits
        return best

    def _retrieve(self, query: str) -> List[Dict]:
        q = query.lower()
        scored = []
        for key, doc in self.KNOWLEDGE_BASE.items():
            score = sum(1 for tag in doc["tags"] if tag in q)
            score += sum(0.5 for word in q.split() if len(word) > 4 and word in doc["content"].lower())
            if score > 0:
                scored.append({
                    "doc_id":    key,
                    "title":     doc["title"],
                    "excerpt":   doc["content"][:220] + "…",
                    "relevance": min(1.0, round(score / 5 + random.uniform(0, 0.2), 3)),
                    "source":    f"Walmart Internal KB — {doc['title'][:40]}",
                })
        return sorted(scored, key=lambda x: x["relevance"], reverse=True)[:3]

    def _react(self, query: str, state: AgentState) -> List[Dict]:
        intent = self._classify_intent(query)
        return [
            {"step": "THOUGHT",     "content": f"User intent: '{intent}'. Initiating multi-source retrieval."},
            {"step": "ACTION",      "content": f"vector_search(query='{query[:50]}', index='pinecone-walmart-ops', top_k=5)"},
            {"step": "OBSERVATION", "content": "Retrieved 5 semantically relevant document chunks from Pinecone index."},
            {"step": "ACTION",      "content": f"graph_rag(query='{intent}', hops=2, entity_types=['policy','metric','vendor'])"},
            {"step": "OBSERVATION", "content": "Graph traversal: 24 nodes, 37 edges. 3 policy documents matched."},
            {"step": "ACTION",      "content": "Grounding response against agent pipeline state (live operational data)."},
            {"step": "OBSERVATION", "content": f"Pipeline state loaded: {len(state.agent_outputs)} agent outputs available."},
            {"step": "FINAL",       "content": "Synthesizing grounded, citation-backed response."},
        ]

    def _respond(self, query: str, intent: str, state: AgentState, docs: List[Dict]) -> Dict:
        inv_out   = state.agent_outputs.get("InventoryOptAgent",   {})
        vendor_out= state.agent_outputs.get("VendorRiskAgent",     {})
        exec_out  = state.agent_outputs.get("ExecutiveInsightAgent",{})
        log_out   = state.agent_outputs.get("LogisticsCoordAgent", {})
        pricing_out=state.agent_outputs.get("PricingPromoAgent",   {})
        dem_out   = state.agent_outputs.get("DemandForecastAgent",  {})
        kpis      = exec_out.get("kpis", {})
        inv_sum   = inv_out.get("summary", {})
        citations = [d["source"] for d in docs[:2]]

        RESPONSES = {
            "inventory": (
                f"**Inventory Intelligence — Live Snapshot**\n\n"
                f"Across **{inv_sum.get('stores_covered', 'N/A')} stores** and **{inv_sum.get('skus_covered', 'N/A')} SKUs**:\n\n"
                f"| Status | Count |\n|--------|-------|\n"
                f"| 🔴 Stockout | {inv_sum.get('stockout_count', 0):,} |\n"
                f"| 🟠 Critical | {inv_sum.get('critical_count', 0):,} |\n"
                f"| 🟡 Below ROP | {inv_sum.get('below_rop_count', 0):,} |\n"
                f"| 🟢 Healthy | {inv_sum.get('healthy_count', 0):,} |\n"
                f"| 🔵 Overstock | {inv_sum.get('overstock_count', 0):,} |\n\n"
                f"**Total Inventory Value:** ${inv_sum.get('total_inv_value', 0):,.0f}\n"
                f"**Avg Days of Supply:** {inv_sum.get('avg_dos', 0):.1f} days\n"
                f"**Auto-POs Generated:** {len(inv_out.get('replenishment_orders', [])):,} orders\n\n"
                f"Per *{docs[0]['title'] if docs else 'WMT-INV-003'}*: safety stock = 1.5× lead-time demand. All stockout SKUs have triggered emergency POs within the 4-hour SLA window."
            ),
            "vendor": (
                f"**Vendor Risk Intelligence Report**\n\n"
                f"**{vendor_out.get('total_vendors', 0)} vendors** active across 3 tiers:\n\n"
                f"| Risk Tier | Count |\n|-----------|-------|\n"
                f"| 🔴 High/Critical | {vendor_out.get('high_risk_count', 0)} |\n"
                f"| 🟢 Low/Medium | {vendor_out.get('total_vendors', 0) - vendor_out.get('high_risk_count', 0)} |\n\n"
                f"**Vendor Health Score:** {kpis.get('vendor_health_score', 'N/A')}/100\n\n"
                f"Top risk signals: delivery delays, quality rejections, capacity constraints.\n\n"
                f"Per *{docs[0]['title'] if docs else 'WMT-VRF-2024'}*: vendors scoring >75 require C-suite notification and contingency sourcing activation."
            ),
            "demand": (
                f"**Demand Forecasting Intelligence**\n\n"
                f"Forecast model ensemble: XGBoost v4 + LightGBM v3 + Prophet v2 + DeepAR\n"
                f"**MAPE:** {dem_out.get('forecast_mape', 'N/A'):.1f}% (target: <6% for Tier-A)\n"
                f"**Anomalies detected:** {dem_out.get('anomaly_count', 0)} transactions flagged\n\n"
                f"**Seasonal demand alerts:**\n"
                + "\n".join(
                    f"• {a['department']}: +{a.get('recommended_stock_increase_pct', 0):.0f}% stock uplift for *{a.get('event', 'Seasonal')}*"
                    for a in dem_out.get("seasonal_alerts", [])[:4]
                ) or "No active seasonal alerts."
                + f"\n\nTotal period revenue: **${kpis.get('revenue_period_usd', 0):,.0f}** across {kpis.get('total_transactions', 0):,} transactions."
            ),
            "logistics": (
                f"**Logistics & Distribution Network Status**\n\n"
                f"Network avg utilization: **{log_out.get('network_util', 0):.1f}%** (target: ≤82%)\n"
                f"DC bottlenecks detected: **{len(log_out.get('bottlenecks', []))}** facilities in stressed/critical state\n"
                f"Route optimizations: **{len(log_out.get('route_opts', []))}** delivery routes optimized\n\n"
                + (
                    "**Bottleneck Summary:**\n" +
                    "\n".join(f"• DC-{b['dc_id']}: {b['utilization']:.1f}% util — {b['recommended']}"
                              for b in log_out.get("bottlenecks", [])[:4])
                    if log_out.get("bottlenecks") else "No active DC bottlenecks."
                )
                + f"\n\nPer *{docs[0]['title'] if docs else 'WMT-DC-001'}*: utilization >91% triggers automatic overtime authorization."
            ),
            "pricing": (
                f"**Pricing Intelligence & Promotion Analytics**\n\n"
                f"Competitive gaps identified: **{len(pricing_out.get('price_gaps', []))}** SKUs with >4% gap vs competitors\n"
                f"Active promotions analyzed: **{len(pricing_out.get('promo_analysis', []))}** campaigns\n"
                f"Markdown recommendations: **{len(pricing_out.get('markdown_recs', []))}** overstock SKUs\n"
                f"Price architecture violations: **{len(pricing_out.get('architecture_violations', []))}** (SVP approval required)\n\n"
                f"Top recommended action: `{pricing_out.get('price_gaps', [{}])[0].get('action', 'N/A') if pricing_out.get('price_gaps') else 'N/A'}` "
                f"on highest-gap SKU.\n\nPer *{docs[0]['title'] if docs else 'WMT-PRICE-009'}*: overstock items >60 days auto-trigger 25% markdown."
            ),
            "executive": (
                f"**Executive Operational Summary**\n\n"
                f"```\n{exec_out.get('narrative', 'Pipeline not yet run.')}\n```\n\n"
                f"**Strategic Risks:** {len(exec_out.get('strategic_risks', []))}\n"
                + "\n".join(f"• [{r['severity']}] {r['title']}: {r['impact']}"
                             for r in exec_out.get("strategic_risks", [])[:3])
                + f"\n\n**Active Alerts:** {kpis.get('active_alerts', 0)} | **HITL Pending:** {kpis.get('hitl_pending', 0)}"
            ),
            "general": (
                f"**Walmart AI Decision Intelligence Platform**\n\n"
                f"I have full visibility into the operational state across:\n"
                f"• **Inventory:** {kpis.get('stockout_rate_pct', 0):.2f}% stockout rate | {kpis.get('fill_rate_pct', 0):.1f}% fill rate\n"
                f"• **Revenue:** ${kpis.get('revenue_period_usd', 0):,.0f} tracked\n"
                f"• **Vendors:** {kpis.get('vendor_health_score', 0)}/100 health score\n"
                f"• **Logistics:** {kpis.get('dc_avg_utilization_pct', 0):.1f}% DC utilization\n"
                f"• **Alerts:** {kpis.get('active_alerts', 0)} active\n\n"
                f"Ask me about inventory levels, vendor risk, demand forecasting, pricing, DC operations, or for an executive summary."
            ),
        }
        text = RESPONSES.get(intent, RESPONSES["general"])
        return {"text": text, "citations": citations}

    def _execute(self, state: AgentState) -> AgentState:
        """Pipeline mode — readiness initialization."""
        self._think(state, "ConversationalAgent initialized and ready for interactive queries.")
        state.agent_outputs["ConversationalAgent"] = {
            "status":       "READY",
            "mode":         "INTERACTIVE",
            "docs_indexed": len(self.KNOWLEDGE_BASE),
            "memory_turns": len(self._conversation_history),
        }
        return state


# ─────────────────────────────────────────────────────────────────────────────
#  ORCHESTRATOR  (LangGraph-style execution graph manager)
# ─────────────────────────────────────────────────────────────────────────────

class WalmartOrchestrator:
    """
    Manages the full 5-layer agent execution graph.

    Execution order:
      Layer 1 (parallel-capable): DemandForecastAgent, VendorRiskAgent
      Layer 2 (depends on L1):    InventoryOptAgent, PricingPromoAgent
      Layer 3 (depends on L2):    LogisticsCoordAgent
      Layer 4 (synthesis):        ExecutiveInsightAgent
      Layer 5 (interface):        ConversationalAgent
    """

    GRAPH_SPEC = {
        "nodes": [
            {"id": "DemandForecastAgent",   "layer": 1, "type": "analytics",  "color": "#3b82f6", "model": "claude-3-haiku-20240307"},
            {"id": "VendorRiskAgent",        "layer": 1, "type": "risk",       "color": "#ef4444", "model": "claude-3-haiku-20240307"},
            {"id": "InventoryOptAgent",      "layer": 2, "type": "operations", "color": "#10b981", "model": "claude-3-haiku-20240307"},
            {"id": "PricingPromoAgent",      "layer": 2, "type": "revenue",    "color": "#f59e0b", "model": "claude-3-haiku-20240307"},
            {"id": "LogisticsCoordAgent",    "layer": 3, "type": "logistics",  "color": "#8b5cf6", "model": "claude-3-haiku-20240307"},
            {"id": "ExecutiveInsightAgent",  "layer": 4, "type": "synthesis",  "color": "#0071ce", "model": "claude-3-5-sonnet-20241022"},
            {"id": "ConversationalAgent",    "layer": 5, "type": "interface",  "color": "#64748b", "model": "claude-3-5-sonnet-20241022"},
        ],
        "edges": [
            {"from": "DemandForecastAgent",  "to": "InventoryOptAgent",    "label": "demand_context",    "type": "data"},
            {"from": "DemandForecastAgent",  "to": "PricingPromoAgent",    "label": "demand_signals",    "type": "data"},
            {"from": "VendorRiskAgent",       "to": "ExecutiveInsightAgent","label": "risk_alerts",       "type": "alert"},
            {"from": "InventoryOptAgent",     "to": "LogisticsCoordAgent",  "label": "replenishment_pos", "type": "request"},
            {"from": "InventoryOptAgent",     "to": "PricingPromoAgent",    "label": "overstock_flags",   "type": "data"},
            {"from": "InventoryOptAgent",     "to": "ExecutiveInsightAgent","label": "inv_summary",       "type": "data"},
            {"from": "PricingPromoAgent",     "to": "ExecutiveInsightAgent","label": "pricing_intel",     "type": "data"},
            {"from": "LogisticsCoordAgent",   "to": "ExecutiveInsightAgent","label": "dc_health",         "type": "data"},
            {"from": "ExecutiveInsightAgent", "to": "ConversationalAgent",  "label": "grounded_context",  "type": "context"},
        ],
    }

    def __init__(self):
        self._agents = {
            "DemandForecastAgent":  DemandForecastAgent(),
            "VendorRiskAgent":       VendorRiskAgent(),
            "InventoryOptAgent":     InventoryOptAgent(),
            "PricingPromoAgent":     PricingPromoAgent(),
            "LogisticsCoordAgent":   LogisticsCoordAgent(),
            "ExecutiveInsightAgent": ExecutiveInsightAgent(),
            "ConversationalAgent":   ConversationalAgent(),
        }
        self._conv_agent = self._agents["ConversationalAgent"]
        self._current_state: Optional[AgentState] = None
        self._run_history: List[Dict] = []
        self._lock = threading.Lock()

    def run_pipeline(self, data_context: Dict, trigger: str = "SCHEDULED") -> AgentState:
        """Execute the full orchestration graph and return final state."""
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        t0     = time.perf_counter()

        state = AgentState(
            run_id=run_id, trigger=trigger, trigger_payload={},
            context=data_context, agent_outputs={}, messages=[],
            trace=[], decisions=[], alerts=[], hitl_queue=[], metadata={},
        )

        EXECUTION_ORDER = [
            ["DemandForecastAgent", "VendorRiskAgent"],   # Layer 1
            ["InventoryOptAgent", "PricingPromoAgent"],   # Layer 2
            ["LogisticsCoordAgent"],                       # Layer 3
            ["ExecutiveInsightAgent"],                     # Layer 4
            ["ConversationalAgent"],                       # Layer 5
        ]

        for layer_idx, layer_agents in enumerate(EXECUTION_ORDER):
            for agent_name in layer_agents:
                agent = self._agents[agent_name]
                state = agent.run(state)

        elapsed = round((time.perf_counter() - t0) * 1000) / 1000

        state.metadata.update({
            "run_id":            run_id,
            "trigger":           trigger,
            "elapsed_sec":       elapsed,
            "total_messages":    len(state.messages),
            "total_alerts":      len(state.alerts),
            "total_decisions":   len(state.decisions),
            "total_trace_steps": len(state.trace),
            "hitl_count":        len(state.hitl_queue),
            "agent_stats":       {n: a.stats for n, a in self._agents.items()},
            "total_cost_usd":    round(sum(a._total_cost for a in self._agents.values()), 6),
            "total_tokens":      sum(a._total_tokens for a in self._agents.values()),
        })

        with self._lock:
            self._current_state = state
            self._run_history.append({
                "run_id": run_id, "ts": datetime.utcnow().isoformat(),
                "elapsed": elapsed, "status": state.status,
                "alerts": len(state.alerts), "decisions": len(state.decisions),
            })

        return state

    def chat(self, message: str) -> Dict:
        with self._lock:
            if self._current_state is None:
                return {
                    "response": "⚠️ Please run the agent pipeline first to initialize the knowledge context.",
                    "citations": [], "react_trace": [], "rag_docs": [], "confidence": 0,
                    "llm_metadata": {}, "ts": datetime.utcnow().isoformat(), "turn": 0,
                }
            return self._conv_agent.chat(message, self._current_state)

    @property
    def current_state(self) -> Optional[AgentState]:
        return self._current_state

    @property
    def agent_stats(self) -> Dict:
        return {n: a.stats for n, a in self._agents.items()}

    def graph_spec(self) -> Dict:
        return self.GRAPH_SPEC
