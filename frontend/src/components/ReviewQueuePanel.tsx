import React from 'react';
import type { ReviewQueueEntry } from '../api/client';
import { UserCheck, Clock } from 'lucide-react';

interface ReviewQueuePanelProps {
  entries: ReviewQueueEntry[];
  onSelectCluster: (clusterId: string) => void;
  selectedClusterId: string | null;
}

export const ReviewQueuePanel: React.FC<ReviewQueuePanelProps> = ({
  entries,
  onSelectCluster,
  selectedClusterId,
}) => {
  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
        <div className="flex items-center gap-1.5 font-bold text-slate-200 uppercase tracking-wider text-[11px]">
          <UserCheck className="w-3.5 h-3.5 text-sky-400" />
          <span>Analyst Review Queue (K=5 Rate-Limited, §21.8)</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">Ranked by Coordination Score C_c</span>
      </div>

      {entries.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-500 text-[11px] italic">
          No unprovenanced clusters currently in review queue.
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
          {entries.map((entry) => (
            <div
              key={entry.cluster_id}
              onClick={() => onSelectCluster(entry.cluster_id)}
              className={`p-2 rounded border cursor-pointer transition-all ${
                entry.cluster_id === selectedClusterId
                  ? 'bg-sky-950/40 border-sky-600 text-slate-100'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-[10px] px-1 py-0.2 bg-slate-800 text-sky-400 rounded">
                    Rank #{entry.queue_rank}
                  </span>
                  <span className="font-mono font-bold text-slate-200">{entry.cluster_id}</span>
                </div>
                <span className="font-mono text-amber-400 font-semibold text-[11px]">
                  C_c: {entry.coordination_score_c_c.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1 text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" /> {entry.persistence_windows} win persistence
                </span>
                <span>{entry.member_count} members</span>
                <span className="text-rose-400/90 font-medium">Zero Provenance</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
