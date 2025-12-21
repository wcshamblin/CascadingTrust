"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  useNodesState,
  useEdgesState,
  Panel,
  BackgroundVariant,
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

import { 
  listNodes, 
  createNode,
  updateNode,
  revokeNode,
  deleteNode,
  Node as ApiNode,
  CreateNodeRequest,
  UpdateNodeRequest,
} from "../../../../services/api.service";
import SiteNode from "./SiteNode";
import PasswordNode from "./PasswordNode";
import InviteNode from "./InviteNode";

const nodeTypes = {
  site: SiteNode,
  password: PasswordNode,
  invite: InviteNode,
};

const NODE_WIDTH = 176;
const NODE_HEIGHT = 100;

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 60 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
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
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

const transformToFlowElements = (apiNodes: ApiNode[], selectedId: number | null) => {
  const nodes: Node[] = apiNodes.map((node) => ({
    id: String(node.id),
    type: node.node_type,
    data: {
      id: node.id,
      value: node.value,
      redirectUrl: node.redirect_url,
      uses: node.uses,
      maxUses: node.max_uses,
      isActive: node.is_active,
      createdAt: node.created_at,
      expiresAt: node.expires_at,
      parentId: node.parent_id,
      isSelected: node.id === selectedId,
    },
    position: { x: 0, y: 0 },
  }));

  const edges: Edge[] = apiNodes
    .filter((node) => node.parent_id !== null)
    .map((node) => ({
      id: `e${node.parent_id}-${node.id}`,
      source: String(node.parent_id),
      target: String(node.id),
      type: "smoothstep",
      style: {
        stroke: node.is_active ? "rgba(237,237,237,0.4)" : "rgba(237,237,237,0.15)",
        strokeWidth: 1,
      },
    }));

  return getLayoutedElements(nodes, edges);
};

