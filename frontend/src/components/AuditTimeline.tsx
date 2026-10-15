import React, { useState } from 'react';
import type { AuditRecord } from '../api/client';
import { ShieldCheck, ShieldAlert, CheckCircle2, AlertOctagon } from 'lucide-react';

interface AuditTimelineProps {
  records: AuditRecord[];
  isChainValid: boolean;
  firstInvalidIndex: number | null;
  onVerifyChain: () => void;
  onTamperRecord: (index: number) => void;
}

const STATE_NAMES = ['Observe', 'Throttle', 'Challenge', 'Restriction', 'Escalation'];

export const AuditTimeline: React.FC<AuditTimelineProps> = ({
  records,
  isChainValid,
  firstInvalidIndex,
  onVerifyChain,
  onTamperRecord,
}) => {
  const [_selectedRecordIndex, setSelectedRecordIndex] = useState<number>(0);

  return (
    <div className="flex flex-col h-full bg-slate-900/80 border border-slate-800 rounded-lg p-4 text-xs text-slate-300 space-y-3 shadow-xl">
      {/* Header and Verification Controls */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Cryptographic Audit Chain (Invariant I7)
            </h3>
            {isChainValid ? (
              <span className="flex items-center gap-1 bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded text-[10px] font-semibold">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" /> CHAIN INTACT
              </span>
            ) : (
              <span className="flex items-center gap-1 bg-rose-950 text-rose-400 border border-rose-800 px-2 py-0.5 rounded text-[10px] font-semibold animate-pulse">
                <AlertOctagon className="w-3 h-3 text-rose-400" /> CORRUPTION AT #{firstInvalidIndex}
              </span>
            )}
          </div>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Append-only SHA-256 hash-chained log. h_i = SHA256(h_{'{i-1}'} || canonical_json(rec_i))
          </p>
        </div>

        {/* Demo Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={onVerifyChain}
            className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-[11px] font-medium transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Verify Chain
          </button>
          <button
            onClick={() => onTamperRecord(Math.max(0, Math.floor(records.length / 2)))}
            className="flex items-center gap-1 px-2.5 py-1 bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800 rounded text-[11px] font-medium transition-colors"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" /> Tamper Demo (M14b)
          </button>
        </div>
      </div>

      {/* Audit Chain Table */}
      <div className="flex-1 overflow-y-auto border border-slate-800/80 rounded bg-slate-950/50">
        <table className="w-full text-left border-collapse text-[11px]">
          <thead className="bg-slate-900 sticky top-0 text-[10px] text-slate-400 uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-2 px-2.5">#</th>
              <th className="py-2 px-2">Win</th>
              <th className="py-2 px-2">Account</th>
              <th className="py-2 px-2">Transition</th>
              <th className="py-2 px-2">Rule Fired</th>
              <th className="py-2 px-2 font-mono">Record Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-900">
            {records.slice(-100).reverse().map((rec) => {
              const isCorrupt = firstInvalidIndex !== null && rec.record_index === firstInvalidIndex;
              return (
                <tr
                  key={rec.record_index}
                  onClick={() => setSelectedRecordIndex(rec.record_index)}
                  className={`cursor-pointer transition-colors ${
                    isCorrupt
                      ? 'bg-rose-950/40 text-rose-300 font-semibold'
                      : rec.new_state > rec.prev_state
                      ? 'bg-amber-950/20 text-slate-200'
                      : 'hover:bg-slate-900/60 text-slate-400'
                  }`}
                >
                  <td className="py-1.5 px-2.5 font-mono text-[10px] text-slate-500">#{rec.record_index}</td>
                  <td className="py-1.5 px-2 font-mono text-[10px] text-slate-400">W{rec.window_index}</td>
                  <td className="py-1.5 px-2 font-mono text-slate-300">{rec.account_id}</td>
                  <td className="py-1.5 px-2">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                        rec.new_state === 0
                          ? 'bg-sky-950 text-sky-400'
                          : rec.new_state === 1
                          ? 'bg-amber-950 text-amber-400'
                          : rec.new_state === 2
                          ? 'bg-orange-950 text-orange-400'
                          : 'bg-red-950 text-red-400'
                      }`}
                    >
                      {STATE_NAMES[rec.prev_state]} → {STATE_NAMES[rec.new_state]}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 truncate max-w-[200px]" title={rec.rule_fired}>
                    {rec.rule_fired}
                  </td>
                  <td className="py-1.5 px-2 font-mono text-[10px] text-slate-500">
                    {rec.record_hash.substring(0, 10)}...
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
