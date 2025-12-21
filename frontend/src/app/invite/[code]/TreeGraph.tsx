"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

import { TreeNode as TreeNodeType } from "../../../../services/api.service";

// Simple node component for the invite page
function SimpleNode({ data }: { data: { nodeType: string; isCurrent: boolean } }) {
  const isSite = data.nodeType === "site";
  const isPassword = data.nodeType === "password";
  const isCurrent = data.isCurrent;

  // Size based on hierarchy level
  const size = isSite ? "w-10 h-10" : isPassword ? "w-8 h-8" : "w-6 h-6";
  
  // Label based on type
  const label = isSite ? "st" : isPassword ? "pw" : "iv";

  return (
    <div
      className={`
        flex items-center justify-center font-mono transition-all relative
        ${size}
        ${isCurrent
          ? "bg-foreground text-background"
          : "bg-background text-foreground/40 border border-foreground/30"
        }
      `}
    >
      {/* Top handle for incoming edges */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-1 !h-1 !bg-transparent !border-0 !min-w-0 !min-h-0"
      />
      
      <span className="text-[8px] uppercase">
        {label}
      </span>
      
      {/* Bottom handle for outgoing edges */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-1 !h-1 !bg-transparent !border-0 !min-w-0 !min-h-0"
      />
    </div>
  );
}

// Custom node types
const nodeTypes = {
  simple: SimpleNode,
};

// Check if a tree contains the current node
function treeContainsCurrent(node: TreeNodeType): boolean {
  if (node.is_current) return true;
  if (node.children) {
    return node.children.some((child) => treeContainsCurrent(child));
  }
  return false;
}

// Flatten a single tree to nodes and edges
function flattenTree(tree: TreeNodeType): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  function traverse(node: TreeNodeType, parentId?: string) {
    const nodeId = String(node.id);
    
    nodes.push({
      id: nodeId,
      type: "simple",
      data: {
        nodeType: node.node_type,
        isCurrent: node.is_current,
      },
      position: { x: 0, y: 0 },
    });

    if (parentId) {
      edges.push({
        id: `e${parentId}-${nodeId}`,
        source: parentId,
        target: nodeId,
        type: "smoothstep",
        style: {
          stroke: "rgba(255,255,255,0.4)",
          strokeWidth: 1,
        },
      });
    }

    if (node.children) {
      node.children.forEach((child) => traverse(child, nodeId));
    }
  }

  traverse(tree);
  
  return { nodes, edges };
}

// Layout with dagre
function getLayoutedElements(nodes: Node[], edges: Edge[]) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: "TB", nodesep: 30, ranksep: 40 });

  const nodeWidth = 48;  // Accommodate largest node (site)
  const nodeHeight = 48;

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

interface TreeGraphProps {
  trees: TreeNodeType[];
}

export default function TreeGraph({ trees }: TreeGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!trees || trees.length === 0) return { nodes: [], edges: [] };
    
    // Find the tree containing the current node (current site only)
    const currentTree = trees.find((tree) => treeContainsCurrent(tree));
    if (!currentTree) return { nodes: [], edges: [] };
    
    const { nodes, edges } = flattenTree(currentTree);
    return getLayoutedElements(nodes, edges);
  }, [trees]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  if (!trees || trees.length === 0) {
    return null;
  }

  return (
    <div className="w-72 h-72 border border-foreground/20 font-mono">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.4 }}
        minZoom={0.3}
        maxZoom={2}
        panOnDrag
        zoomOnScroll
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        defaultEdgeOptions={{
          type: "smoothstep",
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background 
          variant={BackgroundVariant.Dots} 
          color="rgba(255,255,255,0.15)" 
          gap={12} 
          size={1} 
        />
      </ReactFlow>
    </div>
  );
}
