import React from 'react';
import type { EvidenceCard, ClusterSummary } from '../api/client';
import { ShieldCheck, ShieldAlert, ArrowRight, HelpCircle, HardDrive, MessageSquare, Clock } from 'lucide-react';

interface EvidencePanelProps {
  card: EvidenceCard | null;
  clusters: ClusterSummary[];
  onSelectCluster: (clusterId: string) => void;
  isLoading: boolean;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  card,
  clusters,
  onSelectCluster,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900/60 border border-slate-800 rounded-lg p-6 text-slate-400">
        Loading evidence card...
      </div>
    );
  }

  if (!card) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-slate-900/60 border border-slate-800 rounded-lg p-6 text-center text-slate-400">
        <HelpCircle className="w-10 h-10 mb-2 text-slate-500" />
        <div className="text-sm font-medium">No Cluster Selected</div>
        <p className="text-xs text-slate-500 mt-1">
          Click any cluster node in the network graph or select from the cluster list below.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900/80 border border-slate-800 rounded-lg overflow-y-auto text-xs text-slate-300 p-4 space-y-4 shadow-xl">
      {/* Cluster Header & Quick Selector */}
      <div className="border-b border-slate-800 pb-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Selected Cluster</span>
            <h3 className="text-base font-bold text-slate-100 font-mono">{card.cluster_id}</h3>
          </div>
          <span
            className={`px-2.5 py-1 rounded text-xs font-semibold uppercase tracking-wider ${
              card.current_state === 0
                ? 'bg-sky-950 text-sky-400 border border-sky-800'
                : card.current_state === 1
                ? 'bg-amber-950 text-amber-400 border border-amber-800'
                : card.current_state === 2
                ? 'bg-orange-950 text-orange-400 border border-orange-800'
                : 'bg-red-950 text-red-400 border border-red-800'
            }`}
          >
            {card.state_label}
          </span>
        </div>

        {/* Quick Cluster Selector Pills */}
        <div className="flex items-center gap-1.5 mt-2 overflow-x-auto pb-1">
          <span className="text-[10px] text-slate-500">Clusters:</span>
          {clusters.slice(0, 6).map((c) => (
            <button
              key={c.cluster_id}
              onClick={() => onSelectCluster(c.cluster_id)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                c.cluster_id === card.cluster_id
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/50'
                  : 'bg-slate-800/80 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {c.cluster_id.split('_').slice(-2).join('_')} ({c.member_count}m)
            </button>
          ))}
        </div>
      </div>

      {/* Cluster Stats Overview */}
      <div className="grid grid-cols-4 gap-2 text-center">
        <div className="bg-slate-800/40 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase">Members</div>
          <div className="text-sm font-mono font-bold text-slate-100">{card.member_count}</div>
        </div>
        <div className="bg-slate-800/40 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase">Eligible</div>
          <div className="text-sm font-mono font-bold text-slate-100">
            {card.eligible_count} <span className="text-[10px] text-slate-400">({(card.eligible_fraction * 100).toFixed(0)}%)</span>
          </div>
        </div>
        <div className="bg-slate-800/40 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase">Score (L_c)</div>
          <div className="text-sm font-mono font-bold text-sky-400">{card.evidence_score.toFixed(2)}</div>
        </div>
        <div className="bg-slate-800/40 p-2 rounded border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase">Risk (R_c)</div>
          <div className="text-sm font-mono font-bold text-amber-400">{card.running_risk.toFixed(2)}</div>
        </div>
      </div>

      {/* Non-Compensatory Gate Status Box */}
      <div
        className={`p-3 rounded-lg border ${
          card.gate_passed
            ? 'bg-emerald-950/30 border-emerald-800 text-emerald-200'
            : 'bg-rose-950/30 border-rose-800 text-rose-200'
        }`}
      >
        <div className="flex items-center gap-2 font-semibold">
          {card.gate_passed ? <ShieldCheck className="w-4 h-4 text-emerald-400" /> : <ShieldAlert className="w-4 h-4 text-rose-400" />}
          <span>{card.gate_passed ? 'Non-Compensatory Gate: PASSED' : 'Non-Compensatory Gate: REFUSED'}</span>
        </div>
        <p className="mt-1 text-xs opacity-90">{card.gate_message}</p>
        
        {/* Active Groups checklist */}
        <div className="flex items-center gap-3 mt-2 text-[11px]">
          <div className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${card.active_groups.includes('Provenance') ? 'bg-emerald-400' : 'bg-slate-600'}`} />
            <span className={card.active_groups.includes('Provenance') ? 'text-slate-200 font-medium' : 'text-slate-500'}>
              Provenance {card.active_groups.includes('Provenance') ? '✓' : '✗'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${card.active_groups.includes('Behavioral') ? 'bg-emerald-400' : 'bg-slate-600'}`} />
            <span className={card.active_groups.includes('Behavioral') ? 'text-slate-200 font-medium' : 'text-slate-500'}>
              Behavioral {card.active_groups.includes('Behavioral') ? '✓' : '✗'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${card.active_groups.includes('Content') ? 'bg-emerald-400' : 'bg-slate-600'}`} />
            <span className={card.active_groups.includes('Content') ? 'text-slate-200 font-medium' : 'text-slate-500'}>
              Content {card.active_groups.includes('Content') ? '✓' : '✗'}
            </span>
          </div>
        </div>
      </div>

      {/* Signal Contributions (Additive Log-Odds) */}
      <div>
        <div className="font-semibold text-slate-200 mb-2 flex items-center justify-between">
          <span>Signal Contributions (Exact Additive Log-Odds, Invariant I4)</span>
          <span className="text-[10px] text-slate-400">Total: {card.evidence_score.toFixed(2)}</span>
        </div>
        <div className="space-y-1.5">
          {card.signal_contributions.map((sig) => {
            const widthPct = Math.min(100, (sig.calibrated_log_odds / 2.5) * 100);
            return (
              <div key={sig.signal_name} className="bg-slate-800/40 p-1.5 rounded">
                <div className="flex justify-between text-[11px] mb-0.5">
                  <span className="font-mono text-slate-300">{sig.signal_name}</span>
                  <span className="font-mono font-medium text-slate-200">
                    +{sig.calibrated_log_odds.toFixed(2)}{' '}
                    <span className="text-[10px] text-slate-500">(raw: {sig.raw_value.toFixed(2)})</span>
                  </span>
                </div>
                <div className="w-full bg-slate-700/50 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      sig.group === 'Provenance'
                        ? 'bg-pink-500'
                        : sig.group === 'Behavioral'
                        ? 'bg-yellow-400'
                        : sig.group === 'Content'
                        ? 'bg-emerald-400'
                        : 'bg-slate-500'
                    }`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Exact Counterfactuals (§11.2) */}
      <div className="bg-slate-800/30 p-3 rounded-lg border border-slate-800">
        <div className="font-semibold text-slate-200 mb-2 flex items-center gap-1.5">
          <span>Exact Counterfactual Re-Scoring (§11.2)</span>
        </div>
        <div className="space-y-2">
          {card.counterfactuals.map((cf) => (
            <div key={cf.removed_group_or_signal} className="text-[11px] border-l-2 border-slate-700 pl-2">
              <div className="flex items-center gap-1 text-slate-300 font-medium">
                <span className="text-rose-400">Without {cf.removed_group_or_signal}:</span>
                <span className="flex items-center gap-1">
                  State {cf.original_state} <ArrowRight className="w-3 h-3 text-slate-500 inline" /> State {cf.counterfactual_state}
                </span>
                <span className="text-slate-500 font-mono text-[10px]">(-{cf.delta_log_odds.toFixed(2)} log-odds)</span>
              </div>
              <p className="text-slate-400 text-[10px] mt-0.5">{cf.explanation}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Representative Evidence Samples */}
      {card.representative_samples.length > 0 && (
        <div className="bg-slate-800/30 p-3 rounded-lg border border-slate-800">
          <div className="font-semibold text-slate-200 mb-2">Representative Evidence Samples</div>
          <div className="space-y-2">
            {card.representative_samples.map((samp, idx) => (
              <div key={idx} className="bg-slate-900/60 p-2 rounded border border-slate-800/60 text-[11px]">
                <div className="flex items-center gap-1.5 text-slate-300 font-medium mb-1">
                  {samp.sample_type === 'device_group' ? (
                    <HardDrive className="w-3.5 h-3.5 text-pink-400" />
                  ) : samp.sample_type === 'post_pair' ? (
                    <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Clock className="w-3.5 h-3.5 text-yellow-400" />
                  )}
                  <span>{samp.description}</span>
                </div>
                {samp.sample_type === 'post_pair' && (
                  <div className="space-y-1 font-mono text-[10px] text-slate-400 bg-slate-950 p-1.5 rounded">
                    <div>[A1]: "{samp.evidence_data.post_1?.text}"</div>
                    <div>[A2]: "{samp.evidence_data.post_2?.text}"</div>
                  </div>
                )}
                {samp.sample_type === 'device_group' && (
                  <div className="font-mono text-[10px] text-slate-400">
                    Hashed Hardware ID: <span className="text-pink-400">{samp.evidence_data.device_hash_prefix}***</span> (Privacy-by-Design, Invariant I8)
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
