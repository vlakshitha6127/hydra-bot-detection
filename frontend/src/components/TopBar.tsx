import React from 'react';
import { Play, Pause, SkipForward, RotateCcw, Shield, Eye } from 'lucide-react';
import type { Scenario } from '../api/client';

interface TopBarProps {
  scenarios: Scenario[];
  selectedScenario: string;
  onSelectScenario: (scenarioId: string) => void;
  seed: number;
  onSeedChange: (seed: number) => void;
  currentWindow: number;
  maxWindows: number;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onStep: () => void;
  onReset: () => void;
  activeTab: 'operations' | 'audit' | 'evaluation';
  onTabChange: (tab: 'operations' | 'audit' | 'evaluation') => void;
  showGroundTruth: boolean;
  onToggleGroundTruth: () => void;
  isBackendHealthy: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  scenarios,
  selectedScenario,
  onSelectScenario,
  seed,
  onSeedChange,
  currentWindow,
  maxWindows,
  isPlaying,
  onTogglePlay,
  onStep,
  onReset,
  activeTab,
  onTabChange,
  showGroundTruth,
  onToggleGroundTruth,
  isBackendHealthy,
}) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between shadow-lg">
      {/* Brand & Platform Notice */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-md">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-base text-slate-100 tracking-tight">BREACHX / HYDRA</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 bg-slate-800 text-sky-400 rounded border border-slate-700">
                v1.7
              </span>
            </div>
            <div className="text-[10px] text-slate-400">Autonomous Coordinated Bot Detection Platform</div>
          </div>
        </div>

        {/* Backend health status indicator */}
        <div className="hidden md:flex items-center gap-1.5 text-[11px] font-mono ml-3 border-l border-slate-800 pl-3">
          <span className={`w-2 h-2 rounded-full ${isBackendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
          <span className={isBackendHealthy ? 'text-slate-300' : 'text-rose-400'}>
            {isBackendHealthy ? 'ENGINE ONLINE' : 'DISCONNECTED'}
          </span>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
        <button
          onClick={() => onTabChange('operations')}
          className={`px-3 py-1.5 rounded-md font-medium transition-all ${
            activeTab === 'operations'
              ? 'bg-sky-600 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Network Operations
        </button>
        <button
          onClick={() => onTabChange('audit')}
          className={`px-3 py-1.5 rounded-md font-medium transition-all ${
            activeTab === 'audit'
              ? 'bg-sky-600 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Audit Log & Chain
        </button>
        <button
          onClick={() => onTabChange('evaluation')}
          className={`px-3 py-1.5 rounded-md font-medium transition-all ${
            activeTab === 'evaluation'
              ? 'bg-sky-600 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Evaluation & Arms-Race
        </button>
      </div>

      {/* Scenario & Discrete Window Stepper Controls */}
      <div className="flex items-center gap-3">
        {/* Scenario Select */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-400 uppercase font-mono">Scenario:</span>
          <select
            value={selectedScenario}
            onChange={(e) => onSelectScenario(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1 font-mono focus:outline-none focus:border-sky-500"
          >
            {scenarios.map((s) => (
              <option key={s.scenario_id} value={s.scenario_id}>
                {s.scenario_id}: {s.name.split(':')[1] || s.name}
              </option>
            ))}
          </select>
        </div>

        {/* Master Seed */}
        <div className="hidden lg:flex items-center gap-1 text-xs font-mono">
          <span className="text-[10px] text-slate-400 uppercase">Seed:</span>
          <input
            type="number"
            value={seed}
            onChange={(e) => onSeedChange(parseInt(e.target.value) || 42)}
            className="w-14 bg-slate-950 border border-slate-700 text-slate-200 rounded px-1.5 py-0.5 text-center focus:outline-none focus:border-sky-500"
          />
        </div>

        {/* Stepper controls */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded border border-slate-800">
          <button
            onClick={onTogglePlay}
            className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause className="w-4 h-4 text-amber-400" /> : <Play className="w-4 h-4 text-emerald-400" />}
          </button>
          <button
            onClick={onStep}
            className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
            title="Step to Next Window"
          >
            <SkipForward className="w-4 h-4" />
          </button>
          <button
            onClick={onReset}
            className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
            title="Reset Simulation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <span className="text-[11px] font-mono px-2 text-slate-400 border-l border-slate-800">
            W{currentWindow} / {maxWindows - 1}
          </span>
        </div>

        {/* Judge Ground-Truth Toggle (§12) */}
        <button
          onClick={onToggleGroundTruth}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono border transition-all ${
            showGroundTruth
              ? 'bg-purple-950/80 border-purple-600 text-purple-300'
              : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
          }`}
          title="Toggle Judge Ground-Truth Overlay (Hidden from detector)"
        >
          <Eye className="w-3.5 h-3.5" />
          <span>Ground Truth: {showGroundTruth ? 'ON' : 'OFF'}</span>
        </button>
      </div>
    </header>
  );
};
