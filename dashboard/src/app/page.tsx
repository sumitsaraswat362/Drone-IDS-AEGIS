'use client';
import { useState, useEffect, useRef } from 'react';
import { Activity, ShieldAlert, ShieldCheck, Database, Radio, Crosshair, Terminal, Zap, Settings, Download, Server, Play, Square, AlertTriangle, FileJson } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';

type Alert = { id: number; time: string; rule: string; severity: 'CRITICAL' | 'HIGH' | 'MEDIUM'; detail: string; detector: string; sha256?: string; };
type Telemetry = { timestamp_s: number; packets: number; lat: number; lon: number; alt_m: number; mahalanobis: number; chi2_threshold: number; is_attack: boolean; };

const SCENARIOS = [
  { label: 'GPS / NavIC Spoofing', value: 'gps', icon: Crosshair, color: 'text-cyan-400' },
  { label: 'Command Injection', value: 'cmd', icon: Terminal, color: 'text-red-400' },
  { label: 'DoS Heartbeat Flood', value: 'dos', icon: Radio, color: 'text-orange-400' },
];

export default function AegisDashboard() {
  const [activeTab, setActiveTab] = useState('LIVE');
  const [systemStatus, setSystemStatus] = useState<'SECURE'|'THREAT_DETECTED'|'MISSION_COMPLETE'>('SECURE');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [telemetry, setTelemetry] = useState<Telemetry[]>([]);
  const [packets, setPackets] = useState(0);
  const [selectedScenario, setSelectedScenario] = useState(SCENARIOS[0].value);
  const [isRunning, setIsRunning] = useState(false);
  
  const alertEndRef = useRef<HTMLDivElement>(null);

  // In-browser Simulation Engine (replaces WebSocket for Vercel deployment)
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRunning) {
      let pktCount = 0;
      let tick = 0;
      let attackActive = false;
      
      interval = setInterval(() => {
        tick++;
        pktCount += Math.floor(Math.random() * 20) + 10;
        setPackets(pktCount);
        
        // Scenario timeline
        if (tick === 5) {
          attackActive = true;
          setSystemStatus('THREAT_DETECTED');
          
          let newAlert: Alert;
          if (selectedScenario === 'gps') {
             newAlert = { id: Date.now(), time: new Date().toLocaleTimeString('en-US',{hour12:false}), rule: 'EKF_DIGITAL_TWIN_ANOMALY', severity: 'CRITICAL', detail: 'Mahalanobis distance 24.3 > 16.27. NavIC/GPS spoofing highly probable. Physics envelope violated.', detector: 'EKF_DIGITAL_TWIN', sha256: Math.random().toString(36).substring(2,15) };
          } else if (selectedScenario === 'dos') {
             newAlert = { id: Date.now(), time: new Date().toLocaleTimeString('en-US',{hour12:false}), rule: 'R4_HEARTBEAT_FLOOD', severity: 'HIGH', detail: '80 heartbeats in 1.0s (threshold: 10). MAVLink bus saturated.', detector: 'RULE_ENGINE', sha256: Math.random().toString(36).substring(2,15) };
          } else {
             newAlert = { id: Date.now(), time: new Date().toLocaleTimeString('en-US',{hour12:false}), rule: 'R5_UNKNOWN_SRC_COMMAND', severity: 'CRITICAL', detail: 'COMMAND_LONG (id=21 LAND) injected from unknown system_id=99.', detector: 'RULE_ENGINE', sha256: Math.random().toString(36).substring(2,15) };
          }
          setAlerts(prev => [...prev.slice(-99), newAlert]);
        }
        
        if (tick === 15) {
          attackActive = false;
          setSystemStatus('SECURE');
        }
        
        if (tick === 20) {
          setSystemStatus('MISSION_COMPLETE');
          setIsRunning(false);
          clearInterval(interval);
        }

        // Generate telemetry frame
        const isGpsSpoof = attackActive && selectedScenario === 'gps';
        const mDist = isGpsSpoof ? Math.random() * 15 + 18 : Math.random() * 5 + 2;
        
        setTelemetry(prev => [...prev.slice(-59), {
          timestamp_s: tick, packets: pktCount, lat: 19.1334, lon: 72.9133, alt_m: 50 + (Math.random()*2-1),
          mahalanobis: mDist, chi2_threshold: 16.27, is_attack: attackActive
        }]);

      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRunning, selectedScenario]);

  useEffect(() => { alertEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [alerts]);

  const startScenario = () => {
    setAlerts([]); setTelemetry([]); setIsRunning(true); setSystemStatus('SECURE'); setPackets(0);
  };

  const ekfData = telemetry.map(t => ({ t: t.timestamp_s, d: parseFloat(t.mahalanobis.toFixed(2)), thresh: 16.27 }));
  const criticalAlerts = alerts.filter(a => a.severity === 'CRITICAL').length;
  const highAlerts = alerts.filter(a => a.severity === 'HIGH').length;

  const radarData = [
    { subject: 'GPS/NavIC', A: alerts.filter(a=>a.rule.includes('GPS')||a.rule.includes('EKF')).length * 10 || 0 },
    { subject: 'Command Inj.', A: alerts.filter(a=>a.rule.includes('COMMAND')||a.rule.includes('SRC')).length * 10 || 0 },
    { subject: 'DoS/Flood', A: alerts.filter(a=>a.rule.includes('FLOOD')||a.rule.includes('DOS')).length * 10 || 0 },
    { subject: 'Replay', A: alerts.filter(a=>a.rule.includes('REPLAY')).length * 10 || 0 },
    { subject: 'EKF Anomaly', A: alerts.filter(a=>a.rule.includes('EKF')).length * 10 || 0 },
    { subject: 'ML Anomaly', A: alerts.filter(a=>a.rule.includes('ML')).length * 10 || 0 },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'LIVE':
        return (
          <div className="space-y-5 animate-in fade-in duration-300">
            {/* SCENARIO LAUNCHER */}
            <div className="bg-[#040410]/80 border border-slate-800/50 rounded-xl p-5 backdrop-blur-sm">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2"><Zap size={12} className="text-yellow-500"/> Attack Scenario Launcher</h3>
              <div className="flex items-center gap-4 flex-wrap">
                {SCENARIOS.map(s => (
                  <button key={s.value} onClick={() => setSelectedScenario(s.value)} disabled={isRunning}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-all ${selectedScenario===s.value?'bg-cyan-950/60 border-cyan-700/70 text-cyan-300':'border-slate-700/50 text-slate-400 hover:border-slate-600 hover:text-slate-300'} ${isRunning ? 'opacity-50 cursor-not-allowed' : ''}`}>
                    <s.icon size={14} className={selectedScenario===s.value?'text-cyan-400':'text-slate-500'}/> {s.label}
                  </button>
                ))}
                <button onClick={startScenario} disabled={isRunning}
                  className={`ml-auto flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${isRunning?'bg-slate-800 text-slate-600 cursor-not-allowed':'bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/40'}`}>
                  {isRunning?<><Square size={14}/> Simulation Running…</>:<><Play size={14}/> Launch Simulation</>}
                </button>
              </div>
            </div>

            {/* KPI GRID */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label:'Packets Analyzed', value: packets.toLocaleString(), sub: isRunning ? `+${Math.floor(Math.random()*50+10)}/sec` : '0/sec', color:'text-white', icon: Server },
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

            {/* RADAR & QUICK LOG */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
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

              <div className="xl:col-span-2 bg-[#040410]/80 border border-slate-800/50 rounded-xl overflow-hidden backdrop-blur-sm">
                <div className="px-5 py-3.5 border-b border-slate-800/50 flex justify-between items-center">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2"><Database size={14} className="text-red-400"/> Recent Alerts</h3>
                </div>
                <div className="h-52 overflow-y-auto font-mono text-xs divide-y divide-slate-800/50">
                  {alerts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-slate-700">
                      <ShieldCheck size={32} className="mb-2 opacity-40"/>
                      <p>No anomalies detected.</p>
                    </div>
                  ) : alerts.slice().reverse().map(a => (
                    <div key={a.id} className={`px-4 py-2 flex items-start gap-3 hover:bg-slate-800/20 transition-colors ${a.severity==='CRITICAL'?'border-l-2 border-red-500':a.severity==='HIGH'?'border-l-2 border-orange-500':'border-l-2 border-yellow-500'}`}>
                      <span className="text-slate-600 w-16 shrink-0">{a.time}</span>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ${a.severity==='CRITICAL'?'bg-red-500/15 text-red-400':a.severity==='HIGH'?'bg-orange-500/15 text-orange-400':'bg-yellow-500/15 text-yellow-400'}`}>{a.severity}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-white font-semibold">{a.rule}</p>
                        <p className="text-slate-400">{a.detail}</p>
                      </div>
                    </div>
                  ))}
                  <div ref={alertEndRef}/>
                </div>
              </div>
            </div>
          </div>
        );
      case 'EKF':
        return (
          <div className="space-y-5 animate-in fade-in duration-300 h-full flex flex-col">
            <div className="bg-[#040410]/80 border border-slate-800/50 rounded-xl overflow-hidden backdrop-blur-sm flex-1 flex flex-col">
              <div className="px-5 py-4 border-b border-slate-800/50 flex justify-between items-center">
                <h3 className="text-base font-semibold text-white flex items-center gap-2"><Crosshair size={18} className="text-cyan-400"/> EKF Digital Twin: Mahalanobis Distance Time Series</h3>
                <span className="text-xs text-slate-600 font-mono">χ² threshold = 16.27 (99.9% CI, 3 DOF)</span>
              </div>
              <div className="p-6 flex-1 min-h-[400px]">
                {telemetry.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-700">
                      <Activity size={48} className="mb-4 opacity-30 animate-pulse"/>
                      <p>Waiting for telemetry. Launch a simulation from the Live Dashboard.</p>
                    </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={ekfData}>
                      <defs>
                        <linearGradient id="ekfGradLarge" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#0f172a"/>
                      <XAxis dataKey="t" stroke="#334155" tick={{fontSize:10, fill:'#475569'}} label={{ value: 'Time (s)', position: 'insideBottom', offset: -5, fill: '#475569' }}/>
                      <YAxis stroke="#334155" tick={{fontSize:10, fill:'#475569'}} domain={[0,40]} label={{ value: 'd² Score', angle: -90, position: 'insideLeft', fill: '#475569' }}/>
                      <Tooltip contentStyle={{backgroundColor:'#020208', borderColor:'#1e293b', borderRadius:'8px', fontSize:'12px'}} labelStyle={{color:'#94a3b8'}} itemStyle={{color:'#e2e8f0'}}/>
                      <Area type="monotone" dataKey="d" stroke="#06b6d4" strokeWidth={3} fill="url(#ekfGradLarge)" dot={false} isAnimationActive={false} name="d² Score"/>
                      <Line type="step" dataKey="thresh" stroke="#ef4444" strokeWidth={2} strokeDasharray="6 4" dot={false} name="χ² Threshold"/>
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>
              <div className="px-5 py-4 border-t border-slate-800/50 bg-slate-900/20 text-xs text-slate-400">
                <p><strong>Physics-based detection:</strong> The Extended Kalman Filter tracks the 6-DOF state $[x, y, z, v_x, v_y, v_z]^T$. If the sensor innovation residual yields a Mahalanobis distance exceeding the $\chi^2$ 99.9% confidence threshold (16.27), it indicates the UAV has physically violated the laws of motion, definitively identifying a NavIC/GPS spoofing attack.</p>
              </div>
            </div>
          </div>
        );
      case 'FORENSICS':
        return (
          <div className="space-y-5 animate-in fade-in duration-300 h-full flex flex-col">
            <div className="bg-[#040410]/80 border border-slate-800/50 rounded-xl overflow-hidden backdrop-blur-sm flex-1 flex flex-col">
              <div className="px-5 py-4 border-b border-slate-800/50 flex justify-between items-center">
                <h3 className="text-base font-semibold text-white flex items-center gap-2"><Database size={18} className="text-red-400"/> Cryptographic Chain Logger</h3>
                <button className="flex items-center gap-2 text-xs text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors border border-slate-700 px-3 py-1.5 rounded-lg shadow">
                  <Download size={14}/> Export JSONL
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-6 font-mono text-xs">
                 {alerts.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-700">
                      <FileJson size={48} className="mb-4 opacity-30"/>
                      <p>No forensic logs available. Chain is empty.</p>
                    </div>
                ) : (
                  <div className="space-y-4">
                    {alerts.map((a, i) => (
                      <div key={a.id} className="border border-slate-800 rounded-lg p-4 bg-[#0a0a1a]">
                        <div className="flex justify-between mb-2">
                           <span className="text-cyan-500">Block #{i+1}</span>
                           <span className="text-slate-500">{a.time} UTC</span>
                        </div>
                        <div className="text-emerald-400 mb-2">
                          "event_type": "ALERT",<br/>
                          "detector": "{a.detector}",<br/>
                          "severity": "{a.severity}",<br/>
                          "rule": "{a.rule}",<br/>
                          "detail": "{a.detail}"
                        </div>
                        <div className="border-t border-slate-800 pt-2 text-slate-600 break-all">
                          "prev_hash": "{i === 0 ? 'GENESIS_BLOCK_0000000000000' : alerts[i-1].sha256}"<br/>
                          <span className="text-slate-400">"entry_hash": "{a.sha256}"</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      case 'SETTINGS':
        return (
          <div className="space-y-5 animate-in fade-in duration-300">
             <div className="bg-[#040410]/80 border border-slate-800/50 rounded-xl p-6 backdrop-blur-sm max-w-2xl">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-6"><Settings size={20} className="text-slate-400"/> System Configuration</h3>
                
                <div className="space-y-6">
                  <div>
                    <label className="block text-xs font-bold text-slate-500 mb-2 uppercase">EKF $\chi^2$ Confidence Level</label>
                    <select className="w-full bg-[#0a0a1a] border border-slate-700 rounded-lg px-4 py-2 text-slate-300 focus:outline-none focus:border-cyan-500">
                      <option>99.9% (Threshold: 16.27) - DEFAULT</option>
                      <option>99.0% (Threshold: 11.34)</option>
                      <option>95.0% (Threshold: 7.81)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 mb-2 uppercase">ML Isolation Forest Contamination</label>
                    <input type="range" min="0.01" max="0.1" step="0.01" defaultValue="0.01" className="w-full accent-cyan-500"/>
                    <div className="flex justify-between text-[10px] text-slate-500 mt-1"><span>0.01 (Conservative)</span><span>0.1 (Aggressive)</span></div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 mb-2 uppercase">Forensic Sync Endpoint</label>
                    <input type="text" defaultValue="wss://hq.persistent-formation.mil/ingest" disabled className="w-full bg-[#0a0a1a]/50 border border-slate-800 rounded-lg px-4 py-2 text-slate-500 cursor-not-allowed"/>
                  </div>
                  
                  <div className="pt-4 border-t border-slate-800">
                    <button className="bg-cyan-900/50 border border-cyan-700 text-cyan-400 px-6 py-2 rounded-lg text-sm font-medium hover:bg-cyan-900 transition-colors">
                      Save Configuration
                    </button>
                  </div>
                </div>
             </div>
          </div>
        );
      default:
        return null;
    }
  };

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

        {/* Local Engine Status */}
        <div className="p-4 border-t border-slate-800/50">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500 font-mono">SIM ENGINE</span>
            <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
              <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"/>
              ONLINE
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col h-screen overflow-hidden bg-[radial-gradient(ellipse_at_top_left,_#0a0a1a_0%,_#020208_60%)]">
        {/* HEADER */}
        <header className="h-14 border-b border-slate-800/50 flex items-center justify-between px-6 bg-[#040410]/60 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-slate-600">SESSION</span>
            <code className="text-xs bg-slate-800/80 text-slate-300 px-2 py-1 rounded border border-slate-700/50">AEGIS_{Date.now().toString(36).substring(0,6).toUpperCase()}</code>
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

        <div className="flex-1 overflow-hidden p-6">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}
