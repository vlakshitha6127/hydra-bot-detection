import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import type { GraphNode, GraphEdge, ClusterSummary } from '../api/client';

interface NetworkGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: ClusterSummary[];
  selectedClusterId: string | null;
  onSelectCluster: (clusterId: string) => void;
  showGroundTruth: boolean;
}

const STATE_HALO_COLORS: Record<number, string> = {
  0: '#38bdf8', // Observe (Sky blue)
  1: '#fbbf24', // Throttle (Amber)
  2: '#f97316', // Challenge (Orange)
  3: '#ef4444', // Restriction (Red)
  4: '#a855f7', // Human Escalation (Purple)
};

export const NetworkGraph: React.FC<NetworkGraphProps> = ({
  nodes,
  edges,
  clusters: _clusters,
  selectedClusterId,
  onSelectCluster,
  showGroundTruth,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Convert nodes to Cytoscape format
    const cyNodes = nodes.map((n) => {
      let truthColor = '#64748b';
      if (showGroundTruth && n.actor_type_truth) {
        if (n.actor_type_truth === 'bot') truthColor = '#ef4444';
        else if (n.actor_type_truth === 'decoy_fan') truthColor = '#10b981';
        else if (n.actor_type_truth === 'decoy_news') truthColor = '#3b82f6';
        else if (n.actor_type_truth === 'decoy_nat') truthColor = '#f59e0b';
        else truthColor = '#475569';
      }

      return {
        data: {
          id: n.id,
          label: n.id,
          clusterId: n.cluster_id || 'unassigned',
          policyState: n.policy_state,
          haloColor: STATE_HALO_COLORS[n.policy_state] || '#38bdf8',
          truthColor,
          isEligible: n.is_eligible,
        },
      };
    });

    // Convert edges to Cytoscape format
    const cyEdges = edges.map((e, idx) => ({
      data: {
        id: `e_${e.source}_${e.target}_${idx}`,
        source: e.source,
        target: e.target,
        weight: e.weight,
        edgeType: e.edge_types[0] || 'generic',
      },
    }));

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...cyNodes, ...cyEdges],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#1e293b',
            'border-width': 2,
            'border-color': 'data(haloColor)',
            'border-opacity': 0.9,
            width: 24,
            height: 24,
            label: 'data(label)',
            'font-size': '8px',
            color: '#94a3b8',
            'text-valign': 'bottom',
            'text-margin-y': 4,
          },
        },
        {
          selector: 'node[?isEligible]',
          style: {
            width: 28,
            height: 28,
            'background-color': '#334155',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 'mapData(weight, 0.1, 1.0, 1, 3)',
            'line-color': '#475569',
            opacity: 0.5,
            'curve-style': 'bezier',
          },
        },
        {
          selector: 'edge[edgeType = "device"]',
          style: {
            'line-color': '#ec4899', // Pink/Magenta for device sharing
            opacity: 0.8,
            width: 2.5,
          },
        },
        {
          selector: 'edge[edgeType = "content"]',
          style: {
            'line-color': '#10b981', // Emerald for semantic content
            opacity: 0.6,
          },
        },
        {
          selector: 'edge[edgeType = "timing"]',
          style: {
            'line-color': '#eab308', // Yellow for synchrony
            opacity: 0.6,
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 4,
            'border-color': '#ffffff',
            'background-color': '#3b82f6',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        randomize: false,
        componentSpacing: 60,
        nodeOverlap: 20,
        idealEdgeLength: () => 40,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });

    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const cId = node.data('clusterId');
      if (cId && cId !== 'unassigned') {
        onSelectCluster(cId);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [nodes, edges, showGroundTruth]);

  // Highlight selected cluster
  useEffect(() => {
    if (!cyRef.current || !selectedClusterId) return;
    const cy = cyRef.current;
    cy.batch(() => {
      cy.nodes().forEach((n) => {
        if (n.data('clusterId') === selectedClusterId) {
          n.animate({
            style: {
              'border-width': 4,
              'border-color': '#ffffff',
            },
            duration: 200,
          });
        } else {
          n.style({
            'border-width': 2,
            'border-color': n.data('haloColor'),
          });
        }
      });
    });
  }, [selectedClusterId]);

  return (
    <div className="relative w-full h-full bg-[#080c14] rounded-lg border border-slate-800 overflow-hidden shadow-inner">
      <div ref={containerRef} className="w-full h-full" />
      
      {/* Legend Overlay */}
      <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur-md border border-slate-700/60 rounded px-3 py-2 text-xs text-slate-300 pointer-events-none shadow-lg">
        <div className="font-semibold text-slate-200 mb-1">State Halo (Graduated Ladder)</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
            <span>State 0: Observe</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span>State 1: Throttle</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
            <span>State 2: Challenge</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span>State 3: Restriction</span>
          </div>
        </div>
        <div className="border-t border-slate-700 my-1.5 pt-1 flex items-center gap-3">
          <span className="flex items-center gap-1 text-[10px]">
            <span className="w-3 h-0.5 bg-pink-500" /> Device Link
          </span>
          <span className="flex items-center gap-1 text-[10px]">
            <span className="w-3 h-0.5 bg-emerald-500" /> Content Link
          </span>
          <span className="flex items-center gap-1 text-[10px]">
            <span className="w-3 h-0.5 bg-yellow-400" /> Timing Link
          </span>
        </div>
      </div>
    </div>
  );
};
