"use client";

import { useState, useEffect } from "react";
import { 
  listNodes, 
  createNode, 
  updateNode, 
  revokeNode, 
  deleteNode,
  Node, 
  CreateNodeRequest, 
  UpdateNodeRequest 
} from "../../../services/api.service";

export default function AdminPanel() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // Form states for creating
  const [createForm, setCreateForm] = useState<CreateNodeRequest>({
    node_type: 'password',
    value: '',
    redirect_url: '',
    parent_id: null,
    max_uses: null,
    expires_at: null,
  });

  // Form states for editing
  const [editForm, setEditForm] = useState<UpdateNodeRequest>({
    redirect_url: '',
    parent_id: null,
    max_uses: null,
    is_active: true,
    expires_at: null,
  });

  const fetchNodes = async () => {
    setLoading(true);
    const { data, error } = await listNodes();
    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }
    if (data) {
      setNodes(data);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchNodes();
  }, []);

  const handleCreateNode = async (e: React.FormEvent) => {
    e.preventDefault();
    const { data, error } = await createNode(createForm);
    if (error) {
      alert(`Error creating node: ${error.message}`);
      return;
    }
    if (data) {
      // Reset form and close modal
      setCreateForm({
        node_type: 'password',
        value: '',
        redirect_url: '',
        parent_id: null,
        max_uses: null,
        expires_at: null,
      });
      setShowCreateModal(false);
      // Refresh nodes list
      fetchNodes();
    }
  };

  const handleUpdateNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNode) return;

    const { data, error } = await updateNode(selectedNode.id, editForm);
    if (error) {
      alert(`Error updating node: ${error.message}`);
      return;
    }
    if (data) {
      setShowEditModal(false);
      setSelectedNode(null);
      // Refresh nodes list
      fetchNodes();
    }
  };

  const handleRevoke = async (nodeId: number) => {
    if (!confirm('Are you sure you want to revoke this node?')) return;
    
    const { error } = await revokeNode(nodeId);
    if (error) {
      alert(`Error revoking node: ${error.message}`);
      return;
    }
    // Refresh nodes list
    fetchNodes();
  };

  const handleDelete = async (nodeId: number) => {
    if (!confirm('Are you sure you want to delete this node? This will also delete all child nodes.')) return;
    
    const { error } = await deleteNode(nodeId);
    if (error) {
      alert(`Error deleting node: ${error.message}`);
      return;
    }
    // Refresh nodes list
    fetchNodes();
  };

  const openEditModal = (node: Node) => {
    setSelectedNode(node);
    setEditForm({
      redirect_url: node.redirect_url,
      parent_id: node.parent_id,
      max_uses: node.max_uses,
      is_active: node.is_active,
      expires_at: node.expires_at,
    });
    setShowEditModal(true);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground text-xl">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-red-500 text-xl">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-bold">Admin Panel</h1>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition-colors"
          >
            Create New Node
          </button>
        </div>

        {/* Nodes Table */}
        <div className="bg-gray-900 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Value</th>
                  <th className="px-4 py-3 text-left">Redirect URL</th>
                  <th className="px-4 py-3 text-left">Parent ID</th>
                  <th className="px-4 py-3 text-left">Uses</th>
                  <th className="px-4 py-3 text-left">Max Uses</th>
                  <th className="px-4 py-3 text-left">Active</th>
                  <th className="px-4 py-3 text-left">Created</th>
                  <th className="px-4 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((node) => (
                  <tr key={node.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                    <td className="px-4 py-3">{node.id}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        node.node_type === 'password' ? 'bg-green-900 text-green-300' : 'bg-blue-900 text-blue-300'
                      }`}>
                        {node.node_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-sm">{node.value}</td>
                    <td className="px-4 py-3 text-sm truncate max-w-xs" title={node.redirect_url}>
                      {node.redirect_url}
                    </td>
                    <td className="px-4 py-3">{node.parent_id ?? 'N/A'}</td>
                    <td className="px-4 py-3">{node.uses}</td>
                    <td className="px-4 py-3">{node.max_uses ?? 'Unlimited'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${
                        node.is_active ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                      }`}>
                        {node.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">{formatDate(node.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => openEditModal(node)}
                          className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 rounded text-xs font-semibold transition-colors"
                        >
                          Edit
                        </button>
                        {node.is_active && (
                          <button
                            onClick={() => handleRevoke(node.id)}
                            className="px-3 py-1 bg-orange-600 hover:bg-orange-700 rounded text-xs font-semibold transition-colors"
                          >
                            Revoke
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(node.id)}
                          className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-xs font-semibold transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {nodes.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                No nodes found. Create your first node to get started.
              </div>
            )}
          </div>
        </div>

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-900 rounded-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
              <h2 className="text-2xl font-bold mb-4">Create New Node</h2>
              <form onSubmit={handleCreateNode} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold mb-2">Node Type</label>
                  <select
                    value={createForm.node_type}
                    onChange={(e) => setCreateForm({ ...createForm, node_type: e.target.value as 'password' | 'invite' })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                    required
                  >
                    <option value="password">Password</option>
                    <option value="invite">Invite</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2">Value</label>
                  <input
                    type="text"
                    value={createForm.value}
                    onChange={(e) => setCreateForm({ ...createForm, value: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2">Redirect URL</label>
                  <input
                    type="text"
                    value={createForm.redirect_url}
                    onChange={(e) => setCreateForm({ ...createForm, redirect_url: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>

                {createForm.node_type === 'invite' && (
                  <div>
                    <label className="block text-sm font-semibold mb-2">Parent ID (required for invites)</label>
                    <input
                      type="number"
                      value={createForm.parent_id ?? ''}
                      onChange={(e) => setCreateForm({ ...createForm, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-semibold mb-2">Max Uses (optional)</label>
                  <input
                    type="number"
                    value={createForm.max_uses ?? ''}
                    onChange={(e) => setCreateForm({ ...createForm, max_uses: e.target.value ? parseInt(e.target.value) : null })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2">Expires At (optional)</label>
                  <input
                    type="datetime-local"
                    value={createForm.expires_at ?? ''}
                    onChange={(e) => setCreateForm({ ...createForm, expires_at: e.target.value || null })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-semibold transition-colors"
                  >
                    Create
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-semibold transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Modal */}
        {showEditModal && selectedNode && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-900 rounded-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
              <h2 className="text-2xl font-bold mb-4">Edit Node #{selectedNode.id}</h2>
              <form onSubmit={handleUpdateNode} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold mb-2">Redirect URL</label>
                  <input
                    type="text"
                    value={editForm.redirect_url}
                    onChange={(e) => setEditForm({ ...editForm, redirect_url: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                  />
                </div>

                {selectedNode.node_type === 'invite' && (
                  <div>
                    <label className="block text-sm font-semibold mb-2">Parent ID</label>
                    <input
                      type="number"
                      value={editForm.parent_id ?? ''}
                      onChange={(e) => setEditForm({ ...editForm, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-semibold mb-2">Max Uses</label>
                  <input
                    type="number"
                    value={editForm.max_uses ?? ''}
                    onChange={(e) => setEditForm({ ...editForm, max_uses: e.target.value ? parseInt(e.target.value) : null })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2">Active Status</label>
                  <select
                    value={editForm.is_active ? 'true' : 'false'}
                    onChange={(e) => setEditForm({ ...editForm, is_active: e.target.value === 'true' })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                  >
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2">Expires At</label>
                  <input
                    type="datetime-local"
                    value={editForm.expires_at ?? ''}
                    onChange={(e) => setEditForm({ ...editForm, expires_at: e.target.value || null })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded font-semibold transition-colors"
                  >
                    Update
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedNode(null);
                    }}
                    className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-semibold transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

