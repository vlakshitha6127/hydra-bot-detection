import React, { useState, useEffect, useRef } from 'react';
import { api } from './api/client';
import type {
  Scenario,
  NetworkGraphPayload,
  EvidenceCard,
  AuditRecord,
  ReviewQueueEntry,
  AblationRow,
  BaselineRow,
  CostOfEvasionRecord,
} from './api/client';
import { TopBar } from './components/TopBar';
import { NetworkGraph } from './components/NetworkGraph';
import { EvidencePanel } from './components/EvidencePanel';
import { AuditTimeline } from './components/AuditTimeline';
import { EvaluationView } from './components/EvaluationView';
import { ReviewQueuePanel } from './components/ReviewQueuePanel';
import { Users, Layers } from 'lucide-react';

export const App: React.FC = () => {
  // Navigation & Controls state
  const [activeTab, setActiveTab] = useState<'operations' | 'audit' | 'evaluation'>('operations');
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('S2');
  const [seed, setSeed] = useState<number>(42);
  const [currentWindow, setCurrentWindow] = useState<number>(0);
  const [maxWindows, setMaxWindows] = useState<number>(10);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [showGroundTruth, setShowGroundTruth] = useState<boolean>(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(false);

  // Data states
  const [graphData, setGraphData] = useState<NetworkGraphPayload>({
    window_index: 0,
    nodes: [],
    edges: [],
    clusters: [],
  });
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [evidenceCard, setEvidenceCard] = useState<EvidenceCard | null>(null);
  const [auditRecords, setAuditRecords] = useState<AuditRecord[]>([]);
  const [isChainValid, setIsChainValid] = useState<boolean>(true);
  const [firstInvalidIndex, setFirstInvalidIndex] = useState<number | null>(null);
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueEntry[]>([]);
  const [ablationMatrix, setAblationMatrix] = useState<AblationRow[]>([]);
  const [baselineRows, setBaselineRows] = useState<BaselineRow[]>([]);
  const [costRecords, setCostRecords] = useState<CostOfEvasionRecord[]>([]);

  const [isLoadingEvidence, setIsLoadingEvidence] = useState<boolean>(false);
  const timerRef = useRef<any>(null);

  // 1. Initial Setup: Check health and fetch scenario list
  useEffect(() => {
    const init = async () => {
      try {
        const health = await api.getHealth();
        if (health.status === 'healthy') {
          setIsBackendHealthy(true);
        }
        const scList = await api.getScenarios();
        setScenarios(scList);
        await runNewSimulation('S2', 42);
      } catch (err) {
        console.error('Failed to initialize connection to BreachX backend:', err);
        setIsBackendHealthy(false);
      }
    };
    init();
  }, []);

  // 2. Run new simulation
  const runNewSimulation = async (scId: string, sVal: number) => {
    try {
      const res = await api.runSimulation(scId, sVal, 10);
      setMaxWindows(res.total_windows || 10);
      setCurrentWindow(res.total_windows - 1);
      await refreshWindowData(res.total_windows - 1);
      await refreshAuxiliaryData();
    } catch (err) {
      console.error('Error running simulation:', err);
    }
  };

  // 3. Fetch data for current window
  const refreshWindowData = async (wIdx: number) => {
    try {
      const gData = await api.getGraph(wIdx, showGroundTruth);
      setGraphData(gData);

      // Select first cluster if none selected or current not in list
      if (gData.clusters.length > 0) {
        const targetCId =
          selectedClusterId && gData.clusters.some((c) => c.cluster_id === selectedClusterId)
            ? selectedClusterId
            : gData.clusters[0].cluster_id;
        setSelectedClusterId(targetCId);
        loadEvidence(targetCId);
      } else {
        setSelectedClusterId(null);
        setEvidenceCard(null);
      }
    } catch (err) {
      console.error('Error loading window graph:', err);
    }
  };

  // 4. Fetch evidence card
  const loadEvidence = async (clusterId: string) => {
    setIsLoadingEvidence(true);
    try {
      const card = await api.getEvidenceCard(clusterId);
      setEvidenceCard(card);
    } catch (err) {
      console.error('Error loading evidence card:', err);
    } finally {
      setIsLoadingEvidence(false);
    }
  };

  // 5. Fetch audit logs and evaluation data
  const refreshAuxiliaryData = async () => {
    try {
      const auditRes = await api.getAuditLogs();
      setAuditRecords(auditRes.records);
      setIsChainValid(auditRes.is_chain_valid);
      setFirstInvalidIndex(auditRes.first_invalid_index);

      const qEntries = await api.getReviewQueue();
      setReviewQueue(qEntries);

      const ablRes = await api.getAblationMatrix();
      setAblationMatrix(ablRes.ablation_matrix);
      setBaselineRows(ablRes.baselines_comparison);

      const cRecords = await api.getCostOfEvasion();
      setCostRecords(cRecords);
    } catch (err) {
      console.error('Error loading auxiliary data:', err);
    }
  };

  // 6. Handle Scenario / Seed change
  const handleSelectScenario = (scId: string) => {
    setSelectedScenario(scId);
    runNewSimulation(scId, seed);
  };

  const handleSeedChange = (sVal: number) => {
    setSeed(sVal);
    runNewSimulation(selectedScenario, sVal);
  };

  // 7. Stepper controls
  const handleStep = async () => {
    const nextW = (currentWindow + 1) % maxWindows;
    setCurrentWindow(nextW);
    await api.stepSimulation(nextW);
    await refreshWindowData(nextW);
  };

  const handleReset = async () => {
    setIsPlaying(false);
    await api.resetSimulation();
    await runNewSimulation(selectedScenario, seed);
  };

  // 8. Auto-play loop
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = setInterval(() => {
        handleStep();
      }, 2000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isPlaying, currentWindow, maxWindows]);

  // 9. Re-fetch graph when ground-truth toggle changes
  useEffect(() => {
    refreshWindowData(currentWindow);
  }, [showGroundTruth]);

  // Audit verify and tamper demo actions
  const handleVerifyChain = async () => {
    const res = await api.verifyAuditLog();
    setIsChainValid(res.is_valid);
    setFirstInvalidIndex(res.first_invalid_index);
    alert(res.message);
  };

  const handleTamperRecord = async (index: number) => {
    const res = await api.tamperAuditLog(index);
    setIsChainValid(res.chain_valid);
    setFirstInvalidIndex(res.detected_corrupt_index);
    alert(
      `Tamper Simulation: Field modified at index ${index}. Hash chain verification failed at exact record index #${res.detected_corrupt_index}!`
    );
  };

  // Count accounts by state
  const stateCounts = {
    observe: graphData.nodes.filter((n) => n.policy_state === 0).length,
    throttle: graphData.nodes.filter((n) => n.policy_state === 1).length,
    challenge: graphData.nodes.filter((n) => n.policy_state === 2).length,
    restriction: graphData.nodes.filter((n) => n.policy_state === 3).length,
    escalation: graphData.nodes.filter((n) => n.policy_state === 4).length,
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-[#090d16] text-slate-200 overflow-hidden font-sans select-none">
      {/* Top Header & Scenario Controls */}
      <TopBar
        scenarios={scenarios}
        selectedScenario={selectedScenario}
        onSelectScenario={handleSelectScenario}
        seed={seed}
        onSeedChange={handleSeedChange}
        currentWindow={currentWindow}
        maxWindows={maxWindows}
        isPlaying={isPlaying}
        onTogglePlay={() => setIsPlaying(!isPlaying)}
        onStep={handleStep}
        onReset={handleReset}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        showGroundTruth={showGroundTruth}
        onToggleGroundTruth={() => setShowGroundTruth(!showGroundTruth)}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden p-3 flex flex-col space-y-2.5">
        {/* Operations View */}
        {activeTab === 'operations' && (
          <div className="flex-1 flex flex-col space-y-2.5 overflow-hidden">
            {/* Live Metrics Header */}
            <div className="grid grid-cols-6 gap-2 text-xs">
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded flex items-center justify-between">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Total Nodes</div>
                  <div className="text-base font-bold font-mono text-slate-100">{graphData.nodes.length}</div>
                </div>
                <Users className="w-5 h-5 text-slate-600" />
              </div>
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded flex items-center justify-between">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Detected Clusters</div>
                  <div className="text-base font-bold font-mono text-sky-400">{graphData.clusters.length}</div>
                </div>
                <Layers className="w-5 h-5 text-sky-600" />
              </div>
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded flex items-center justify-between">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Observe (State 0)</div>
                  <div className="text-base font-bold font-mono text-sky-400">{stateCounts.observe}</div>
                </div>
                <div className="w-2.5 h-2.5 rounded-full bg-sky-400" />
              </div>
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded flex items-center justify-between">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Throttled (State 1)</div>
                  <div className="text-base font-bold font-mono text-amber-400">{stateCounts.throttle}</div>
                </div>
                <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              </div>
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded flex items-center justify-between">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Challenged (State 2)</div>
                  <div className="text-base font-bold font-mono text-orange-400">{stateCounts.challenge}</div>
                </div>
                <div className="w-2.5 h-2.5 rounded-full bg-orange-400" />
              </div>
              <div className="bg-slate-900/90 border border-slate-800 p-2 rounded flex items-center justify-between">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Restricted (State 3)</div>
                  <div className="text-base font-bold font-mono text-rose-500">{stateCounts.restriction}</div>
                </div>
                <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              </div>
            </div>

            {/* Split Grid: Network Graph (Left) & Evidence Panel (Right) */}
            <div className="flex-1 grid grid-cols-12 gap-3 min-h-0">
              <div className="col-span-7 h-full flex flex-col space-y-2">
                <div className="flex-1 min-h-0">
                  <NetworkGraph
                    nodes={graphData.nodes}
                    edges={graphData.edges}
                    clusters={graphData.clusters}
                    selectedClusterId={selectedClusterId}
                    onSelectCluster={(cId) => {
                      setSelectedClusterId(cId);
                      loadEvidence(cId);
                    }}
                    showGroundTruth={showGroundTruth}
                  />
                </div>
                {/* Embedded Review Queue Panel */}
                <div className="h-36">
                  <ReviewQueuePanel
                    entries={reviewQueue}
                    selectedClusterId={selectedClusterId}
                    onSelectCluster={(cId) => {
                      setSelectedClusterId(cId);
                      loadEvidence(cId);
                    }}
                  />
                </div>
              </div>

              <div className="col-span-5 h-full min-h-0">
                <EvidencePanel
                  card={evidenceCard}
                  clusters={graphData.clusters}
                  onSelectCluster={(cId) => {
                    setSelectedClusterId(cId);
                    loadEvidence(cId);
                  }}
                  isLoading={isLoadingEvidence}
                />
              </div>
            </div>
          </div>
        )}

        {/* Audit Log View */}
        {activeTab === 'audit' && (
          <div className="flex-1 min-h-0">
            <AuditTimeline
              records={auditRecords}
              isChainValid={isChainValid}
              firstInvalidIndex={firstInvalidIndex}
              onVerifyChain={handleVerifyChain}
              onTamperRecord={handleTamperRecord}
            />
          </div>
        )}

        {/* Evaluation & Arms-Race View */}
        {activeTab === 'evaluation' && (
          <div className="flex-1 min-h-0">
            <EvaluationView
              ablationRows={ablationMatrix}
              baselineRows={baselineRows}
              costRecords={costRecords}
            />
          </div>
        )}
      </main>

      {/* Footer Disclaimer (§19.6) */}
      <footer className="bg-slate-950 border-t border-slate-900 px-4 py-1.5 flex items-center justify-between text-[10px] text-slate-500 font-mono">
        <div>
          [SYNTHETIC BENCHMARK DATASET] — Zero raw identifiers stored at rest (Invariant I8: Keyed HMAC-SHA256).
        </div>
        <div>
          BreachX 2026 / HYDRA • Authoritative Precedence: §21 &gt; §20 &gt; Architecture
        </div>
      </footer>
    </div>
  );
};

export default App;
