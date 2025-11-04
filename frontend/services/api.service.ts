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
