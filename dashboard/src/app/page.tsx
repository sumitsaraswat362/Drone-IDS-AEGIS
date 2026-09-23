'use client';
import { useState, useEffect, useRef } from 'react';
import { Activity, ShieldAlert, ShieldCheck, Database, Radio, Crosshair, Terminal, Zap, Settings, Download, Server } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

type Alert = { id: number; time: string; rule: string; severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'; detail: string; };

export default function AegisDashboard() {
  const [activeTab, setActiveTab] = useState('DASHBOARD');
  const [systemStatus, setSystemStatus] = useState<'SECURE' | 'WARNING' | 'COMPROMISED'>('SECURE');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [packets, setPackets] = useState(14032);
  const [ekfData, setEkfData] = useState<{time: string, mahalanobis: number, threshold: number}[]>([]);
  const alertEndRef = useRef<HTMLDivElement>(null);

  // Initialize EKF Data
  useEffect(() => {
    const initData = Array.from({length: 20}).map((_, i) => ({
      time: `00:00:${i.toString().padStart(2, '0')}`,
      mahalanobis: Math.random() * 5 + 2,
      threshold: 16.27
    }));
    setEkfData(initData);
  }, []);

  // Simulate incoming telemetry and EKF tracking
  useEffect(() => {
    let pktCount = packets;
    const interval = setInterval(() => {
      pktCount += Math.floor(Math.random() * 50) + 10;
      setPackets(pktCount);
      
      setEkfData(prev => {
        const newData = [...prev.slice(1), {
          time: new Date().toLocaleTimeString('en-US', { hour12: false, second: '2-digit', minute: '2-digit' }),
          mahalanobis: systemStatus === 'SECURE' ? Math.random() * 5 + 2 : Math.random() * 30 + 16.5,
          threshold: 16.27
        }];
        return newData;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [systemStatus, packets]);

  // Auto-scroll alerts
  useEffect(() => {
    alertEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [alerts]);

  const triggerAttack = (type: string) => {
    setSystemStatus('COMPROMISED');
    let newAlert: Alert;
    
    if (type === 'gps') {
      newAlert = { id: Date.now(), time: new Date().toISOString().split('T')[1].slice(0, 11), rule: 'EKF_DIGITAL_TWIN_ANOMALY', severity: 'CRITICAL', detail: 'Mahalanobis distance 24.3 > 16.27. NavIC/GPS spoofing highly probable. Physics envelope violated.' };
    } else if (type === 'dos') {
      newAlert = { id: Date.now(), time: new Date().toISOString().split('T')[1].slice(0, 11), rule: 'R4_HEARTBEAT_FLOOD', severity: 'HIGH', detail: '80 heartbeats in 1.0s (threshold: 10). MAVLink bus saturated.' };
    } else {
      newAlert = { id: Date.now(), time: new Date().toISOString().split('T')[1].slice(0, 11), rule: 'R5_UNKNOWN_SRC_COMMAND', severity: 'CRITICAL', detail: 'COMMAND_LONG (id=21 LAND) injected from unknown system_id=99.' };
    }
    
    setAlerts(prev => [...prev.slice(-99), newAlert]);
    setTimeout(() => setSystemStatus('WARNING'), 4000);
    setTimeout(() => setSystemStatus('SECURE'), 8000);
  };

  return (
    <div className="min-h-screen bg-[#050505] text-slate-300 font-sans selection:bg-cyan-500/30 flex overflow-hidden">
      
      {/* SIDEBAR */}
      <aside className="w-64 border-r border-slate-800 bg-[#0a0a0a] flex flex-col">
        <div className="p-6 border-b border-slate-800">
          <h1 className="text-2xl font-black tracking-tighter text-white flex items-center gap-2">
            <ShieldCheck className="text-cyan-500" size={28} /> AEGIS
          </h1>
          <p className="text-[10px] text-cyan-500/70 uppercase tracking-widest mt-1 font-mono">Cyber-Physical Twin</p>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          {[
            { id: 'DASHBOARD', icon: Activity, label: 'Live Dashboard' },
            { id: 'EKF', icon: Crosshair, label: 'EKF Digital Twin' },
            { id: 'FORENSICS', icon: Database, label: 'Forensic Logs' },
            { id: 'TERMINAL', icon: Terminal, label: 'Terminal' },
            { id: 'SETTINGS', icon: Settings, label: 'System Settings' }
          ].map(item => (
            <button key={item.id} onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${activeTab === item.id ? 'bg-cyan-950/40 text-cyan-400 border border-cyan-900/50' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'}`}>
              <item.icon size={18} /> {item.label}
            </button>
          ))}
        </nav>

        <div className="p-6 border-t border-slate-800">
          <div className="flex items-center justify-between text-xs font-mono text-slate-500 mb-2">
            <span>UAV LINK</span>
            <span className="text-emerald-500">CONNECTED</span>
          </div>
          <div className="flex items-center justify-between text-xs font-mono text-slate-500">
            <span>PING</span>
            <span>12ms</span>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col h-screen overflow-y-auto bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900/20 via-[#050505] to-[#050505]">
        
        {/* TOP NAVBAR */}
        <header className="h-16 border-b border-slate-800 flex items-center justify-between px-8 bg-[#0a0a0a]/50 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <span className="text-sm font-mono text-slate-400">SESSION ID:</span>
            <span className="text-sm font-mono text-white bg-slate-800 px-2 py-1 rounded">AEGIS_1790176941</span>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Server size={14} className="text-slate-400" />
              <span className="text-xs font-mono text-slate-400">GCS NODE 01</span>
            </div>
            <div className={`px-4 py-1.5 rounded-full text-xs font-bold font-mono tracking-widest border flex items-center gap-2 ${
              systemStatus === 'SECURE' ? 'bg-emerald-950/50 text-emerald-400 border-emerald-900' :
              systemStatus === 'WARNING' ? 'bg-orange-950/50 text-orange-400 border-orange-900' :
              'bg-red-950/50 text-red-400 border-red-900 animate-pulse'
            }`}>
              <div className={`h-2 w-2 rounded-full ${systemStatus === 'SECURE' ? 'bg-emerald-400' : systemStatus === 'WARNING' ? 'bg-orange-400' : 'bg-red-400 animate-ping'}`} />
              {systemStatus}
            </div>
          </div>
        </header>

        {/* DASHBOARD CONTENT */}
        <div className="p-8 space-y-6">
          
          {/* KPI CARDS */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-[#0a0a0a] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity"><Radio size={48} /></div>
              <p className="text-xs font-semibold text-slate-400 mb-1">PACKETS ANALYZED</p>
              <h2 className="text-3xl font-mono text-white">{packets.toLocaleString()}</h2>
              <p className="text-[10px] text-cyan-500 mt-2 flex items-center gap-1"><Zap size={10} /> +124/sec (MAVLink v2)</p>
            </div>
            
            <div className="bg-[#0a0a0a] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 text-red-500 group-hover:opacity-20 transition-opacity"><ShieldAlert size={48} /></div>
              <p className="text-xs font-semibold text-slate-400 mb-1">ACTIVE THREATS</p>
              <h2 className={`text-3xl font-mono ${alerts.length > 0 ? 'text-red-500' : 'text-white'}`}>{alerts.length}</h2>
              <p className="text-[10px] text-slate-500 mt-2">Zero-day isolation forest active</p>
            </div>

            <div className="bg-[#0a0a0a] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 text-cyan-500 group-hover:opacity-20 transition-opacity"><Crosshair size={48} /></div>
              <p className="text-xs font-semibold text-slate-400 mb-1">EKF χ² SCORE (99.9%)</p>
              <h2 className={`text-3xl font-mono ${ekfData[ekfData.length-1]?.mahalanobis > 16.27 ? 'text-red-500' : 'text-emerald-400'}`}>
                {ekfData[ekfData.length-1]?.mahalanobis.toFixed(2)}
              </h2>
              <p className="text-[10px] text-slate-500 mt-2">Mahalanobis Distance</p>
            </div>

            <div className="bg-[#0a0a0a] border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity"><Activity size={48} /></div>
              <p className="text-xs font-semibold text-slate-400 mb-1">FALSE POSITIVE RATE</p>
              <h2 className="text-3xl font-mono text-white">{"<"} 2.1%</h2>
              <p className="text-[10px] text-emerald-500 mt-2 flex items-center gap-1"><ShieldCheck size={10} /> Tuned via EKF</p>
            </div>
          </div>

          {/* MAIN CHARTS & LOGS */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-[450px]">
            
            {/* EKF CHART */}
            <div className="xl:col-span-2 bg-[#0a0a0a] border border-slate-800 rounded-xl shadow-lg flex flex-col overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/20">
                <h3 className="text-sm font-bold text-white flex items-center gap-2"><Crosshair size={16} className="text-cyan-500"/> EKF Digital Twin: Kinematic Innovation</h3>
                <span className="text-[10px] text-slate-500 font-mono">Live Mahalanobis Distance (d²)</span>
              </div>
              <div className="flex-1 p-4 w-full h-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={ekfData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#475569" tick={{fontSize: 10}} />
                    <YAxis stroke="#475569" tick={{fontSize: 10}} domain={[0, 40]} />
                    <Tooltip contentStyle={{backgroundColor: '#0f172a', borderColor: '#1e293b', fontSize: '12px'}} />
                    <Line type="monotone" dataKey="mahalanobis" stroke="#06b6d4" strokeWidth={2} dot={false} isAnimationActive={false} />
                    <Line type="step" dataKey="threshold" stroke="#ef4444" strokeWidth={1} strokeDasharray="5 5" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* THREAT LOG */}
            <div className="bg-[#0a0a0a] border border-slate-800 rounded-xl shadow-lg flex flex-col overflow-hidden">
              <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/20">
                <h3 className="text-sm font-bold text-white flex items-center gap-2"><ShieldAlert size={16} className="text-red-500"/> Forensic Alert Log</h3>
                <button className="text-[10px] flex items-center gap-1 text-slate-400 hover:text-white transition-colors"><Download size={12}/> EXPORT JSONL</button>
              </div>
              <div className="flex-1 p-3 overflow-y-auto space-y-3 font-mono text-xs">
                {alerts.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-600 opacity-50">
                    <ShieldCheck size={48} className="mb-2" />
                    <p>No anomalies detected in current session.</p>
                  </div>
                ) : (
                  alerts.map(a => (
                    <div key={a.id} className="border-l-2 border-red-500 bg-red-950/10 p-3 rounded-r-lg">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-slate-400">{a.time}</span>
                        <span className={`px-2 py-0.5 text-[9px] font-bold rounded ${a.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : 'bg-orange-500/20 text-orange-400'}`}>{a.severity}</span>
                      </div>
                      <div className="text-white font-bold mb-1">{a.rule}</div>
                      <div className="text-slate-400 leading-relaxed">{a.detail}</div>
                      <div className="mt-2 text-[9px] text-slate-600 border-t border-slate-800/50 pt-1">
                        SHA256: {Math.random().toString(36).substring(2, 15)}...
                      </div>
                    </div>
                  ))
                )}
                <div ref={alertEndRef} />
              </div>
            </div>

          </div>

          {/* ATTACK SIMULATION CONTROLS */}
          <div className="bg-[#0a0a0a] border border-slate-800 rounded-xl shadow-lg overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/20">
              <h3 className="text-sm font-bold text-white flex items-center gap-2"><Zap size={16} className="text-yellow-500"/> Live Threat Injection (Demonstration)</h3>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <button onClick={() => triggerAttack('gps')} className="flex flex-col items-center justify-center p-4 border border-slate-700 rounded-lg hover:bg-slate-800 hover:border-cyan-500 transition-all group">
                <Crosshair size={24} className="text-cyan-500 mb-2 group-hover:scale-110 transition-transform" />
                <span className="text-sm font-bold text-white">Inject NavIC/GPS Spoofing</span>
                <span className="text-[10px] text-slate-500 mt-1 text-center">Triggers EKF Innovation Anomaly</span>
              </button>
              
              <button onClick={() => triggerAttack('cmd')} className="flex flex-col items-center justify-center p-4 border border-slate-700 rounded-lg hover:bg-slate-800 hover:border-red-500 transition-all group">
                <Terminal size={24} className="text-red-500 mb-2 group-hover:scale-110 transition-transform" />
                <span className="text-sm font-bold text-white">Inject GCS Command Impersonation</span>
                <span className="text-[10px] text-slate-500 mt-1 text-center">Triggers Rule Engine R5 & R7</span>
              </button>
              
              <button onClick={() => triggerAttack('dos')} className="flex flex-col items-center justify-center p-4 border border-slate-700 rounded-lg hover:bg-slate-800 hover:border-orange-500 transition-all group">
                <Radio size={24} className="text-orange-500 mb-2 group-hover:scale-110 transition-transform" />
                <span className="text-sm font-bold text-white">Inject MAVLink DoS Flood</span>
                <span className="text-[10px] text-slate-500 mt-1 text-center">Triggers Rule Engine R4</span>
              </button>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
