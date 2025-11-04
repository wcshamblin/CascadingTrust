import { callExternalApi } from "./external-api.service";

const apiServerUrl = process.env.NEXT_PUBLIC_API_SERVER_URL || "http://localhost:8000";

export const validatePassword = async (password: string) => {
  const config = {
    url: `${apiServerUrl}/api/validate-password`,
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    data: {
      password,
    },
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data || null,
    error,
  };
};

/**
 * Check if the user has a valid JWT authentication token.
 * This checks the auth_token cookie that was set during password validation.
 * 
 * @returns {Promise<{isAuthenticated: boolean, nodeId?: number, error?: any}>}
 */
export const checkAuthentication = async () => {
  const config = {
    url: `${apiServerUrl}/api/validate-jwt-cookie`,
    method: "GET",
  };

  const { data, error } = await callExternalApi({ config });

  if (error) {
    return {
      isAuthenticated: false,
      error,
    };
  }

  if (data && data.valid) {
    return {
      isAuthenticated: true,
      nodeId: data.node_id,
    };
  }

  return {
    isAuthenticated: false,
  };
};

// Admin API calls

export interface Node {
  id: number;
  node_type: 'password' | 'invite';
  value: string;
  redirect_url: string;
  parent_id: number | null;
  uses: number;
  max_uses: number | null;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export const listNodes = async () => {
  const config = {
    url: `${apiServerUrl}/api/admin/nodes`,
    method: "GET",
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data || null,
    error,
  };
};

export interface CreateNodeRequest {
  node_type: 'password' | 'invite';
  value: string;
  redirect_url: string;
  parent_id?: number | null;
  max_uses?: number | null;
  expires_at?: string | null;
}

export const createNode = async (request: CreateNodeRequest) => {
  const config = {
    url: `${apiServerUrl}/api/admin/nodes`,
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    data: request,
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data || null,
    error,
  };
};

export interface UpdateNodeRequest {
  redirect_url?: string;
  parent_id?: number | null;
  max_uses?: number | null;
  is_active?: boolean;
  expires_at?: string | null;
}

export const updateNode = async (nodeId: number, request: UpdateNodeRequest) => {
  const config = {
    url: `${apiServerUrl}/api/admin/nodes/${nodeId}`,
    method: "PATCH",
    headers: {
      "content-type": "application/json",
    },
    data: request,
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data || null,
    error,
  };
};

export const revokeNode = async (nodeId: number) => {
  const config = {
    url: `${apiServerUrl}/api/admin/nodes/${nodeId}/revoke`,
    method: "POST",
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data || null,
    error,
  };
};

export const deleteNode = async (nodeId: number) => {
  const config = {
    url: `${apiServerUrl}/api/admin/nodes/${nodeId}`,
    method: "DELETE",
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data || null,
    error,
  };
};
