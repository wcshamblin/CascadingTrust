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
