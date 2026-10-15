/**
 * Typed API Client for BreachX / HYDRA Detection Platform.
 */

export interface Scenario {
  scenario_id: string;
  name: string;
  description: string;
  n_background: number;
  n_bots: number;
  n_fan_decoys: number;
  n_news_decoys: number;
  n_nat_decoys: number;
}

export interface GraphNode {
  id: string;
  label: string;
  cluster_id?: string;
  policy_state: number;
  is_eligible: boolean;
  actor_type_truth?: string;
  is_bot_truth?: boolean;
  post_count: number;
  device_hash?: string;
  ip_range_hash?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  edge_types: string[];
}

export interface ClusterSummary {
  cluster_id: string;
  member_count: number;
  member_ids: string[];
  eligible_member_ids: string[];
  eligible_fraction: number;
  internal_density: number;
  median_policy_state: number;
  evidence_score: number;
  active_evidence_groups: string[];
  gate_passed: boolean;
  gate_reason: string;
}

export interface NetworkGraphPayload {
  window_index: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: ClusterSummary[];
}

export interface SignalContribution {
  signal_name: string;
  family: string;
  group: string;
  raw_value: number;
  calibrated_log_odds: number;
  weight: number;
}

export interface CounterfactualOutcome {
  removed_group_or_signal: string;
  original_state: number;
  counterfactual_state: number;
  delta_log_odds: number;
  explanation: string;
}

export interface RepresentativeSample {
  sample_type: string;
  description: string;
  evidence_data: Record<string, any>;
}

export interface EvidenceCard {
  cluster_id: string;
  window_index: number;
  member_count: number;
  eligible_count: number;
  eligible_fraction: number;
  creation_time_span_seconds: number;
  current_state: number;
  state_label: string;
  risk_trend: string;
  running_risk: number;
  evidence_score: number;
  group_contributions: Record<string, number>;
  signal_contributions: SignalContribution[];
  active_groups: string[];
  missing_groups: string[];
  has_provenance: boolean;
  gate_passed: boolean;
  gate_message: string;
  counterfactuals: CounterfactualOutcome[];
  representative_samples: RepresentativeSample[];
  ineligible_members: string[];
}

export interface AuditRecord {
  record_index: number;
  window_index: number;
  cluster_id: string;
  account_id: string;
  prev_state: number;
  new_state: number;
  rule_fired: string;
  evidence_score: number;
  running_risk: number;
  is_eligible: boolean;
  prev_hash: string;
  record_hash: string;
  timestamp: number;
}

export interface AuditLogResponse {
  is_chain_valid: boolean;
  first_invalid_index: number | null;
  verification_message: string;
  total_records: number;
  records: AuditRecord[];
}

export interface ReviewQueueEntry {
  cluster_id: string;
  window_index: number;
  coordination_score_c_c: number;
  persistence_windows: number;
  member_count: number;
  active_groups: string[];
  is_behavior_only: boolean;
  queue_rank: number;
  evidence_summary: string;
}

export interface CostOfEvasionRecord {
  round_index: number;
  tactic_name: string;
  throughput_retained_pct: number;
  reach_retained_pct: number;
  distinct_devices_required: number;
  distinct_ips_required: number;
  escape_rate_pct: number;
  detection_state_summary: string;
}

export interface AblationRow {
  scenario_id: string;
  condition_id: string;
  condition_description: string;
  disabled_groups: string[];
  bot_farm_recall_pct: number;
  decoy_restriction_rate_pct: number;
  detection_delay_windows: number | null;
  background_fpr_pct: number;
  audit_chain_intact: boolean;
}

export interface BaselineRow {
  baseline_name: string;
  bot_farm_detected: boolean;
  decoy_fan_flagged: boolean;
  decoy_nat_flagged: boolean;
  decoy_news_flagged: boolean;
  background_fp_count: number;
  primary_failure_mode: string;
}

const API_BASE = '/api';

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  async getScenarios(): Promise<Scenario[]> {
    const res = await fetch(`${API_BASE}/scenarios`);
    return res.json();
  },

  async runSimulation(scenarioId: string, seed: number = 42, totalWindows: number = 10, disabledGroups: string[] = []) {
    const res = await fetch(`${API_BASE}/simulation/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario_id: scenarioId,
        seed,
        total_windows: totalWindows,
        disabled_groups: disabledGroups,
      }),
    });
    return res.json();
  },

  async stepSimulation(windowIndex: number) {
    const res = await fetch(`${API_BASE}/simulation/step?window_index=${windowIndex}`, {
      method: 'POST',
    });
    return res.json();
  },

  async resetSimulation() {
    const res = await fetch(`${API_BASE}/simulation/reset`, { method: 'POST' });
    return res.json();
  },

  async getGraph(windowIndex?: number, showGroundTruth: boolean = false): Promise<NetworkGraphPayload> {
    const url = new URL(`${window.location.origin}${API_BASE}/simulation/graph`);
    if (windowIndex !== undefined) url.searchParams.set('window_index', windowIndex.toString());
    if (showGroundTruth) url.searchParams.set('show_ground_truth', 'true');
    const res = await fetch(url.toString());
    return res.json();
  },

  async getEvidenceCard(clusterId: string): Promise<EvidenceCard> {
    const res = await fetch(`${API_BASE}/simulation/evidence/${clusterId}`);
    if (!res.ok) throw new Error('Evidence card not found');
    return res.json();
  },

  async getReviewQueue(): Promise<ReviewQueueEntry[]> {
    const res = await fetch(`${API_BASE}/review-queue`);
    return res.json();
  },

  async getAuditLogs(): Promise<AuditLogResponse> {
    const res = await fetch(`${API_BASE}/audit/logs`);
    return res.json();
  },

  async verifyAuditLog() {
    const res = await fetch(`${API_BASE}/audit/verify`, { method: 'POST' });
    return res.json();
  },

  async tamperAuditLog(recordIndex: number) {
    const res = await fetch(`${API_BASE}/audit/tamper`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ record_index: recordIndex }),
    });
    return res.json();
  },

  async getEvaluationMetrics() {
    const res = await fetch(`${API_BASE}/evaluation/metrics`);
    return res.json();
  },

  async getAblationMatrix(): Promise<{ ablation_matrix: AblationRow[]; baselines_comparison: BaselineRow[] }> {
    const res = await fetch(`${API_BASE}/evaluation/ablation`);
    return res.json();
  },

  async getCostOfEvasion(): Promise<CostOfEvasionRecord[]> {
    const res = await fetch(`${API_BASE}/attacker/cost-of-evasion`);
    return res.json();
  },
};
