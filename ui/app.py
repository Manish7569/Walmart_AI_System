"""
WALMART AI DECISION INTELLIGENCE PLATFORM — ENTERPRISE UI v2.0
Executive Operations Command Center · 10 Operational Pages
"""
import sys, os, time, random
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from data.generators.engine import engine
from platform_core.orchestration.engine import WalmartOrchestrator

st.set_page_config(page_title="Walmart AI | Decision Intelligence", page_icon="⚡",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--wmt-blue:#0071CE;--wmt-navy:#002D63;--wmt-yellow:#FFC220;--s0:#060C1A;--s1:#0A1428;--s2:#0E1C38;--s3:#132246;--border:rgba(0,113,206,0.15);--tx-primary:#DCE8F5;--tx-secondary:#7A90B0;--tx-muted:#3D5070;--green:#10B981;--red:#EF4444;--amber:#F59E0B;--purple:#8B5CF6}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:var(--s0)!important;color:var(--tx-primary)!important}
.stApp{background:var(--s0)!important}
.main .block-container{padding:1.2rem 2rem 2rem!important;max-width:100%!important}
[data-testid="stSidebar"]{background:var(--s1)!important;border-right:1px solid var(--border)}
[data-testid="stSidebar"] *{color:var(--tx-primary)!important}
[data-testid="stSidebar"] .stRadio label{background:transparent;border:1px solid transparent;border-radius:7px;padding:9px 13px;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s;display:block}
[data-testid="stSidebar"] .stRadio label:hover{background:var(--s2);border-color:var(--border)}
[data-testid="metric-container"]{background:var(--s2)!important;border:1px solid var(--border)!important;border-radius:10px!important;padding:16px 18px!important}
[data-testid="stMetricValue"]{font-size:1.75rem!important;font-weight:700!important;color:var(--tx-primary)!important}
[data-testid="stMetricLabel"]{font-size:11px!important;color:var(--tx-secondary)!important;text-transform:uppercase!important;letter-spacing:.08em!important;font-weight:600!important}
.wcard{background:var(--s2);border:1px solid var(--border);border-radius:12px;padding:20px 22px;margin:6px 0}
.wcard-sm{background:var(--s2);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin:4px 0}
.ph{background:linear-gradient(135deg,var(--s1),var(--s2));border:1px solid var(--border);border-radius:12px;padding:18px 24px;margin-bottom:20px}
.pt{font-size:17px;font-weight:700;color:var(--tx-primary)}
.ps{font-size:12px;color:var(--tx-secondary);margin-top:3px}
.sec{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--tx-muted);padding-bottom:7px;border-bottom:1px solid var(--border);margin:22px 0 14px}
.arow{background:var(--s2);border:1px solid var(--border);border-left:3px solid var(--wmt-blue);border-radius:8px;padding:12px 16px;margin:5px 0}
.aname{font-size:12px;font-weight:700;color:var(--wmt-yellow)}
.atext{font-size:13px;color:var(--tx-primary);margin:4px 0 0;line-height:1.55}
.ameta{font-size:10.5px;color:var(--tx-muted);font-family:'JetBrains Mono',monospace;margin-top:4px}
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin:0 3px}
.sc{background:rgba(239,68,68,.18);color:#EF4444;border:1px solid rgba(239,68,68,.35)}
.sh{background:rgba(245,158,11,.18);color:#F59E0B;border:1px solid rgba(245,158,11,.35)}
.sm{background:rgba(59,130,246,.18);color:#60A5FA;border:1px solid rgba(59,130,246,.35)}
.sl{background:rgba(16,185,129,.18);color:#34D399;border:1px solid rgba(16,185,129,.35)}
.ts{background:var(--s1);border-left:2px solid var(--wmt-blue);padding:5px 11px;margin:2px 0;border-radius:0 6px 6px 0;font-size:11.5px;font-family:'JetBrains Mono',monospace;color:var(--tx-secondary)}
.tt{border-left-color:var(--purple)}.ta{border-left-color:var(--amber)}.to{border-left-color:var(--green)}.tf{border-left-color:var(--wmt-blue);color:var(--tx-primary)}
.cu{background:var(--wmt-blue);color:white;padding:10px 16px;border-radius:16px 16px 4px 16px;margin:8px 0;max-width:75%;float:right;clear:both;font-size:13.5px}
.ca{background:var(--s3);border:1px solid var(--border);color:var(--tx-primary);padding:13px 17px;border-radius:4px 16px 16px 16px;margin:8px 0;max-width:90%;float:left;clear:both;font-size:13.5px;line-height:1.7}
.cc{font-size:10.5px;color:var(--wmt-blue);border-top:1px solid var(--border);margin-top:9px;padding-top:5px}
.ccon{overflow:hidden;min-height:10px}
.stButton>button{background:var(--wmt-blue)!important;color:white!important;border:none!important;border-radius:7px!important;font-size:13px!important;font-weight:600!important;padding:9px 18px!important}
.stButton>button:hover{background:#005BAD!important;transform:translateY(-1px)!important}
.stTabs [data-baseweb="tab-list"]{background:var(--s1)!important;border-radius:8px!important;padding:4px!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--tx-secondary)!important;border-radius:6px!important;font-size:12.5px!important}
.stTabs [aria-selected="true"]{background:var(--s3)!important;color:var(--tx-primary)!important}
.stDataFrame{border:1px solid var(--border)!important;border-radius:8px!important}
::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-thumb{background:var(--s3);border-radius:3px}
.stTextInput input{background:var(--s2)!important;border:1px solid var(--border)!important;color:var(--tx-primary)!important;border-radius:7px!important}
.streamlit-expanderHeader{background:var(--s2)!important;border:1px solid var(--border)!important;border-radius:7px!important;font-size:13px!important}
</style>
""", unsafe_allow_html=True)

# Plotly theme
PBG="#0A1428"; GC="rgba(0,113,206,0.10)"; AC="#3D5070"
BLUE="#0071CE"; YELLOW="#FFC220"; GREEN="#10B981"; RED="#EF4444"; PURPLE="#8B5CF6"

def _fig(fig, h=300):
    fig.update_layout(height=h,margin=dict(t=8,b=8,l=10,r=10),
        plot_bgcolor=PBG,paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=AC,family="Inter",size=10.5),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color=AC,size=10)),
        xaxis=dict(gridcolor=GC,linecolor=GC,tickcolor=AC,zerolinecolor=GC),
        yaxis=dict(gridcolor=GC,linecolor=GC,tickcolor=AC,zerolinecolor=GC))
    return fig

def badge(sev):
    m={"Critical":"sc","High":"sh","Medium":"sm","Low":"sl"}
    return f'<span class="badge {m.get(sev,"sm")}">{sev}</span>'

# Session state
for k,v in [("orc",None),("pipeline",None),("chat_hist",[]),("data_ready",False)]:
    if k not in st.session_state:
        st.session_state[k] = v
if st.session_state.orc is None:
    st.session_state.orc = WalmartOrchestrator()
ORC = st.session_state.orc

FAST_STARTUP = os.environ.get("WALMART_AI_FAST_STARTUP", "1").lower() in ("1", "true", "yes")
if not st.session_state.data_ready:
    startup_label = "300 stores · 3K SKUs · 12K transactions" if FAST_STARTUP else "4,200 stores · 50K SKUs · 60K transactions"
    with st.spinner(f"⚙️ Initializing Walmart Data Engine — {startup_label}..."):
        engine.initialize(verbose=False, fast=FAST_STARTUP)
        st.session_state.data_ready = True
    if FAST_STARTUP:
        st.info("Local fast startup enabled. Set WALMART_AI_FAST_STARTUP=0 for full enterprise mode.")

# Sidebar
with st.sidebar:
    st.markdown('<div style="padding:16px 4px 10px;"><div style="font-size:20px;font-weight:800;color:#FFC220;">⚡ WALMART AI</div><div style="font-size:9.5px;color:#3D5070;letter-spacing:.20em;text-transform:uppercase;margin-top:1px;">Decision Intelligence Platform</div></div><div style="height:1px;background:rgba(0,113,206,.18);margin:0 0 14px;"></div>', unsafe_allow_html=True)
    page = st.radio("N", ["🏠  Executive Command","📡  Live Data Streams","🤖  Agent Orchestration",
        "📦  Inventory Intelligence","🚚  Vendor Risk Center","📈  Demand & Forecasting",
        "💲  Pricing Intelligence","💬  Conversational AI","🔭  AI Observability","🏗️  Architecture"],
        label_visibility="collapsed")
    st.markdown('<div style="height:1px;background:rgba(0,113,206,.18);margin:14px 0 12px;"></div>', unsafe_allow_html=True)
    pr=st.session_state.pipeline; s=engine.summary()
    st.markdown(f'<div style="font-size:12px;line-height:2.1;color:#7A90B0;">🟢 Data Engine: {s.get("stores",0):,} stores<br/>🟢 SKUs: {s.get("skus",0):,} · Txns: {s.get("pos_transactions",0):,}<br/>{"🟢" if pr else "🟡"} Pipeline: {"✅ "+pr.status if pr else "⏸ Awaiting run"}<br/>🟢 7 Agents: Online</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="height:1px;background:rgba(0,113,206,.18);margin:12px 0;"></div><div style="font-size:9.5px;color:#3D5070;line-height:2.3;">LangGraph · Amazon Bedrock<br/>Apache Kafka · Snowflake<br/>Pinecone · Neo4j · FAISS<br/>Prometheus · Grafana<br/>Docker · Kubernetes · Terraform</div><div style="margin-top:10px;font-size:10px;color:#3D5070;">🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# EXECUTIVE COMMAND
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Executive Command":
    st.markdown(f'<div class="ph" style="display:flex;justify-content:space-between;align-items:center;"><div><div class="pt">Walmart Supply Chain Decision Intelligence</div><div class="ps">Enterprise Operations Command Center · AI-Native · Real-Time Monitoring</div></div><div style="text-align:right;font-size:12px;color:#7A90B0;">{datetime.now().strftime("%A, %B %d %Y")}<br/><span style="color:#FFC220;font-weight:700;">{datetime.now().strftime("%H:%M")} CST</span></div></div>', unsafe_allow_html=True)
    pos=engine.pos; inv=engine.inventory; decs=engine.decisions
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("💰 Period Revenue",f"${pos['total_revenue'].sum()/1e6:.1f}M","+7.8% vs LY")
    c2.metric("🔴 Stockouts",f"{(inv['status']=='Stockout').sum():,}","-4 vs yesterday")
    c3.metric("🟠 Critical SKUs",f"{(inv['status']=='Critical').sum():,}","+11 today")
    c4.metric("🏭 DC Utilization",f"{engine.telemetry['dock_utilization_pct'].mean():.0f}%","-0.8%")
    c5.metric("🚚 High-Risk Vendors",f"{engine.vendors['risk'].isin(['High','Critical']).sum()}","+1 this week")
    c6.metric("🤖 AI Decisions",f"{len(decs):,}",f"{(decs['severity']=='Critical').sum()} critical")

    st.markdown('<div class="sec">Revenue Intelligence</div>', unsafe_allow_html=True)
    try:
        ca,cb=st.columns([2,1])
        with ca:
            if len(pos) > 0 and "total_revenue" in pos.columns and "date" in pos.columns:
                daily=pos.groupby("date")["total_revenue"].sum().reset_index(); daily["date"]=pd.to_datetime(daily["date"]); ma7=daily["total_revenue"].rolling(7,min_periods=1).mean()
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=daily["date"],y=daily["total_revenue"],fill="tozeroy",fillcolor="rgba(0,113,206,.07)",line=dict(color=BLUE,width=1.5),name="Daily Rev",mode="lines"))
                fig.add_trace(go.Scatter(x=daily["date"],y=ma7,line=dict(color=YELLOW,width=2,dash="dot"),name="7d MA",mode="lines"))
                fig.update_yaxes(tickprefix="$",tickformat=",.0f"); _fig(fig,270); fig.update_layout(title=dict(text="90-Day Revenue Trend",font=dict(size=12,color=AC))); st.plotly_chart(fig,use_container_width=True)
            else:
                st.warning("⚠️ Revenue data not available. POS transactions may be loading...")
        with cb:
            if len(pos) > 0 and "total_revenue" in pos.columns and "department" in pos.columns:
                dr=pos.groupby("department")["total_revenue"].sum().sort_values(ascending=True).tail(6)
                if len(dr) > 0:
                    fig2=go.Figure(go.Bar(y=dr.index,x=dr.values,orientation="h",marker=dict(color=dr.values,colorscale=[[0,"#002D63"],[.5,BLUE],[1,YELLOW]])))
                    fig2.update_xaxes(tickprefix="$",tickformat=",.0f"); _fig(fig2,270); fig2.update_layout(margin=dict(l=130,r=10,t=8,b=8),title=dict(text="Revenue by Department",font=dict(size=12,color=AC))); st.plotly_chart(fig2,use_container_width=True)
                else:
                    st.info("ℹ️ No department data available yet")
            else:
                st.warning("⚠️ Department data incomplete")
    except Exception as e:
        st.error(f"❌ Revenue Intelligence Error: {str(e)}")

    cc,cd=st.columns(2)
    with cc:
        sc=inv["status"].value_counts().reset_index(); sc.columns=["status","count"]
        cm={"Stockout":RED,"Critical":"#F97316","Below Reorder":YELLOW,"Healthy":GREEN,"Overstock":PURPLE,"Excess":"#64748B"}
        fig3=go.Figure(go.Bar(x=sc["status"],y=sc["count"],marker_color=[cm.get(s,BLUE) for s in sc["status"]]))
        _fig(fig3,240); fig3.update_layout(showlegend=False,title=dict(text="Inventory Health Distribution",font=dict(size=12,color=AC))); st.plotly_chart(fig3,use_container_width=True)
    with cd:
        rr=pos.groupby("region")["total_revenue"].sum().reset_index()
        fig4=go.Figure(go.Pie(labels=rr["region"],values=rr["total_revenue"],hole=.56,marker_colors=[BLUE,"#005BAD",YELLOW,"#002D63",GREEN,PURPLE]))
        fig4.update_traces(textfont_color="white",textfont_size=10); _fig(fig4,240); fig4.update_layout(title=dict(text="Revenue by Region",font=dict(size=12,color=AC))); st.plotly_chart(fig4,use_container_width=True)

    st.markdown('<div class="sec">AI Agent Decision Feed</div>', unsafe_allow_html=True)
    for _,row in decs.head(8).iterrows():
        st.markdown(f'<div class="arow"><div style="display:flex;justify-content:space-between;"><div><span class="aname">{row["agent"]}</span> {badge(row["severity"])} <span class="badge sm">{row["decision_type"]}</span></div><div style="font-size:10px;color:var(--tx-muted);">{str(row["timestamp"])[:16]}</div></div><div class="atext">{str(row["decision_text"])[:170]}{"…" if len(str(row["decision_text"]))>170 else ""}</div><div class="ameta">conf:{row["confidence"]} · {row["tokens_consumed"]:,}tok · {row["latency_ms"]}ms · ${row["business_impact_usd"]:,.0f} · {row["status"]}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# LIVE DATA STREAMS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📡  Live Data Streams":
    st.markdown('<div class="ph"><div class="pt">📡 Real-Time Data Streams</div><div class="ps">Apache Kafka simulation · Event-driven architecture · 100M+ weekly events</div></div>', unsafe_allow_html=True)
    topics={"wmt.pos.transactions":{"p":64,"m":random.randint(850,1900),"l":random.randint(0,80)},"wmt.inventory.updates":{"p":32,"m":random.randint(200,520),"l":random.randint(0,35)},"wmt.vendor.events":{"p":16,"m":random.randint(20,90),"l":random.randint(0,12)},"wmt.warehouse.telemetry":{"p":24,"m":random.randint(100,420),"l":random.randint(0,20)},"wmt.demand.signals":{"p":8,"m":random.randint(45,150),"l":random.randint(0,6)},"wmt.anomaly.alerts":{"p":4,"m":random.randint(1,18),"l":0}}
    cols=st.columns(3)
    for i,(t,s) in enumerate(topics.items()):
        d="🟢" if s["l"]<40 else "🟡" if s["l"]<80 else "🔴"
        with cols[i%3]:
            st.markdown(f'<div class="wcard-sm"><div style="font-size:9.5px;color:var(--tx-muted);font-family:\'JetBrains Mono\',monospace;">{d} {t}</div><div style="font-size:20px;font-weight:700;margin:8px 0 4px;">{s["m"]:,} <span style="font-size:12px;color:var(--tx-secondary);">msg/s</span></div><div style="font-size:10.5px;color:var(--tx-secondary);">P={s["p"]} · lag={s["l"]}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">Live Event Feed</div>', unsafe_allow_html=True)
    et=["POS_TRANSACTION","INVENTORY_UPDATE","VENDOR_SHIPMENT","DC_TELEMETRY","DEMAND_SIGNAL","ANOMALY_DETECTED"]
    ss=[f"WMT-{i:05d}" for i in range(1001,1030)]; sk=[f"SKU-{i:07d}" for i in range(1,200)]
    evs=sorted([{"ts":(datetime.now()-timedelta(seconds=random.randint(0,90))).strftime("%H:%M:%S.%f")[:12],"type":random.choice(et),"store":random.choice(ss),"sku":random.choice(sk),"amt":f"${random.uniform(1.5,999):.2f}"} for _ in range(30)],key=lambda x:x["ts"],reverse=True)
    feed='<div class="wcard" style="font-family:\'JetBrains Mono\',monospace;font-size:11px;max-height:380px;overflow-y:auto;">'
    for ev in evs:
        c=RED if "ANOMALY" in ev["type"] else YELLOW if "VENDOR" in ev["type"] else BLUE
        feed+=f'<div style="padding:5px 0;border-bottom:1px solid rgba(0,113,206,.08);display:flex;gap:12px;"><span style="color:var(--tx-muted);min-width:90px;">{ev["ts"]}</span><span style="color:{c};min-width:200px;font-weight:500;">{ev["type"]}</span><span style="color:var(--tx-secondary);">{ev["store"]} · {ev["sku"]} · {ev["amt"]}</span></div>'
    feed+='</div>'; st.markdown(feed,unsafe_allow_html=True)

    st.markdown('<div class="sec">Kafka Throughput — 48h</div>', unsafe_allow_html=True)
    hrs=list(range(48)); fig=go.Figure()
    for name,base,color in [("POS Transactions",1200,BLUE),("Inventory Updates",350,GREEN),("Vendor Events",55,YELLOW)]:
        fig.add_trace(go.Scatter(x=hrs,y=[max(0,base+random.randint(-base//3,base//3)) for _ in hrs],name=name,mode="lines",fill="tozeroy" if name=="POS Transactions" else "none",fillcolor="rgba(0,113,206,.06)",line=dict(color=color,width=1.8)))
    fig.update_xaxes(title="Hours ago"); fig.update_yaxes(title="msg/s"); _fig(fig,260); st.plotly_chart(fig,use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT ORCHESTRATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤖  Agent Orchestration":
    st.markdown('<div class="ph"><div class="pt">🤖 Multi-Agent Orchestration Engine</div><div class="ps">LangGraph-style execution graph · 7 specialized agents · Event-driven A2A communication</div></div>', unsafe_allow_html=True)
    col_btn,col_stat=st.columns([3,1])
    with col_btn:
        if st.button("🚀  Execute Full Agent Pipeline",use_container_width=True):
            ctx={"pos":engine.pos,"inventory":engine.inventory,"vendor_events":engine.vendor_events,"telemetry":engine.telemetry,"demand_signals":engine.demand_signals,"vendors":engine.vendors,"pricing":engine.pricing}
            prog=st.progress(0); sbox=st.empty()
            AGENTS=[("DemandForecastAgent","📈 Analyzing 90-day POS stream + anomaly detection…"),("VendorRiskAgent","🚚 Scoring risk across 25 vendors via ML model…"),("InventoryOptAgent","📦 Scanning 300 stores × 600 SKUs + generating POs…"),("PricingPromoAgent","💲 Computing competitive gaps + markdown cascade…"),("LogisticsCoordAgent","🏭 Optimizing DC routing across 24 facilities…"),("ExecutiveInsightAgent","📊 Synthesizing executive intelligence package…"),("ConversationalAgent","💬 Initializing RAG context for conversational AI…")]
            for i,(agent,msg) in enumerate(AGENTS):
                sbox.markdown(f'<div class="arow"><span class="aname">⚡ {agent}</span> <span style="color:var(--tx-secondary);font-size:13px;margin-left:10px;">{msg}</span></div>',unsafe_allow_html=True)
                prog.progress((i+1)/len(AGENTS)); time.sleep(0.45)
            result=ORC.run_pipeline(ctx,"USER_REQUEST"); st.session_state.pipeline=result
            prog.empty(); sbox.empty()
            st.success(f"✅ Pipeline complete · {result.run_id} · {result.metadata['elapsed_sec']:.2f}s · {len(result.alerts)} alerts · {len(result.decisions)} decisions · ${result.metadata['total_cost_usd']:.5f}")
    with col_stat:
        res=st.session_state.pipeline
        if res:
            st.markdown(f'<div class="wcard-sm"><div style="font-size:11px;font-family:\'JetBrains Mono\',monospace;line-height:2;color:var(--tx-secondary);">{res.run_id}<br/>Status: <span style="color:var(--green);">{res.status}</span><br/>{res.metadata.get("elapsed_sec",0):.2f}s · {len(res.alerts)} alerts<br/>HITL: {len(res.hitl_queue)} · ${res.metadata.get("total_cost_usd",0):.5f}</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="sec">Agent Execution Graph</div>', unsafe_allow_html=True)
    spec=ORC.graph_spec(); LX={1:.08,2:.32,3:.55,4:.75,5:.94}
    by_layer={}
    for n in spec["nodes"]: by_layer.setdefault(n["layer"],[]).append(n)
    np_={};  
    for ln,nodes in sorted(by_layer.items()):
        for i,n in enumerate(nodes): np_[n["id"]]=(LX[ln],(i+1)/(len(nodes)+1))
    fig_g=go.Figure()
    for e in spec["edges"]:
        x0,y0=np_[e["from"]]; x1,y1=np_[e["to"]]
        ec=RED if e["type"]=="alert" else GREEN if e["type"]=="request" else "rgba(0,113,206,.28)"
        fig_g.add_trace(go.Scatter(x=[x0,x1,None],y=[y0,y1,None],mode="lines",line=dict(color=ec,width=1.3),hoverinfo="none",showlegend=False))
        fig_g.add_annotation(x=(x0+x1)/2,y=(y0+y1)/2,text=e["label"],showarrow=False,font=dict(size=7.5,color=AC),bgcolor="rgba(10,20,40,.85)",borderpad=2)
    res=st.session_state.pipeline
    for n in spec["nodes"]:
        x,y=np_[n["id"]]; done=res and res.agent_outputs.get(n["id"],{}).get("status")=="COMPLETED"
        fig_g.add_trace(go.Scatter(x=[x],y=[y],mode="markers+text",showlegend=False,marker=dict(size=56,color=n["color"] if done else "#132246",line=dict(color=n["color"],width=2.5)),text=[n["id"].replace("Agent","")],textposition="middle center",textfont=dict(size=8.5,color="white",family="Inter")))
    LL={1:"Parallel L1",2:"Dependent L2",3:"Aggregation L3",4:"Synthesis L4",5:"Interface L5"}
    for ln,lx in LX.items(): fig_g.add_annotation(x=lx,y=.03,text=LL[ln],showarrow=False,font=dict(size=8.5,color=AC),xanchor="center")
    fig_g.update_layout(height=370,plot_bgcolor=PBG,paper_bgcolor="rgba(0,0,0,0)",xaxis=dict(showgrid=False,showticklabels=False,zeroline=False,range=[0,1.05]),yaxis=dict(showgrid=False,showticklabels=False,zeroline=False,range=[0,1.05]),margin=dict(t=8,b=30,l=8,r=8))
    st.plotly_chart(fig_g,use_container_width=True)

    if not st.session_state.pipeline:
        st.info("👆 Run the pipeline above to see agent outputs, execution traces and decisions."); st.stop()

    res=st.session_state.pipeline
    tabs=st.tabs(["📈 Demand","📦 Inventory","🚚 Vendor","🏭 Logistics","💲 Pricing","📊 Executive","🔍 Trace","⚠️ Alerts","📋 HITL","📨 Messages"])

    with tabs[0]:
        out=res.agent_outputs.get("DemandForecastAgent",{})
        c1,c2,c3=st.columns(3); c1.metric("Findings",len(out.get("findings",[]))); c2.metric("Anomalies",out.get("anomaly_count",0)); c3.metric("MAPE",f"{out.get('forecast_mape',0):.1f}%")
        for f in out.get("findings",[])[:6]: st.markdown(f'<div class="arow">{badge("High" if "PRIORITIZE" in str(f.get("recommended_action","")) else "Medium")} <span class="atext">{f.get("insight","")}</span><div class="ameta">action:{f.get("recommended_action","")} · conf:{f.get("confidence","")} · ${f.get("impact_usd",0):,.0f}</div></div>',unsafe_allow_html=True)

    with tabs[1]:
        out=res.agent_outputs.get("InventoryOptAgent",{}); summ=out.get("summary",{})
        c1,c2,c3,c4=st.columns(4); c1.metric("Stockouts",summ.get("stockout_count",0)); c2.metric("Critical",summ.get("critical_count",0)); c3.metric("POs",len(out.get("replenishment_orders",[]))); c4.metric("Overstock",len(out.get("overstock_flags",[])))
        st.caption(f"Inv Value: ${summ.get('total_inv_value',0):,.0f} · Fill Rate: {summ.get('fill_rate_avg',0)*100:.1f}% · Avg DOS: {summ.get('avg_dos',0):.1f}d")
        pod=pd.DataFrame(out.get("replenishment_orders",[]))
        if len(pod): st.dataframe(pod.head(20)[["po_id","store_id","region","product_name","quantity","urgency","po_value","lead_days"]],use_container_width=True,height=300)

    with tabs[2]:
        out=res.agent_outputs.get("VendorRiskAgent",{}); c1,c2=st.columns(2); c1.metric("Assessed",out.get("total_vendors",0)); c2.metric("High-Risk",out.get("high_risk_count",0))
        rd=pd.DataFrame(out.get("risk_scores",[]))
        if len(rd):
            figr=go.Figure(go.Bar(x=rd["vendor_name"].head(12),y=rd["risk_score"].head(12),marker_color=[RED if s>75 else YELLOW if s>50 else BLUE if s>25 else GREEN for s in rd["risk_score"].head(12)]))
            figr.add_hline(y=50,line_dash="dash",line_color=YELLOW); figr.add_hline(y=75,line_dash="dash",line_color=RED); _fig(figr,260); figr.update_xaxes(tickangle=-30); st.plotly_chart(figr,use_container_width=True)

    with tabs[3]:
        out=res.agent_outputs.get("LogisticsCoordAgent",{}); c1,c2,c3=st.columns(3); c1.metric("DCs",len(out.get("dc_health",[]))); c2.metric("Bottlenecks",len(out.get("bottlenecks",[]))); c3.metric("Routes",len(out.get("route_opts",[])))
        if out.get("dc_health"):
            dcd=pd.DataFrame(out["dc_health"])
            figdc=go.Figure(go.Bar(x=dcd["dc_id"],y=dcd["dock_utilization_pct"],marker_color=[RED if u>95 else YELLOW if u>88 else GREEN for u in dcd["dock_utilization_pct"]]))
            figdc.add_hline(y=82,line_dash="dash",line_color=GREEN,annotation_text="82% target"); figdc.add_hline(y=91,line_dash="dash",line_color=RED,annotation_text="OT trigger"); _fig(figdc,280); st.plotly_chart(figdc,use_container_width=True)

    with tabs[4]:
        out=res.agent_outputs.get("PricingPromoAgent",{}); c1,c2,c3,c4=st.columns(4); c1.metric("Price Gaps",len(out.get("price_gaps",[]))); c2.metric("Promos",len(out.get("promo_analysis",[]))); c3.metric("Markdowns",len(out.get("markdown_recs",[]))); c4.metric("Violations",len(out.get("architecture_violations",[])))
        for pg in out.get("price_gaps",[])[:6]:
            col=GREEN if pg.get("gap_pct",0)<0 else RED
            st.markdown(f'<div class="arow">{badge("High" if abs(pg.get("gap_pct",0))>10 else "Medium")} <b>{pg.get("product_name","")}</b> <span style="color:{col};font-size:12px;">{"+" if pg.get("gap_pct",0)>0 else ""}{pg.get("gap_pct",0):.1f}% vs comp</span><div class="ameta">curr:${pg.get("current_price",0):.2f} · comp:${pg.get("competitor_price",0):.2f} · {pg.get("action","")} · ${pg.get("revenue_impact_wk",0):,.0f}/wk</div></div>',unsafe_allow_html=True)

    with tabs[5]:
        out=res.agent_outputs.get("ExecutiveInsightAgent",{}); kpis=out.get("kpis",{})
        c1,c2,c3,c4=st.columns(4); c1.metric("Revenue",f"${kpis.get('revenue_period_usd',0):,.0f}"); c2.metric("Stockout Rate",f"{kpis.get('stockout_rate_pct',0):.2f}%"); c3.metric("Vendor Health",f"{kpis.get('vendor_health_score',0):.0f}/100"); c4.metric("Alerts",kpis.get("active_alerts",0))
        st.code(out.get("narrative",""),language=None)
        for risk in out.get("strategic_risks",[]): st.markdown(f'<div class="arow">{badge(risk["severity"])} <b>{risk["title"]}</b><div class="atext" style="font-size:12px;">{risk["impact"]}</div><div class="ameta">Action: {risk["action"]}</div></div>',unsafe_allow_html=True)

    with tabs[6]:
        trace=res.trace; st.caption(f"{len(trace)} trace steps across 7 agents")
        sc_={"THOUGHT":"tt","ACTION":"ta","OBSERVATION":"to","DECISION":"tf","FINAL":"tf"}
        for step in trace[-50:]:
            cls=sc_.get(step.step_type,"ts"); tool=f" → <span style='color:{YELLOW};'>{step.tool_name}</span>" if step.tool_name else ""
            st.markdown(f'<div class="ts {cls}"><span style="color:var(--tx-muted);">{step.ts[11:19]}</span> <span style="color:var(--wmt-yellow);font-weight:600;">[{step.agent.replace("Agent","")}]</span> {step.step_type}{tool}<br/>&nbsp;&nbsp;&nbsp;{step.content[:130]}</div>',unsafe_allow_html=True)

    with tabs[7]:
        for a in res.alerts: st.markdown(f'<div class="arow">{badge(a.get("severity","Medium"))} <b>{a.get("alert_type","")}</b> <span style="font-size:10px;color:var(--tx-muted);">{str(a.get("ts",""))[:16]} · {a.get("source_agent","")}</span><div class="atext" style="font-size:13px;">{a.get("description","")}</div></div>',unsafe_allow_html=True)

    with tabs[8]:
        if res.hitl_queue:
            for h in res.hitl_queue: st.markdown(f'<div class="arow" style="border-left-color:{RED};">{badge(h.severity)} <b>HITL Review</b> · {h.flag_id} · SLA:{h.sla_hours}h<div class="atext" style="font-size:13px;">{h.reason}</div><div class="ameta">Agent:{h.agent} · {h.created_ts[:16]}</div></div>',unsafe_allow_html=True)
        else: st.success("No items in HITL queue — all decisions within auto-approval thresholds.")

    with tabs[9]:
        st.caption(f"{len(res.messages)} A2A messages exchanged")
        for msg in res.messages[:25]:
            pc=RED if msg.priority<=2 else YELLOW if msg.priority<=4 else BLUE
            st.markdown(f'<div class="wcard-sm" style="font-family:\'JetBrains Mono\',monospace;font-size:11px;margin:3px 0;"><span style="color:{pc};">P{msg.priority}</span> <span style="color:var(--wmt-yellow);">{msg.from_agent.replace("Agent","")}</span> <span style="color:var(--tx-muted);">→ {msg.to_agent.replace("Agent","")}</span> <span style="color:var(--tx-muted);">[{msg.msg_type}]</span> {msg.msg_id}</div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📦  Inventory Intelligence":
    st.markdown('<div class="ph"><div class="pt">📦 Inventory Intelligence Center</div><div class="ps">Real-time stock monitoring · AI-driven replenishment · Overstock detection</div></div>',unsafe_allow_html=True)
    inv=engine.inventory; c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Total Records",f"{len(inv):,}"); c2.metric("🔴 Stockouts",f"{(inv['status']=='Stockout').sum():,}"); c3.metric("🟠 Critical",f"{(inv['status']=='Critical').sum():,}"); c4.metric("💰 Inv Value",f"${inv['inventory_value'].sum()/1e6:.1f}M"); c5.metric("⏱ Avg DOS",f"{inv['days_of_supply'].mean():.1f}d")
    st.markdown('<div class="sec">Stock Level Heatmap — Store × Department</div>',unsafe_allow_html=True)
    pivot=inv.pivot_table(values="on_hand_units",index="store_id",columns="department",aggfunc="sum",fill_value=0).head(25)
    figh=go.Figure(go.Heatmap(z=pivot.values,x=pivot.columns.tolist(),y=pivot.index.tolist(),colorscale=[[0,RED],[.25,YELLOW],[.6,BLUE],[1,GREEN]],hovertemplate="Store:%{y}<br>Dept:%{x}<br>Units:%{z}<extra></extra>"))
    _fig(figh,420); figh.update_layout(margin=dict(l=120,r=10,t=8,b=80)); st.plotly_chart(figh,use_container_width=True)
    cf1,cf2,cf3=st.columns(3)
    sf=cf1.multiselect("Status",inv["status"].unique().tolist(),default=["Stockout","Critical","Below Reorder"])
    rf=cf2.multiselect("Region",inv["region"].unique().tolist(),default=inv["region"].unique().tolist())
    dff=cf3.multiselect("Department",inv["department"].unique().tolist(),default=list(inv["department"].unique())[:3])
    filt=inv[inv["status"].isin(sf)&inv["region"].isin(rf)&inv["department"].isin(dff)]
    st.markdown(f'<div class="sec">Records — {len(filt):,} filtered</div>',unsafe_allow_html=True)
    st.dataframe(filt[["store_id","region","state","product_name","department","category","vendor_name","on_hand_units","reorder_point","days_of_supply","status","inventory_value","is_perishable"]].head(300),use_container_width=True,height=400)
    st.download_button("⬇️ Export CSV",filt.to_csv(index=False),"walmart_inventory.csv","text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# VENDOR RISK CENTER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🚚  Vendor Risk Center":
    st.markdown('<div class="ph"><div class="pt">🚚 Vendor Risk Intelligence Center</div><div class="ps">25-vendor ecosystem · SLA tracking · Delivery performance · Alternate sourcing</div></div>',unsafe_allow_html=True)
    vendors=engine.vendors; ve=engine.vendor_events
    c1,c2,c3,c4=st.columns(4); c1.metric("Active Vendors",len(vendors)); c2.metric("High/Critical Risk",f"{vendors['risk'].isin(['High','Critical']).sum()}"); c3.metric("Events 90d",f"{len(ve):,}"); c4.metric("Delay Events",f"{(ve['event_type']=='SHIPMENT_DELAYED').sum():,}")
    rd_=[]
    for _,v in vendors.iterrows():
        vev=ve[ve["vendor_id"]==v["id"]]; d=int((vev["event_type"]=="SHIPMENT_DELAYED").sum()); q=int((vev["event_type"]=="QUALITY_REJECTION").sum())
        score=min(100,int((1-float(v["otd_pct"]))*100)+d*3+q*7+random.randint(-4,8))
        rd_.append({"vendor":v["name"],"tier":int(v["tier"]),"score":score,"otd":round(float(v["otd_pct"])*100,1),"delays":d,"risk":v["risk"]})
    rd=pd.DataFrame(rd_)
    ca,cb=st.columns(2)
    with ca:
        figs=px.scatter(rd,x="delays",y="otd",size="score",color="risk",hover_name="vendor",color_discrete_map={"Low":GREEN,"Medium":BLUE,"High":YELLOW,"Critical":RED},labels={"delays":"Delay Events (90d)","otd":"On-Time %"})
        _fig(figs,300); figs.update_layout(title=dict(text="Vendor Risk Matrix",font=dict(size=12,color=AC))); st.plotly_chart(figs,use_container_width=True)
    with cb:
        rds=rd.sort_values("score",ascending=True)
        figb=go.Figure(go.Bar(x=rds["score"],y=rds["vendor"],orientation="h",marker_color=[RED if s>75 else YELLOW if s>50 else BLUE if s>25 else GREEN for s in rds["score"]]))
        figb.add_vline(x=50,line_dash="dash",line_color=YELLOW); figb.add_vline(x=75,line_dash="dash",line_color=RED); _fig(figb,300); figb.update_layout(margin=dict(l=165,r=10,t=8,b=8),title=dict(text="Risk Scores",font=dict(size=12,color=AC))); st.plotly_chart(figb,use_container_width=True)
    st.markdown('<div class="sec">Event Timeline — 90 Days</div>',unsafe_allow_html=True)
    ect=ve.groupby(["date","event_type"]).size().reset_index(name="count")
    figev=px.bar(ect.head(300),x="date",y="count",color="event_type",color_discrete_sequence=[BLUE,GREEN,YELLOW,RED,PURPLE,"#F97316"])
    _fig(figev,260); st.plotly_chart(figev,use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# DEMAND & FORECASTING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈  Demand & Forecasting":
    st.markdown('<div class="ph"><div class="pt">📈 Demand Intelligence & Forecasting</div><div class="ps">XGBoost + LightGBM + Prophet + DeepAR ensemble · Anomaly detection · Seasonal multipliers</div></div>',unsafe_allow_html=True)
    pos=engine.pos; signals=engine.demand_signals
    c1,c2,c3,c4=st.columns(4); c1.metric("Transactions",f"{len(pos):,}"); c2.metric("Anomalous Txns",f"{pos['is_anomaly'].sum():,}" if "is_anomaly" in pos.columns else "N/A"); c3.metric("Forecast Signals",f"{len(signals):,}"); c4.metric("Store-SKU Combos",f"{signals.groupby(['store_id','sku_id']).ngroups:,}")
    ca,cb=st.columns([2,1])
    with ca:
        daily=pos.groupby("date")["total_revenue"].sum().reset_index(); daily["date"]=pd.to_datetime(daily["date"]); ma7=daily["total_revenue"].rolling(7,min_periods=1).mean()
        fig=go.Figure(); fig.add_trace(go.Scatter(x=daily["date"],y=daily["total_revenue"],fill="tozeroy",fillcolor="rgba(0,113,206,.07)",line=dict(color=BLUE,width=1.5),name="Revenue",mode="lines")); fig.add_trace(go.Scatter(x=daily["date"],y=ma7,line=dict(color=YELLOW,width=2,dash="dot"),name="7d MA",mode="lines"))
        if "is_anomaly" in pos.columns:
            anom=pos[pos["is_anomaly"]].groupby("date")["total_revenue"].sum().reset_index(); anom["date"]=pd.to_datetime(anom["date"]); fig.add_trace(go.Scatter(x=anom["date"],y=anom["total_revenue"],mode="markers",name="Anomaly",marker=dict(color=RED,size=9,symbol="x")))
        fig.update_yaxes(tickprefix="$",tickformat=",.0f"); _fig(fig,290); fig.update_layout(title=dict(text="Revenue Trend + Anomaly Overlay",font=dict(size=12,color=AC))); st.plotly_chart(fig,use_container_width=True)
    with cb:
        ch=pos.groupby("channel")["total_revenue"].sum().reset_index()
        figch=go.Figure(go.Pie(labels=ch["channel"],values=ch["total_revenue"],hole=.52,marker_colors=[BLUE,"#005BAD",YELLOW,"#002D63",GREEN]))
        figch.update_traces(textfont_color="white",textfont_size=10); _fig(figch,290); figch.update_layout(title=dict(text="Revenue by Channel",font=dict(size=12,color=AC))); st.plotly_chart(figch,use_container_width=True)
    st.markdown('<div class="sec">14-Day Demand Forecast by Department</div>',unsafe_allow_html=True)
    fcast=signals.groupby(["forecast_date","department"])["forecast_units"].sum().reset_index()
    figfc=px.line(fcast,x="forecast_date",y="forecast_units",color="department",color_discrete_sequence=[BLUE,YELLOW,GREEN,RED,PURPLE,"#F97316","#14B8A6","#EC4899"])
    _fig(figfc,280); st.plotly_chart(figfc,use_container_width=True)
    cp,cq=st.columns(2)
    with cp:
        pay=pos.groupby("payment")["total_revenue"].sum().reset_index()
        figpay=go.Figure(go.Bar(x=pay["payment"],y=pay["total_revenue"],marker_color=[BLUE,YELLOW,GREEN,PURPLE,RED,"#F97316","#14B8A6"]))
        figpay.update_yaxes(tickprefix="$",tickformat=",.0f"); _fig(figpay,240); figpay.update_layout(title=dict(text="Revenue by Payment Method",font=dict(size=12,color=AC))); st.plotly_chart(figpay,use_container_width=True)
    with cq:
        dow=pos.groupby("day_of_week")["total_revenue"].mean().reset_index()
        figdow=go.Figure(go.Bar(x=dow["day_of_week"],y=dow["total_revenue"],marker_color=BLUE))
        figdow.update_yaxes(tickprefix="$",tickformat=",.0f"); _fig(figdow,240); figdow.update_layout(title=dict(text="Avg Revenue by Day of Week",font=dict(size=12,color=AC))); st.plotly_chart(figdow,use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PRICING INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💲  Pricing Intelligence":
    st.markdown('<div class="ph"><div class="pt">💲 Pricing Intelligence & Promotion Analytics</div><div class="ps">Competitive monitoring · Elasticity modeling · Markdown optimization · AI recommendations</div></div>',unsafe_allow_html=True)
    pricing=engine.pricing; c1,c2,c3,c4=st.columns(4); c1.metric("SKUs Monitored",f"{len(pricing):,}"); c2.metric("Active Promos",f"{pricing['promo_active'].sum():,}"); c3.metric("Price Gaps >4%",f"{(abs(pricing['price_gap_pct'])>4).sum():,}"); c4.metric("Avg Elasticity",f"{pricing['price_elasticity'].mean():.2f}")
    ca,cb=st.columns(2)
    with ca:
        acts=pricing["recommended_action"].value_counts().reset_index(); acts.columns=["action","count"]
        figact=go.Figure(go.Bar(x=acts["action"],y=acts["count"],marker_color=[BLUE,YELLOW,GREEN,PURPLE,RED,"#F97316"]))
        _fig(figact,280); figact.update_xaxes(tickangle=-25); figact.update_layout(title=dict(text="AI Pricing Recommendations",font=dict(size=12,color=AC))); st.plotly_chart(figact,use_container_width=True)
    with cb:
        figel=px.histogram(pricing,x="price_elasticity",nbins=30,color_discrete_sequence=[BLUE])
        _fig(figel,280); figel.update_layout(title=dict(text="Price Elasticity Distribution",font=dict(size=12,color=AC))); st.plotly_chart(figel,use_container_width=True)
    st.markdown('<div class="sec">Competitive Price Gap Analysis — Top 25</div>',unsafe_allow_html=True)
    gap=pricing[abs(pricing["price_gap_pct"])>4].nlargest(25,"price_gap_pct")
    st.dataframe(gap[["product_name","department","category","current_price","competitor_a_price","price_gap_pct","recommended_action","ai_confidence"]],use_container_width=True,height=360)


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSATIONAL AI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬  Conversational AI":
    st.markdown('<div class="ph"><div class="pt">💬 Enterprise Conversational AI</div><div class="ps">RAG-grounded · Pinecone + Neo4j retrieval · Citation-sourced · Multi-turn memory · ReAct reasoning</div></div>',unsafe_allow_html=True)
    if not st.session_state.pipeline:
        st.warning("⚠️ Run the **🤖 Agent Orchestration** pipeline first to initialize the conversational knowledge context."); st.stop()
    SUGGS=["What is our current stockout situation across all regions?","Which vendors have the highest supply risk this week?","Give me a 14-day demand forecast summary.","What pricing actions should we take immediately?","Summarize all critical alerts for executive review.","Which DCs are approaching capacity limits?","Status of emergency replenishment POs?","Show me the overstock analysis and markdown plan."]
    st.markdown('<div class="sec">Suggested Queries</div>',unsafe_allow_html=True)
    cols=st.columns(4)
    for i,sug in enumerate(SUGGS):
        with cols[i%4]:
            if st.button(f"💬 {sug[:35]}…",key=f"s{i}"):
                st.session_state.chat_hist.append({"role":"user","content":sug})
                with st.spinner("🧠 Multi-agent reasoning…"): resp=ORC.chat(sug)
                st.session_state.chat_hist.append({"role":"ai","content":resp}); st.rerun()
    st.markdown('<div class="sec">Conversation</div>',unsafe_allow_html=True)
    for msg in st.session_state.chat_hist:
        if msg["role"]=="user":
            st.markdown(f'<div class="ccon"><div class="cu">👤 {msg["content"]}</div></div>',unsafe_allow_html=True)
        else:
            resp=msg["content"]; cit='<div class="cc">📚 '+"&nbsp;·&nbsp;".join(resp.get("citations",[]))+"</div>" if resp.get("citations") else ""; meta=resp.get("llm_metadata",{})
            st.markdown(f'<div class="ccon"><div class="ca"><div style="font-size:9.5px;color:var(--tx-muted);margin-bottom:7px;">🤖 {meta.get("model","claude-3-5-sonnet")} · {meta.get("tokens_in",0)+meta.get("tokens_out",0):,} tokens · {meta.get("latency_ms",0)}ms · conf:{resp.get("confidence",0):.3f}</div>{resp["response"].replace(chr(10),"<br/>")}{cit}</div></div>',unsafe_allow_html=True)
            with st.expander("🔍 ReAct Reasoning Trace"):
                for step in resp.get("react_trace",[]): 
                    cls={"THOUGHT":"tt","ACTION":"ta","OBSERVATION":"to","FINAL":"tf"}.get(step["step"],"ts")
                    st.markdown(f'<div class="ts {cls}"><b>[{step["step"]}]</b> {step["content"]}</div>',unsafe_allow_html=True)
                if resp.get("rag_docs"):
                    st.markdown("**Retrieved KB Documents:**")
                    for doc in resp["rag_docs"]: st.markdown(f"📄 **{doc['title']}** (relevance: {doc['relevance']})"); st.caption(doc["excerpt"])
    st.markdown("---")
    with st.form("chat_f",clear_on_submit=True):
        ci,cs=st.columns([5,1]); uq=ci.text_input("",placeholder="Ask about inventory, vendors, demand, pricing, DC operations…",label_visibility="collapsed"); go_=cs.form_submit_button("Send →")
    if go_ and uq.strip():
        st.session_state.chat_hist.append({"role":"user","content":uq})
        with st.spinner("🧠 Reasoning…"): resp=ORC.chat(uq)
        st.session_state.chat_hist.append({"role":"ai","content":resp}); st.rerun()
    if st.button("🗑️ Clear"): st.session_state.chat_hist=[]; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# AI OBSERVABILITY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔭  AI Observability":
    st.markdown('<div class="ph"><div class="pt">🔭 AI Observability — LLMOps</div><div class="ps">Prometheus · Grafana · LangSmith-style traces · Per-agent token accounting · Hallucination monitoring</div></div>',unsafe_allow_html=True)
    obs=engine.observability; c1,c2,c3,c4=st.columns(4)
    c1.metric("Avg P50 Latency",f"{obs['p50_latency_ms'].mean():.0f}ms"); c2.metric("Avg P99 Latency",f"{obs['p99_latency_ms'].mean():.0f}ms"); c3.metric("Avg Hallucination",f"{obs['hallucination_rate'].mean():.2%}"); c4.metric("Total Cost 72h",f"${obs['cost_usd'].sum():.3f}")
    by_agent=obs.groupby("agent_name").agg({"avg_latency_ms":"mean","p99_latency_ms":"mean","accuracy_score":"mean","hallucination_rate":"mean","cost_usd":"sum","tokens_in":"sum","tokens_out":"sum","errors_count":"sum","calls_per_interval":"sum"}).reset_index()
    ca,cb=st.columns(2)
    with ca:
        figl=go.Figure(); figl.add_trace(go.Bar(x=by_agent["agent_name"],y=by_agent["avg_latency_ms"],name="P50",marker_color=BLUE)); figl.add_trace(go.Bar(x=by_agent["agent_name"],y=by_agent["p99_latency_ms"],name="P99",marker_color=YELLOW,opacity=0.6))
        _fig(figl,300); figl.update_xaxes(tickangle=-30); figl.update_yaxes(ticksuffix="ms"); figl.update_layout(barmode="overlay",title=dict(text="Latency P50 vs P99",font=dict(size=12,color=AC))); st.plotly_chart(figl,use_container_width=True)
    with cb:
        figa=go.Figure(); figa.add_trace(go.Bar(x=by_agent["agent_name"],y=by_agent["accuracy_score"]*100,name="Accuracy %",marker_color=GREEN)); figa.add_trace(go.Bar(x=by_agent["agent_name"],y=by_agent["hallucination_rate"]*100,name="Hallucination %",marker_color=RED))
        _fig(figa,300); figa.update_xaxes(tickangle=-30); figa.update_yaxes(ticksuffix="%"); figa.update_layout(barmode="group",title=dict(text="Accuracy vs Hallucination",font=dict(size=12,color=AC))); st.plotly_chart(figa,use_container_width=True)
    st.markdown('<div class="sec">Latency Time Series — 72h</div>',unsafe_allow_html=True)
    tss=obs[obs["agent_name"].isin(["DemandForecastAgent","ExecutiveInsightAgent","ConversationalAgent"])]
    figts=px.line(tss.reset_index(),x="index",y="avg_latency_ms",color="agent_name",color_discrete_sequence=[BLUE,YELLOW,GREEN])
    _fig(figts,240); figts.update_yaxes(ticksuffix="ms"); st.plotly_chart(figts,use_container_width=True)
    st.markdown('<div class="sec">Per-Agent Cost & Token Accounting</div>',unsafe_allow_html=True)
    cdf=by_agent[["agent_name","calls_per_interval","tokens_in","tokens_out","cost_usd","errors_count"]].copy(); cdf["cost_usd"]=cdf["cost_usd"].round(5); cdf.columns=["Agent","Calls","Tokens In","Tokens Out","Cost USD","Errors"]; st.dataframe(cdf,use_container_width=True,height=280)


# ══════════════════════════════════════════════════════════════════════════════
# ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏗️  Architecture":
    st.markdown('<div class="ph"><div class="pt">🏗️ System Architecture</div><div class="ps">10-layer enterprise stack · Full technology inventory · Data flow diagram</div></div>',unsafe_allow_html=True)
    LAYERS=[("#002D63","Layer 1 — Data Ingestion",["POS Streams","Vendor EDI/API","IoT Telemetry","HL7/EDI","Batch ETL"]),("#003F8A","Layer 2 — Streaming Engine",["Apache Kafka (64 partitions)","Redpanda","Stream Consumers","Event Topics","Dead-Letter Queue"]),("#004DA0","Layer 3 — Batch Processing",["PySpark Jobs","Delta Lake","Snowflake","Amazon Redshift","Apache Airflow"]),("#005BAD","Layer 4 — AI Orchestration",["LangGraph Engine","7 Specialized Agents","A2A Messaging","HITL Gates","Decision Fusion"]),("#0071CE","Layer 5 — Vector & Graph RAG",["Pinecone (semantic)","FAISS (ANN)","Neo4j (Graph)","Milvus (multi-modal)","Embedding Models"]),("#1A80D9","Layer 6 — LLM Runtime",["Amazon Bedrock","Claude 3.5 Sonnet","Claude 3 Haiku","CoT + ReAct","Structured Outputs"]),("#3391E0","Layer 7 — API Gateway",["FastAPI Microservices","WebSocket Streaming","REST APIs","IAM + JWT Auth","Rate Limiting"]),("#4DA2E8","Layer 8 — Frontend",["Streamlit Dashboard","10 Operational Pages","Real-time Plotly","Agent Visualizer","Conversational AI"]),("#66B3EE","Layer 9 — Observability",["Prometheus","Grafana","LangSmith Traces","Token Accounting","SHAP Explainability"]),("#80C4F5","Layer 10 — Infrastructure",["Docker","Kubernetes / EKS","Terraform IaC","GitHub Actions CI/CD","Multi-Cloud AWS+GCP"])]
    for color,label,comps in LAYERS:
        chips="".join(f'<span style="background:rgba(255,255,255,.12);padding:3px 10px;border-radius:12px;font-size:11px;margin:3px;display:inline-block;">{c}</span>' for c in comps)
        st.markdown(f'<div style="background:{color};border-radius:10px;padding:13px 18px;margin:4px 0;"><div style="font-size:11.5px;font-weight:700;color:rgba(255,255,255,.9);margin-bottom:7px;">{label}</div><div>{chips}</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="sec">Data Flow</div>',unsafe_allow_html=True)
    st.markdown('<div class="wcard" style="font-family:\'JetBrains Mono\',monospace;font-size:11.5px;line-height:2.4;color:var(--tx-secondary);">POS / IoT / Vendor feeds → Apache Kafka (64 partitions) → Stream consumers<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br/>PySpark batch jobs → Delta Lake → Snowflake + Redshift lakehouse<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br/>LangGraph Orchestrator → 7-Agent parallel execution graph<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br/>RAG (Pinecone + Neo4j + FAISS) + LLM (Claude via Bedrock)<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br/>Decisions / Alerts → FastAPI → WebSocket → Dashboard → End Users<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓<br/>Prometheus + Grafana + LangSmith → Observability feedback loop</div>',unsafe_allow_html=True)
    st.markdown('<div class="sec">Data Scale</div>',unsafe_allow_html=True)
    summ=engine.summary(); scale=[("Stores",f"{summ.get('stores',0):,}","4,200 across 50 states"),("SKUs",f"{summ.get('skus',0):,}","8 departments, 60+ subcategories"),("POS Transactions",f"{summ.get('pos_transactions',0):,}","90-day history"),("Inventory Records",f"{summ.get('inventory_records',0):,}","store × SKU combos"),("Vendor Events",f"{summ.get('vendor_events',0):,}","25 vendors, 10 event types"),("DC Telemetry",f"{summ.get('telemetry_records',0):,}","48h, 15-min intervals"),("Demand Signals",f"{summ.get('demand_signals',0):,}","14-day forward forecasts"),("Agent Decisions",f"{summ.get('agent_decisions',0):,}","historical AI decisions")]
    cx,cy=st.columns(2)
    for i,(label,val,desc) in enumerate(scale):
        with (cx if i<4 else cy): st.markdown(f'<div style="display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--border);"><span style="font-size:12px;color:var(--tx-secondary);">{label}</span><span style="font-size:13px;font-weight:700;color:var(--wmt-yellow);">{val}</span><span style="font-size:11px;color:var(--tx-muted);">{desc}</span></div>',unsafe_allow_html=True)
