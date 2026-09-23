'use client';
import { useState, useEffect, useRef } from 'react';

type Alert = {
  id: number;
  time: string;
  rule: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  detail: string;
};

export default function AegisDashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [packets, setPackets] = useState(0);
  const [systemStatus, setSystemStatus] = useState('ARMED');
  const alertEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom of alerts
    alertEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [alerts]);

  useEffect(() => {
    let pktCount = 0;
    const pktInterval = setInterval(() => {
      pktCount += Math.floor(Math.random() * 20) + 10;
      setPackets(pktCount);
    }, 1000);

    const simulatedAttacks = [
      { rule: 'R1_GPS_POSITION_JUMP', severity: 'CRITICAL', detail: 'Position jumped 86.4m in 0.2s (implied speed 432.0 m/s)' },
      { rule: 'ML_ANOMALY_DETECTION', severity: 'HIGH', detail: 'Isolation Forest anomaly score=-0.3812 (threshold=-0.2)' },
      { rule: 'R5_UNKNOWN_SRC_COMMAND', severity: 'CRITICAL', detail: 'COMMAND_LONG from unknown system_id=99' },
      { rule: 'R7_FORGED_COMMAND', severity: 'CRITICAL', detail: 'Command LAND (id=21) from non-GCS sender (sys_id=99)' },
      { rule: 'R4_HEARTBEAT_FLOOD', severity: 'HIGH', detail: '80 heartbeats in 1.0s (threshold: 10)' },
      { rule: 'R2_GPS_HDOP_ANOMALY', severity: 'MEDIUM', detail: 'HDOP=0.20 is abnormally low — possible spoofing' }
    ];

    let attackId = 0;
    const attackInterval = setInterval(() => {
      if (Math.random() > 0.4) {
        const attack = simulatedAttacks[Math.floor(Math.random() * simulatedAttacks.length)];
        const newAlert: Alert = {
          id: attackId++,
          time: new Date().toISOString().split('T')[1].slice(0, 11),
          rule: attack.rule,
          severity: attack.severity as any,
          detail: attack.detail
        };
        setAlerts(prev => [...prev.slice(-49), newAlert]);
        setSystemStatus('THREAT DETECTED');
        setTimeout(() => setSystemStatus('ARMED'), 2000);
      }
    }, 2500);

    return () => {
      clearInterval(pktInterval);
      clearInterval(attackInterval);
    };
  }, []);

  const getSeverityColor = (sev: string) => {
    switch (sev) {
      case 'CRITICAL': return 'bg-red-500 text-white';
      case 'HIGH': return 'bg-orange-500 text-white';
      case 'MEDIUM': return 'bg-yellow-500 text-black';
      default: return 'bg-gray-500 text-white';
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-emerald-500 font-mono p-4 md:p-8 selection:bg-emerald-500 selection:text-neutral-950">
      
      {/* HEADER */}
      <header className="flex justify-between items-center border-b border-emerald-500/30 pb-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-widest text-white">AEGIS <span className="text-emerald-500 opacity-70">IDS</span></h1>
          <p className="text-xs text-emerald-500/50 uppercase tracking-widest">Autonomous Embedded Guardian for Intrusion in Swarms</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-emerald-500/70">SYSTEM STATUS</div>
            <div className={`font-bold tracking-widest ${systemStatus === 'THREAT DETECTED' ? 'text-red-500 animate-pulse' : 'text-emerald-400'}`}>
              [{systemStatus}]
            </div>
          </div>
          <div className="h-10 w-10 border border-emerald-500/30 flex items-center justify-center rounded-full">
            <div className={`h-4 w-4 rounded-full ${systemStatus === 'THREAT DETECTED' ? 'bg-red-500' : 'bg-emerald-500 animate-pulse'}`} />
          </div>
        </div>
      </header>

      {/* MAIN GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: Map & Metrics */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* MAP */}
          <div className="border border-emerald-500/30 bg-neutral-900/50 h-[400px] relative overflow-hidden flex flex-col">
            <div className="border-b border-emerald-500/30 bg-emerald-950/30 px-3 py-1 text-xs text-white">
              [LIVE] MAVLINK PACKET INTERCEPT
            </div>
            <div className="flex-1 relative p-4 flex items-center justify-center">
              {/* Radar rings */}
              <div className="absolute h-64 w-64 border border-emerald-500/20 rounded-full" />
              <div className="absolute h-48 w-48 border border-emerald-500/20 rounded-full" />
              <div className="absolute h-32 w-32 border border-emerald-500/20 rounded-full" />
              
              {/* Scanning line */}
              <div className="absolute h-32 w-1 bg-emerald-500/50 origin-bottom animate-[spin_3s_linear_infinite]" style={{ top: 'calc(50% - 8rem)' }} />

              {/* Drone marker */}
              <div className="absolute h-3 w-3 bg-white rounded-full shadow-[0_0_10px_#fff]" />
              
              {/* Threat markers */}
              {systemStatus === 'THREAT DETECTED' && (
                <div className="absolute top-1/4 left-1/3 h-4 w-4 border-2 border-red-500 rounded-full animate-ping" />
              )}
            </div>
          </div>

          {/* METRICS */}
          <div className="grid grid-cols-3 gap-4">
            <div className="border border-emerald-500/30 bg-neutral-900/50 p-4">
              <div className="text-xs text-emerald-500/50 mb-1">PACKETS ANALYZED</div>
              <div className="text-2xl text-white">{packets.toLocaleString()}</div>
            </div>
            <div className="border border-emerald-500/30 bg-neutral-900/50 p-4">
              <div className="text-xs text-emerald-500/50 mb-1">TOTAL THREATS</div>
              <div className="text-2xl text-red-400">{alerts.length}</div>
            </div>
            <div className="border border-emerald-500/30 bg-neutral-900/50 p-4">
              <div className="text-xs text-emerald-500/50 mb-1">CHAIN HASH</div>
              <div className="text-sm text-white truncate">a5d0da027a6...</div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Threat Log */}
        <div className="border border-emerald-500/30 bg-neutral-900/50 flex flex-col h-[520px]">
          <div className="border-b border-emerald-500/30 bg-emerald-950/30 px-3 py-1 text-xs text-white flex justify-between">
            <span>THREAT ALERT LOG</span>
            <span>{alerts.length > 0 ? 'LIVE' : 'WAITING'}</span>
          </div>
          <div className="flex-1 p-2 overflow-y-auto space-y-2 text-xs">
            {alerts.length === 0 && (
              <div className="text-emerald-500/50 text-center mt-10">NO ANOMALIES DETECTED</div>
            )}
            {alerts.map(a => (
              <div key={a.id} className="border border-emerald-500/20 p-2 bg-neutral-950">
                <div className="flex justify-between mb-1">
                  <span className="text-emerald-500/70">{a.time}</span>
                  <span className={`px-1 text-[10px] uppercase font-bold ${getSeverityColor(a.severity)}`}>
                    {a.severity}
                  </span>
                </div>
                <div className="text-white font-bold mb-1">{a.rule}</div>
                <div className="text-emerald-500/80">{a.detail}</div>
              </div>
            ))}
            <div ref={alertEndRef} />
          </div>
        </div>

      </div>
    </div>
  );
}
