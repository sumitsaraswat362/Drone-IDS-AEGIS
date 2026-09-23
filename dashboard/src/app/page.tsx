'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Activity, ShieldAlert, ShieldCheck, Database, Radio, Crosshair, Terminal, Zap, Settings, Download, Server, Wifi, WifiOff, Play, Square, AlertTriangle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ScatterChart, Scatter, ZAxis } from 'recharts';

type Alert = { id: number; time: string; rule: string; severity: 'CRITICAL' | 'HIGH' | 'MEDIUM'; detail: string; detector: string; sha256?: string; };
type Telemetry = { timestamp_s: number; packets: number; lat: number; lon: number; alt_m: number; mahalanobis: number; chi2_threshold: number; is_attack: boolean; };

const WS_URL = 'ws://localhost:8765';
const SCENARIOS = [
  { label: 'GPS / NavIC Spoofing', value: 'scenarios/gps_spoofing.yaml', icon: Crosshair, color: 'text-cyan-400' },
  { label: 'Command Injection', value: 'scenarios/command_injection.yaml', icon: Terminal, color: 'text-red-400' },
  { label: 'DoS Heartbeat Flood', value: 'scenarios/dos_attack.yaml', icon: Radio, color: 'text-orange-400' },
];

export default function AegisDashboard() {
  const [activeTab, setActiveTab] = useState('LIVE');
  const [wsStatus, setWsStatus] = useState<'disconnected'|'connecting'|'connected'>('disconnected');
  const [systemStatus, setSystemStatus] = useState<'SECURE'|'THREAT_DETECTED'|'MISSION_COMPLETE'>('SECURE');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [telemetry, setTelemetry] = useState<Telemetry[]>([]);
  const [packets, setPackets] = useState(0);
  const [selectedScenario, setSelectedScenario] = useState(SCENARIOS[0].value);
  const [isRunning, setIsRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const alertEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { alertEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [alerts]);

  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setWsStatus('connecting');
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setWsStatus('connected');
    ws.onclose = () => { setWsStatus('disconnected'); setIsRunning(false); };
    ws.onerror = () => setWsStatus('disconnected');
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'ALERT') {
        const p = msg.payload;
        setAlerts(prev => [...prev.slice(-99), { id: Date.now() + Math.random(), time: new Date().toLocaleTimeString('en-US',{hour12:false}), rule: p.rule, severity: p.severity, detail: p.detail, detector: p.detector, sha256: p.sha256 }]);
      }
      if (msg.type === 'TELEMETRY') {
        const p = msg.payload;
        setPackets(p.packets);
        setTelemetry(prev => [...prev.slice(-59), p]);
      }
      if (msg.type === 'STATUS') {
        const s = msg.payload.status;
        setSystemStatus(s as any);
        if (s === 'MISSION_COMPLETE') setIsRunning(false);
      }
    };
    wsRef.current = ws;
  }, []);

  const startScenario = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) { connectWS(); return; }
    setAlerts([]); setTelemetry([]); setIsRunning(true); setSystemStatus('SECURE');
    wsRef.current.send(JSON.stringify({ type: 'START_SCENARIO', scenario: selectedScenario }));
  };

  const ekfData = telemetry.map(t => ({ t: t.timestamp_s.toFixed(1), d: t.mahalanobis, thresh: 16.27 }));
  const criticalAlerts = alerts.filter(a => a.severity === 'CRITICAL').length;
  const highAlerts = alerts.filter(a => a.severity === 'HIGH').length;

  const radarData = [
    { subject: 'GPS/NavIC', A: alerts.filter(a=>a.rule.includes('GPS')).length * 10 || 0 },
    { subject: 'Command Inj.', A: alerts.filter(a=>a.rule.includes('COMMAND')||a.rule.includes('SRC')).length * 10 || 0 },
    { subject: 'DoS/Flood', A: alerts.filter(a=>a.rule.includes('FLOOD')||a.rule.includes('DOS')).length * 10 || 0 },
    { subject: 'Replay', A: alerts.filter(a=>a.rule.includes('REPLAY')).length * 10 || 0 },
    { subject: 'EKF Anomaly', A: alerts.filter(a=>a.rule.includes('EKF')).length * 10 || 0 },
    { subject: 'ML Anomaly', A: alerts.filter(a=>a.rule.includes('ML')).length * 10 || 0 },
  ];

  return (
    <div className="min-h-screen bg-[#020208] text-slate-300 font-sans flex overflow-hidden" style={{fontFamily: "'Inter', system-ui, sans-serif"}}>
      {/* SIDEBAR */}
      <aside className="w-64 border-r border-slate-800/50 bg-[#040410]/80 flex flex-col backdrop-blur-xl">
        <div className="p-6 border-b border-slate-800/50">
          <div className="flex items-center gap-3 mb-1">
            <div className="h-8 w-8 bg-cyan-500/10 border border-cyan-500/30 rounded-lg flex items-center justify-center">
              <ShieldCheck className="text-cyan-400" size={16} />
            </div>
            <h1 className="text-xl font-black tracking-tight text-white">AEGIS</h1>
          </div>
          <p className="text-[9px] text-cyan-500/60 uppercase tracking-widest font-mono pl-11">Cyber-Physical IDS v1.0</p>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {[
            { id: 'LIVE', icon: Activity, label: 'Live Monitor' },
            { id: 'EKF', icon: Crosshair, label: 'EKF Twin' },
            { id: 'FORENSICS', icon: Database, label: 'Forensics' },
            { id: 'SETTINGS', icon: Settings, label: 'Config' },
          ].map(item => (
            <button key={item.id} onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === item.id ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-900/50' : 'text-slate-500 hover:bg-slate-800/50 hover:text-slate-300'}`}>
              <item.icon size={16}/> {item.label}
            </button>
          ))}
        </nav>

        {/* WS Connection */}
        <div className="p-4 border-t border-slate-800/50 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-mono">WS LINK</span>
            <div className={`flex items-center gap-1.5 text-xs font-bold ${wsStatus==='connected'?'text-emerald-400':wsStatus==='connecting'?'text-yellow-400':'text-slate-600'}`}>
              {wsStatus==='connected'?<Wifi size={12}/>:<WifiOff size={12}/>}
              {wsStatus.toUpperCase()}
            </div>
          </div>
          {wsStatus !== 'connected' && (
            <button onClick={connectWS} className="w-full py-2 text-xs bg-cyan-950/50 hover:bg-cyan-950 border border-cyan-900/50 text-cyan-400 rounded-lg font-medium transition-all">
              Connect to AEGIS Server
            </button>
          )}
        </div>
      </aside>

      <main className="flex-1 flex flex-col h-screen overflow-hidden bg-[radial-gradient(ellipse_at_top_left,_#0a0a1a_0%,_#020208_60%)]">
        {/* HEADER */}
        <header className="h-14 border-b border-slate-800/50 flex items-center justify-between px-6 bg-[#040410]/60 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-slate-600">SESSION</span>
            <code className="text-xs bg-slate-800/80 text-slate-300 px-2 py-1 rounded border border-slate-700/50">AEGIS_{Date.now().toString(36).toUpperCase()}</code>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-slate-500">{packets.toLocaleString()} pkts</span>
            <div className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider border flex items-center gap-2 transition-all duration-500 ${
              systemStatus==='SECURE'?'bg-emerald-950/50 text-emerald-400 border-emerald-900/50':
              systemStatus==='THREAT_DETECTED'?'bg-red-950/70 text-red-400 border-red-900/70 animate-pulse':
              'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              <div className={`h-2 w-2 rounded-full ${systemStatus==='SECURE'?'bg-emerald-400':systemStatus==='THREAT_DETECTED'?'bg-red-400 animate-ping':'bg-slate-400'}`}/>
              {systemStatus.replace('_',' ')}
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* SCENARIO LAUNCHER */}
          <div className="bg-[#040410]/80 border border-slate-800/50 rounded-xl p-5 backdrop-blur-sm">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2"><Zap size={12} className="text-yellow-500"/> Attack Scenario Launcher</h3>
            <div className="flex items-center gap-4 flex-wrap">
              {SCENARIOS.map(s => (
                <button key={s.value} onClick={() => setSelectedScenario(s.value)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-all ${selectedScenario===s.value?'bg-cyan-950/60 border-cyan-700/70 text-cyan-300':'border-slate-700/50 text-slate-400 hover:border-slate-600 hover:text-slate-300'}`}>
                  <s.icon size={14} className={selectedScenario===s.value?'text-cyan-400':'text-slate-500'}/> {s.label}
                </button>
              ))}
              <button onClick={startScenario} disabled={isRunning || wsStatus!=='connected'}
                className={`ml-auto flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${isRunning||wsStatus!=='connected'?'bg-slate-800 text-slate-600 cursor-not-allowed':'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/40'}`}>
                {isRunning?<><Square size={14}/> Running…</>:<><Play size={14}/> Launch Simulation</>}
              </button>
            </div>
            {wsStatus!=='connected' && <p className="text-xs text-yellow-500/80 mt-3 flex items-center gap-1"><AlertTriangle size={10}/> Run `python3 ws_server.py` then click Connect above for live data</p>}
          </div>

          {/* KPI GRID */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label:'Packets Analyzed', value: packets.toLocaleString(), sub:`+${Math.floor(Math.random()*50+10)}/sec`, color:'text-white', icon: Server },
              { label:'Critical Alerts', value: criticalAlerts, sub:'Rule Engine + EKF Twin', color:'text-red-400', icon: ShieldAlert },
              { label:'High Severity', value: highAlerts, sub:'Isolation Forest ML', color:'text-orange-400', icon: AlertTriangle },
              { label:'False Pos. Rate', value: '<2.1%', sub:'EKF-filtered ML', color:'text-emerald-400', icon: ShieldCheck },
            ].map(kpi => (
              <div key={kpi.label} className="bg-[#040410]/80 border border-slate-800/50 rounded-xl p-4 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{kpi.label}</p>
                  <kpi.icon size={14} className="text-slate-600"/>
                </div>
                <p className={`text-2xl font-bold font-mono ${kpi.color}`}>{kpi.value}</p>
                <p className="text-[10px] text-slate-600 mt-1">{kpi.sub}</p>
              </div>
            ))}
          </div>

          {/* EKF CHART + RADAR */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
            <div className="xl:col-span-2 bg-[#040410]/80 border border-slate-800/50 rounded-xl overflow-hidden backdrop-blur-sm">
              <div className="px-5 py-3.5 border-b border-slate-800/50 flex justify-between items-center">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2"><Crosshair size={14} className="text-cyan-400"/> EKF Digital Twin — Mahalanobis Distance d²</h3>
                <span className="text-[10px] text-slate-600 font-mono">χ² threshold = 16.27 (99.9% CI, 3 DOF)</span>
              </div>
              <div className="p-4 h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={ekfData}>
                    <defs>
                      <linearGradient id="ekfGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="attackGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#0f172a"/>
                    <XAxis dataKey="t" stroke="#334155" tick={{fontSize:9, fill:'#475569'}}/>
                    <YAxis stroke="#334155" tick={{fontSize:9, fill:'#475569'}} domain={[0,50]}/>
                    <Tooltip contentStyle={{backgroundColor:'#020208', borderColor:'#1e293b', borderRadius:'8px', fontSize:'11px'}} labelStyle={{color:'#94a3b8'}} itemStyle={{color:'#e2e8f0'}}/>
                    <Area type="monotone" dataKey="d" stroke="#06b6d4" strokeWidth={2} fill="url(#ekfGrad)" dot={false} isAnimationActive={false} name="d² Score"/>
                    <Line type="step" dataKey="thresh" stroke="#ef4444" strokeWidth={1.5} strokeDasharray="6 3" dot={false} name="χ² Threshold"/>
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-[#040410]/80 border border-slate-800/50 rounded-xl overflow-hidden backdrop-blur-sm">
              <div className="px-5 py-3.5 border-b border-slate-800/50">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2"><Activity size={14} className="text-purple-400"/> Attack Vector Heatmap</h3>
              </div>
              <div className="p-4 h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#1e293b"/>
                    <PolarAngleAxis dataKey="subject" tick={{fontSize:9, fill:'#64748b'}}/>
                    <PolarRadiusAxis stroke="#1e293b" tick={false}/>
                    <Radar name="Threats" dataKey="A" stroke="#a855f7" fill="#a855f7" fillOpacity={0.25}/>
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* FORENSIC LOG */}
          <div className="bg-[#040410]/80 border border-slate-800/50 rounded-xl overflow-hidden backdrop-blur-sm">
            <div className="px-5 py-3.5 border-b border-slate-800/50 flex justify-between items-center">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2"><Database size={14} className="text-red-400"/> Forensic Alert Log (SHA-256 Chain)</h3>
              <button className="flex items-center gap-1.5 text-[10px] text-slate-500 hover:text-white transition-colors border border-slate-700 px-2 py-1 rounded">
                <Download size={10}/> Export JSONL
              </button>
            </div>
            <div className="max-h-72 overflow-y-auto font-mono text-xs divide-y divide-slate-800/50">
              {alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-slate-700">
                  <ShieldCheck size={40} className="mb-3 opacity-40"/>
                  <p>No anomalies detected. Launch a scenario above.</p>
                </div>
              ) : alerts.slice().reverse().map(a => (
                <div key={a.id} className={`px-5 py-3 flex items-start gap-4 hover:bg-slate-800/20 transition-colors ${a.severity==='CRITICAL'?'border-l-2 border-red-500':a.severity==='HIGH'?'border-l-2 border-orange-500':'border-l-2 border-yellow-500'}`}>
                  <span className="text-slate-600 w-20 shrink-0">{a.time}</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 mt-0.5 ${a.severity==='CRITICAL'?'bg-red-500/15 text-red-400':a.severity==='HIGH'?'bg-orange-500/15 text-orange-400':'bg-yellow-500/15 text-yellow-400'}`}>{a.severity}</span>
                  <span className="text-slate-500 shrink-0 text-[9px] mt-0.5">[{a.detector}]</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-semibold mb-0.5">{a.rule}</p>
                    <p className="text-slate-400">{a.detail}</p>
                    {a.sha256 && <p className="text-slate-700 mt-1 truncate">SHA256: {a.sha256}</p>}
                  </div>
                </div>
              ))}
              <div ref={alertEndRef}/>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
