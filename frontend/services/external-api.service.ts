import axios, { AxiosRequestConfig } from "axios";

interface ApiResponse<T> {
  data: T | null;
  error: {
    message: string;
  } | null;
}

interface CallExternalApiOptions {
  config: AxiosRequestConfig;
}

export const callExternalApi = async <T = any>(
  options: CallExternalApiOptions
): Promise<ApiResponse<T>> => {
  try {
    // Enable credentials to allow cookies to be sent and received
    const configWithCredentials = {
      ...options.config,
      withCredentials: true,
    };
    
    const response = await axios(configWithCredentials);
    const { data } = response;

    return {
      data,
      error: null,
    };
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error;

      const { response } = axiosError;

      let message = "http request failed";

      if (response && response.statusText) {
        message = response.statusText;
      }

      if (axiosError.message) {
        message = axiosError.message;
      }

      if (response && response.data && response.data.message) {
        message = response.data.message;
      }

      return {
        data: null,
        error: {
          message,
        },
      };
    }

    return {
      data: null,
      error: {
        message: (error as Error).message,
      },
    };
  }
};