export default function GraphPage() {
  const [apiNodes, setApiNodes] = useState<ApiNode[]>([]);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Selection state
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [createNodeType, setCreateNodeType] = useState<'password' | 'invite'>('password');
  
  // Form states
  const [createForm, setCreateForm] = useState({ value: '', max_uses: '', expires_at: '' });
  const [editForm, setEditForm] = useState<UpdateNodeRequest>({
    redirect_url: '',
    max_uses: null,
    is_active: true,
    expires_at: null,
  });

  const selectedNode = useMemo(() => 
    apiNodes.find(n => n.id === selectedNodeId) || null
  , [apiNodes, selectedNodeId]);

  const fetchNodes = useCallback(async () => {
    setLoading(true);
    const { data, error } = await listNodes();
    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }
    if (data) {
      setApiNodes(data);
    }
    setLoading(false);
  }, []);

  // Update flow elements when apiNodes or selection changes
  useEffect(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = transformToFlowElements(apiNodes, selectedNodeId);
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [apiNodes, selectedNodeId, setNodes, setEdges]);

  useEffect(() => {
    fetchNodes();
  }, [fetchNodes]);

  // Handle node click
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const nodeId = parseInt(node.id);
    setSelectedNodeId(prev => prev === nodeId ? null : nodeId);
  }, []);

  // Handle pane click to deselect
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  // Actions
  const handleAddChild = () => {
    if (!selectedNode) return;
    const childType = selectedNode.node_type === 'site' ? 'password' : 'invite';
    setCreateNodeType(childType);
    setCreateForm({ value: '', max_uses: '', expires_at: '' });
    setShowCreateModal(true);
  };

  const handleEdit = () => {
    if (!selectedNode) return;
    setEditForm({
      redirect_url: selectedNode.redirect_url || '',
      max_uses: selectedNode.max_uses,
      is_active: selectedNode.is_active,
      expires_at: selectedNode.expires_at,
    });
    setShowEditModal(true);
  };

  const handleDisable = async () => {
    if (!selectedNode) return;
    const { error } = await revokeNode(selectedNode.id);
    if (error) {
      alert(`Error: ${error.message}`);
    } else {
      fetchNodes();
    }
  };

  const handleEnable = async () => {
    if (!selectedNode) return;
    const { error } = await updateNode(selectedNode.id, { is_active: true });
    if (error) {
      alert(`Error: ${error.message}`);
    } else {
      fetchNodes();
    }
  };

  const handleDelete = async () => {
    if (!selectedNode) return;
    if (!confirm(`Delete ${selectedNode.node_type} "${selectedNode.value}" and all children?`)) {
      return;
    }
    const { error } = await deleteNode(selectedNode.id);
    if (error) {
      alert(`Error: ${error.message}`);
    } else {
      setSelectedNodeId(null);
      fetchNodes();
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNode) return;
    const request: CreateNodeRequest = {
      node_type: createNodeType,
      value: createForm.value,
      parent_id: selectedNode.id,
      max_uses: createForm.max_uses ? parseInt(createForm.max_uses) : null,
      expires_at: createForm.expires_at || null,
    };
    const { error } = await createNode(request);
    if (error) {
      alert(`Error: ${error.message}`);
    } else {
      setShowCreateModal(false);
      fetchNodes();
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNode) return;
    const { error } = await updateNode(selectedNode.id, editForm);
    if (error) {
      alert(`Error: ${error.message}`);
    } else {
      setShowEditModal(false);
      fetchNodes();
    }
  };

  const stats = useMemo(() => {
    const sites = apiNodes.filter((n) => n.node_type === "site");
    const passwords = apiNodes.filter((n) => n.node_type === "password");
    const invites = apiNodes.filter((n) => n.node_type === "invite");
    const active = apiNodes.filter((n) => n.is_active);
    return {
      total: apiNodes.length,
      sites: sites.length,
      passwords: passwords.length,
      invites: invites.length,
      active: active.length,
    };
  }, [apiNodes]);

  if (loading) {
    return (
      <div className="h-screen bg-background flex items-center justify-center font-mono">
        <span className="text-foreground/40 text-xs">loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen bg-background flex items-center justify-center font-mono">
        <div className="border border-foreground/20 p-4">
          <span className="text-foreground/60 text-xs">error: {error}</span>
          <button
            onClick={fetchNodes}
            className="ml-4 text-foreground/40 hover:text-foreground text-xs"
          >
            retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-background font-mono">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.2}
        maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
        defaultEdgeOptions={{
          type: "smoothstep",
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background 
          variant={BackgroundVariant.Dots} 
          color="rgba(237,237,237,0.15)" 
          gap={16} 
          size={1} 
        />

        {/* Header */}
        <Panel position="top-left" className="!m-4">
          <div className="border border-foreground/20 bg-background p-3">
            <div className="text-xs uppercase tracking-wider mb-2">graph view</div>
            <a
              href="/admin"
              className="text-foreground/40 hover:text-foreground text-xs"
            >
              ← back
            </a>
          </div>
        </Panel>

        {/* Stats */}
        <Panel position="top-right" className="!m-4">
          <div className="border border-foreground/20 bg-background p-3">
            <div className="text-xs text-foreground/40 space-y-1">
              <div className="flex justify-between gap-4">
                <span>total</span>
                <span className="text-foreground">{stats.total}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>sites</span>
                <span className="text-foreground">{stats.sites}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>passwords</span>
                <span className="text-foreground">{stats.passwords}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>invites</span>
                <span className="text-foreground">{stats.invites}</span>
              </div>
              <div className="flex justify-between gap-4 pt-1 border-t border-foreground/10">
                <span>active</span>
                <span className="text-foreground">{stats.active}</span>
              </div>
            </div>
          </div>
        </Panel>

        {/* Legend */}
        <Panel position="bottom-left" className="!m-4">
          <div className="border border-foreground/20 bg-background p-3">
            <div className="text-xs text-foreground/40 space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-foreground" />
                <span>Site</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border border-foreground/40" />
                <span>Password</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border border-foreground/20" />
                <span>Invite</span>
              </div>
              <div className="pt-1.5 border-t border-foreground/10 text-[10px]">
                click node for options
              </div>
            </div>
          </div>
        </Panel>

        {/* Selected Node Actions */}
        {selectedNode && (
          <Panel position="bottom-right" className="!m-4">
            <div className="border border-foreground/30 bg-background">
              <div className="px-3 py-2 border-b border-foreground/20 text-xs">
                <span className="text-foreground/40 uppercase">{selectedNode.node_type}</span>
                <span className="text-foreground/30 mx-1.5">·</span>
                <span className="text-foreground">#{selectedNode.id}</span>
                <span className="text-foreground/30 mx-1.5">·</span>
                <span className="text-foreground/60 truncate max-w-[120px] inline-block align-bottom">{selectedNode.value}</span>
              </div>
              <div className="p-1">
                {selectedNode.node_type !== 'invite' && (
                  <button
                    onClick={handleAddChild}
                    className="w-full px-3 py-1.5 text-left text-xs hover:bg-foreground/10"
                  >
                    + add {selectedNode.node_type === 'site' ? 'password' : 'invite'}
                  </button>
                )}
                <button
                  onClick={handleEdit}
                  className="w-full px-3 py-1.5 text-left text-xs hover:bg-foreground/10"
                >
                  edit
                </button>
                {selectedNode.is_active ? (
                  <button
                    onClick={handleDisable}
                    className="w-full px-3 py-1.5 text-left text-xs hover:bg-foreground/10"
                  >
                    disable
                  </button>
                ) : (
                  <button
                    onClick={handleEnable}
                    className="w-full px-3 py-1.5 text-left text-xs hover:bg-foreground/10"
                  >
                    enable
                  </button>
                )}
                <button
                  onClick={handleDelete}
                  className="w-full px-3 py-1.5 text-left text-xs hover:bg-foreground/10 text-foreground/50"
                >
                  delete
                </button>
              </div>
            </div>
          </Panel>
        )}

        {/* Refresh - only show when no node selected */}
        {!selectedNode && (
          <Panel position="bottom-right" className="!m-4">
            <button
              onClick={fetchNodes}
              className="border border-foreground/20 bg-background px-3 py-1.5 text-foreground/40 hover:text-foreground text-xs"
            >
              refresh
            </button>
          </Panel>
        )}
      </ReactFlow>

      {/* Create Child Modal */}
      {showCreateModal && selectedNode && (
        <div className="fixed inset-0 bg-background/90 flex items-center justify-center z-50 font-mono">
          <div className="border border-foreground/20 bg-background p-6 max-w-sm w-full">
            <h2 className="text-sm uppercase tracking-wider mb-4">
              new {createNodeType}
            </h2>
            <div className="text-xs text-foreground/40 mb-4">
              parent: {selectedNode.node_type} #{selectedNode.id}
            </div>
            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs text-foreground/40 mb-1">
                  {createNodeType === 'password' ? 'password' : 'invite code'}
                </label>
                <input
                  type="text"
                  value={createForm.value}
                  onChange={(e) => setCreateForm({ ...createForm, value: e.target.value })}
                  className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-xs text-foreground/40 mb-1">max uses (optional)</label>
                <input
                  type="number"
                  value={createForm.max_uses}
                  onChange={(e) => setCreateForm({ ...createForm, max_uses: e.target.value })}
                  className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                />
              </div>

              <div>
                <label className="block text-xs text-foreground/40 mb-1">expires (optional)</label>
                <input
                  type="datetime-local"
                  value={createForm.expires_at}
                  onChange={(e) => setCreateForm({ ...createForm, expires_at: e.target.value })}
                  className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 px-3 py-1.5 bg-foreground text-background text-xs uppercase"
                >
                  create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-3 py-1.5 border border-foreground/30 text-xs uppercase"
                >
                  cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedNode && (
        <div className="fixed inset-0 bg-background/90 flex items-center justify-center z-50 font-mono">
          <div className="border border-foreground/20 bg-background p-6 max-w-sm w-full">
            <h2 className="text-sm uppercase tracking-wider mb-4">
              edit {selectedNode.node_type} #{selectedNode.id}
            </h2>
            <form onSubmit={handleEditSubmit} className="space-y-4">
              {selectedNode.node_type === 'site' && (
                <div>
                  <label className="block text-xs text-foreground/40 mb-1">redirect url</label>
                  <input
                    type="text"
                    value={editForm.redirect_url || ''}
                    onChange={(e) => setEditForm({ ...editForm, redirect_url: e.target.value })}
                    className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs text-foreground/40 mb-1">max uses</label>
                <input
                  type="number"
                  value={editForm.max_uses ?? ''}
                  onChange={(e) => setEditForm({ ...editForm, max_uses: e.target.value ? parseInt(e.target.value) : null })}
                  className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                />
              </div>

              <div>
                <label className="block text-xs text-foreground/40 mb-1">status</label>
                <select
                  value={editForm.is_active ? 'on' : 'off'}
                  onChange={(e) => setEditForm({ ...editForm, is_active: e.target.value === 'on' })}
                  className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                >
                  <option value="on">active</option>
                  <option value="off">inactive</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-foreground/40 mb-1">expires</label>
                <input
                  type="datetime-local"
                  value={editForm.expires_at ?? ''}
                  onChange={(e) => setEditForm({ ...editForm, expires_at: e.target.value || null })}
                  className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 px-3 py-1.5 bg-foreground text-background text-xs uppercase"
                >
                  save
                </button>
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 px-3 py-1.5 border border-foreground/30 text-xs uppercase"
                >
                  cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
