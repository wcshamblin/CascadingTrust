import { callExternalApi } from "./external-api.service";

const apiServerUrl = process.env.NEXT_PUBLIC_API_SERVER_URL || "http://localhost:8000";

export interface TreeNode {
  id: number;
  node_type: 'site' | 'password' | 'invite';
  is_current: boolean;
  children: TreeNode[];
}

export interface PasswordValidationResponse {
  password: string;
  redirect_url: string;
  token: string;
  trees: TreeNode[];
}

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
    data: data as PasswordValidationResponse | null,
    error,
  };
};

export interface InviteValidationResponse {
  password: string;
  redirect_url: string;
  token: string;
  trees: TreeNode[];
}

export const validateInvite = async (code: string) => {
  const config = {
    url: `${apiServerUrl}/api/invite/${encodeURIComponent(code)}`,
    method: "GET",
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data as InviteValidationResponse | null,
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

export interface AuthRedirectResponse {
  valid: boolean;
  redirect_url?: string;
  token?: string;
  site_id?: number;
  password?: string;
  trees?: TreeNode[];
}

/**
 * Check if the user has valid auth and get their redirect URL.
 * Used on invite pages to redirect already-authenticated users.
 * 
 * @param forSiteId - Optional site ID to validate token against.
 *                    If provided, only returns valid=true if the token
 *                    is for that specific site (prevents cross-site auth).
 * 
 * @returns {Promise<{data: AuthRedirectResponse | null, error?: any}>}
 */
export const checkAuthRedirect = async (forSiteId?: number) => {
  let url = `${apiServerUrl}/api/auth-redirect`;
  if (forSiteId !== undefined) {
    url += `?for_site_id=${forSiteId}`;
  }
  
  const config = {
    url,
    method: "GET",
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data as AuthRedirectResponse | null,
    error,
  };
};

/**
 * Validate a JWT token for a specific site (site-scoped validation).
 * This is the RECOMMENDED method for external sites to validate tokens.
 * It ensures the token was issued for the requesting site, preventing
 * cross-site token reuse.
 * 
 * @param token - The JWT token to validate
 * @param siteId - The site ID to validate the token against
 * 
 * @returns {Promise<{isAuthenticated: boolean, nodeId?: number, siteId?: number, error?: any}>}
 */
export const validateTokenForSite = async (token: string, siteId: number) => {
  const config = {
    url: `${apiServerUrl}/api/validate-jwt-for-site`,
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    data: {
      token,
      site_id: siteId,
    },
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
      siteId: data.site_id,
    };
  }

  return {
    isAuthenticated: false,
  };
};

// Admin API calls

export interface Node {
  id: number;
  node_type: 'site' | 'password' | 'invite';
  value: string;
  redirect_url: string | null;  // Only sites have redirect_url
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
  node_type: 'site' | 'password' | 'invite';
  value: string;
  redirect_url?: string | null;  // Only required for sites
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

// Invite generation API calls

export interface GenerateInviteRequest {
  max_uses?: number | null;
  expires_in_days?: number | null;
}

export interface GenerateInviteResponse {
  invite_code: string;
  invite_url: string;
  node_id: number;
  parent_node_id: number;
  site_id: number;
  expires_at: string | null;
}

/**
 * Generate a new invite code for the authenticated user.
 * The invite will be a child of the node used to authenticate.
 * 
 * This can be called from the host website to generate new invites.
 * Authentication is provided via the auth_token cookie or Authorization header.
 * 
 * @param token - Optional JWT token. If not provided, will use cookie auth.
 * @param options - Optional configuration for the invite (max_uses, expires_in_days)
 * 
 * @returns {Promise<{data: GenerateInviteResponse | null, error?: any}>}
 */
export const generateInvite = async (
  token?: string,
  options?: GenerateInviteRequest
) => {
  const headers: Record<string, string> = {
    "content-type": "application/json",
  };

  // If token is provided, add it to Authorization header
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config = {
    url: `${apiServerUrl}/api/generate-invite`,
    method: "POST",
    headers,
    data: options || {},
  };

  const { data, error } = await callExternalApi({ config });

  return {
    data: data as GenerateInviteResponse | null,
    error,
  };
};
