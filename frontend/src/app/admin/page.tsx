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

  const [createForm, setCreateForm] = useState<CreateNodeRequest>({
    node_type: 'site',
    value: '',
    redirect_url: '',
    parent_id: null,
    max_uses: null,
    expires_at: null,
  });

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
      setCreateForm({
        node_type: 'site',
        value: '',
        redirect_url: '',
        parent_id: null,
        max_uses: null,
        expires_at: null,
      });
      setShowCreateModal(false);
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
      fetchNodes();
    }
  };

  const handleRevoke = async (nodeId: number) => {
    if (!confirm('Revoke this node?')) return;
    
    const { error } = await revokeNode(nodeId);
    if (error) {
      alert(`Error revoking node: ${error.message}`);
      return;
    }
    fetchNodes();
  };

  const handleDelete = async (nodeId: number) => {
    if (!confirm('Delete this node and all children?')) return;
    
    const { error } = await deleteNode(nodeId);
    if (error) {
      alert(`Error deleting node: ${error.message}`);
      return;
    }
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
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString();
  };

  // Organize nodes hierarchically
  const organizeNodesHierarchically = () => {
    const sites = nodes.filter(node => node.node_type === 'site').sort((a, b) => a.id - b.id);
    const passwords = nodes.filter(node => node.node_type === 'password').sort((a, b) => a.id - b.id);
    const invites = nodes.filter(node => node.node_type === 'invite').sort((a, b) => a.id - b.id);
    
    const organized: Array<{ node: Node; depth: number }> = [];
    
    sites.forEach(site => {
      organized.push({ node: site, depth: 0 });
      
      const sitePasswords = passwords.filter(p => p.parent_id === site.id);
      sitePasswords.forEach(password => {
        organized.push({ node: password, depth: 1 });
        
        const passwordInvites = invites.filter(i => i.parent_id === password.id);
        passwordInvites.forEach(invite => {
          organized.push({ node: invite, depth: 2 });
        });
      });
    });
    
    const siteIds = new Set(sites.map(s => s.id));
    const orphanedPasswords = passwords.filter(p => !siteIds.has(p.parent_id ?? -1));
    orphanedPasswords.forEach(password => {
      organized.push({ node: password, depth: 0 });
      
      const passwordInvites = invites.filter(i => i.parent_id === password.id);
      passwordInvites.forEach(invite => {
        organized.push({ node: invite, depth: 1 });
      });
    });
    
    const passwordIds = new Set(passwords.map(p => p.id));
    const orphanedInvites = invites.filter(i => !passwordIds.has(i.parent_id ?? -1));
    orphanedInvites.forEach(orphan => {
      organized.push({ node: orphan, depth: 0 });
    });
    
    return organized;
  };

  const organizedNodes = organizeNodesHierarchically();

  // Stats
  const stats = {
    total: nodes.length,
    sites: nodes.filter(n => n.node_type === 'site').length,
    passwords: nodes.filter(n => n.node_type === 'password').length,
    invites: nodes.filter(n => n.node_type === 'invite').length,
    active: nodes.filter(n => n.is_active).length,
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center font-mono">
        <span className="text-foreground/60">loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center font-mono">
        <span className="text-foreground/60">error: {error}</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-6 font-mono">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-start mb-6 border-b border-foreground/20 pb-4">
          <div>
            <h1 className="text-lg uppercase tracking-widest">admin</h1>
            <div className="text-foreground/40 text-xs mt-2 flex gap-4">
              <span>{stats.total} nodes</span>
              <span>{stats.sites} st</span>
              <span>{stats.passwords} pw</span>
              <span>{stats.invites} iv</span>
              <span>{stats.active} active</span>
            </div>
          </div>
          <div className="flex gap-2">
            <a
              href="/admin/graph"
              className="px-3 py-1.5 border border-foreground/30 text-foreground/60 hover:text-foreground hover:border-foreground/60 text-xs uppercase"
            >
              graph
            </a>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1.5 bg-foreground text-background text-xs uppercase"
            >
              + new
            </button>
          </div>
        </div>

        {/* Nodes List */}
        <div className="border border-foreground/20">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-2 px-3 py-2 border-b border-foreground/20 text-foreground/40 text-xs uppercase">
            <div className="col-span-1">id</div>
            <div className="col-span-1">type</div>
            <div className="col-span-2">value</div>
            <div className="col-span-2">redirect</div>
            <div className="col-span-1">uses</div>
            <div className="col-span-1">status</div>
            <div className="col-span-2">created</div>
            <div className="col-span-2">actions</div>
          </div>

          {/* Table Body */}
          {organizedNodes.map(({ node, depth }) => (
            <div
              key={node.id}
              className={`
                grid grid-cols-12 gap-2 px-3 py-2 border-b border-foreground/10 text-xs
                ${!node.is_active ? 'text-foreground/30' : ''}
              `}
            >
              <div className="col-span-1" style={{ paddingLeft: `${depth * 12}px` }}>
                {depth > 0 && <span className="text-foreground/20 mr-1">└</span>}
                {node.id}
              </div>
              <div className="col-span-1">
                <span className={`
                  inline-block w-6 h-6 flex items-center justify-center text-[10px] uppercase
                  ${node.node_type === 'site' ? 'bg-foreground text-background' : 
                    node.node_type === 'password' ? 'border border-foreground/40' : 
                    'border border-foreground/20'}
                `}>
                  {node.node_type === 'site' ? 'st' : node.node_type === 'password' ? 'pw' : 'iv'}
                </span>
              </div>
              <div className="col-span-2 truncate" title={node.value}>
                {node.value}
              </div>
              <div className="col-span-2 truncate text-foreground/40" title={node.redirect_url || ''}>
                {node.node_type === 'site' ? node.redirect_url : '—'}
              </div>
              <div className="col-span-1">
                {node.uses}{node.max_uses ? `/${node.max_uses}` : ''}
              </div>
              <div className="col-span-1">
                <span className={node.is_active ? 'text-foreground' : 'text-foreground/30'}>
                  {node.is_active ? 'on' : 'off'}
                </span>
              </div>
              <div className="col-span-2 text-foreground/40">
                {formatDate(node.created_at)}
              </div>
              <div className="col-span-2 flex gap-2">
                <button
                  onClick={() => openEditModal(node)}
                  className="text-foreground/40 hover:text-foreground"
                >
                  edit
                </button>
                {node.is_active && (
                  <button
                    onClick={() => handleRevoke(node.id)}
                    className="text-foreground/40 hover:text-foreground"
                  >
                    revoke
                  </button>
                )}
                <button
                  onClick={() => handleDelete(node.id)}
                  className="text-foreground/40 hover:text-foreground"
                >
                  del
                </button>
              </div>
            </div>
          ))}
          
          {nodes.length === 0 && (
            <div className="px-3 py-6 text-center text-foreground/30 text-xs">
              no nodes. create one to start.
            </div>
          )}
        </div>

        {/* Create Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-background/90 flex items-center justify-center p-4 z-50">
            <div className="border border-foreground/20 bg-background p-6 max-w-sm w-full">
              <h2 className="text-sm uppercase tracking-wider mb-4">new node</h2>
              <form onSubmit={handleCreateNode} className="space-y-4">
                <div>
                  <label className="block text-xs text-foreground/40 mb-1">type</label>
                  <select
                    value={createForm.node_type}
                    onChange={(e) => setCreateForm({ ...createForm, node_type: e.target.value as 'site' | 'password' | 'invite', parent_id: null })}
                    className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                    required
                  >
                    <option value="site">site</option>
                    <option value="password">password</option>
                    <option value="invite">invite</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-foreground/40 mb-1">
                    {createForm.node_type === 'site' ? 'name' : createForm.node_type === 'password' ? 'password' : 'code'}
                  </label>
                  <input
                    type="text"
                    value={createForm.value}
                    onChange={(e) => setCreateForm({ ...createForm, value: e.target.value })}
                    className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                    required
                  />
                </div>

                {createForm.node_type === 'site' && (
                  <div>
                    <label className="block text-xs text-foreground/40 mb-1">redirect url</label>
                    <input
                      type="text"
                      value={createForm.redirect_url || ''}
                      onChange={(e) => setCreateForm({ ...createForm, redirect_url: e.target.value })}
                      className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                      placeholder="https://..."
                      required
                    />
                  </div>
                )}

                {createForm.node_type === 'password' && (
                  <div>
                    <label className="block text-xs text-foreground/40 mb-1">parent site</label>
                    <select
                      value={createForm.parent_id ?? ''}
                      onChange={(e) => setCreateForm({ ...createForm, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                      className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                      required
                    >
                      <option value="">select...</option>
                      {nodes.filter(n => n.node_type === 'site').map(site => (
                        <option key={site.id} value={site.id}>#{site.id} {site.value}</option>
                      ))}
                    </select>
                  </div>
                )}

                {createForm.node_type === 'invite' && (
                  <div>
                    <label className="block text-xs text-foreground/40 mb-1">parent password</label>
                    <select
                      value={createForm.parent_id ?? ''}
                      onChange={(e) => setCreateForm({ ...createForm, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                      className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                      required
                    >
                      <option value="">select...</option>
                      {nodes.filter(n => n.node_type === 'password').map(pw => (
                        <option key={pw.id} value={pw.id}>#{pw.id} {pw.value}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-xs text-foreground/40 mb-1">max uses (optional)</label>
                  <input
                    type="number"
                    value={createForm.max_uses ?? ''}
                    onChange={(e) => setCreateForm({ ...createForm, max_uses: e.target.value ? parseInt(e.target.value) : null })}
                    className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                  />
                </div>

                <div>
                  <label className="block text-xs text-foreground/40 mb-1">expires (optional)</label>
                  <input
                    type="datetime-local"
                    value={createForm.expires_at ?? ''}
                    onChange={(e) => setCreateForm({ ...createForm, expires_at: e.target.value || null })}
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
          <div className="fixed inset-0 bg-background/90 flex items-center justify-center p-4 z-50">
            <div className="border border-foreground/20 bg-background p-6 max-w-sm w-full">
              <h2 className="text-sm uppercase tracking-wider mb-4">
                edit {selectedNode.node_type} #{selectedNode.id}
              </h2>
              <form onSubmit={handleUpdateNode} className="space-y-4">
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

                {selectedNode.node_type === 'password' && (
                  <div>
                    <label className="block text-xs text-foreground/40 mb-1">parent site</label>
                    <select
                      value={editForm.parent_id ?? ''}
                      onChange={(e) => setEditForm({ ...editForm, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                      className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                    >
                      <option value="">select...</option>
                      {nodes.filter(n => n.node_type === 'site').map(site => (
                        <option key={site.id} value={site.id}>#{site.id} {site.value}</option>
                      ))}
                    </select>
                  </div>
                )}

                {selectedNode.node_type === 'invite' && (
                  <div>
                    <label className="block text-xs text-foreground/40 mb-1">parent password</label>
                    <select
                      value={editForm.parent_id ?? ''}
                      onChange={(e) => setEditForm({ ...editForm, parent_id: e.target.value ? parseInt(e.target.value) : null })}
                      className="w-full px-2 py-1.5 bg-background border border-foreground/30 text-xs focus:outline-none focus:border-foreground"
                    >
                      <option value="">select...</option>
                      {nodes.filter(n => n.node_type === 'password').map(pw => (
                        <option key={pw.id} value={pw.id}>#{pw.id} {pw.value}</option>
                      ))}
                    </select>
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
                    <option value="on">on</option>
                    <option value="off">off</option>
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
                    onClick={() => {
                      setShowEditModal(false);
                      setSelectedNode(null);
                    }}
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
    </div>
  );
}
