import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import type {
  AppSettingsResponse as AppSettings,
  AppSettingsUpdate as AppSettingsUpdateRequest,
  ApiKeyCreate as ApiKeyCreateRequest,
  ApiKeyResponse as ApiKeyInfo,
  LlmSettingResponse as LlmSettings,
  LlmSettingUpdate as LlmSettingsUpdateRequest,
  InvestmentPromptResponse,
  PersonalApiKeyStatus,
  PersonalApiKeyCreated,
  PersonalApiKeyRevealed,
} from '@/shared/types/settings';

export const settingsKeys = {
  all: ['settings'] as const,
  app: () => [...settingsKeys.all, 'app'] as const,
  apiKeys: () => [...settingsKeys.all, 'api-keys'] as const,
  llm: () => [...settingsKeys.all, 'llm'] as const,
  investmentPrompt: () => [...settingsKeys.all, 'investment-prompt'] as const,
  personalApiKey: () => [...settingsKeys.all, 'personal-api-key'] as const,
};

export function useAppSettings() {
  return useQuery({
    queryKey: settingsKeys.app(),
    queryFn: async (): Promise<AppSettings> => {
      const { data } = await apiClient.get('/v1/settings');
      return data;
    },
  });
}

export function useUpdateAppSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: AppSettingsUpdateRequest): Promise<AppSettings> => {
      const { data } = await apiClient.put('/v1/settings', body);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: settingsKeys.app() }); },
  });
}

export function useApiKeys() {
  return useQuery({
    queryKey: settingsKeys.apiKeys(),
    queryFn: async (): Promise<ApiKeyInfo[]> => {
      const { data } = await apiClient.get('/v1/settings/api-keys');
      return data;
    },
  });
}

export function useUpsertApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ApiKeyCreateRequest): Promise<ApiKeyInfo> => {
      const { data } = await apiClient.put('/v1/settings/api-keys', body);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: settingsKeys.apiKeys() }); qc.invalidateQueries({ queryKey: settingsKeys.app() }); },
  });
}

export function useDeleteApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (service: string) => {
      const { data } = await apiClient.delete(`/v1/settings/api-keys/${service}`);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: settingsKeys.apiKeys() }); qc.invalidateQueries({ queryKey: settingsKeys.app() }); },
  });
}

export function useLlmSettings() {
  return useQuery({
    queryKey: settingsKeys.llm(),
    queryFn: async (): Promise<LlmSettings> => {
      const { data } = await apiClient.get('/v1/settings/llm');
      return data;
    },
  });
}

export function useUpdateLlmSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: LlmSettingsUpdateRequest): Promise<LlmSettings> => {
      const { data } = await apiClient.put('/v1/settings/llm', body);
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: settingsKeys.llm() }); qc.invalidateQueries({ queryKey: settingsKeys.app() }); },
  });
}

export function useInvestmentPrompt() {
  return useQuery({
    queryKey: settingsKeys.investmentPrompt(),
    queryFn: async (): Promise<InvestmentPromptResponse> => {
      const { data } = await apiClient.get('/v1/settings/investment-prompt');
      return data;
    },
  });
}

export function useUpdateInvestmentPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (investment_prompt: string): Promise<InvestmentPromptResponse> => {
      const { data } = await apiClient.put('/v1/settings/investment-prompt', { investment_prompt });
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: settingsKeys.investmentPrompt() }); qc.invalidateQueries({ queryKey: settingsKeys.app() }); },
  });
}

export function useDeleteInvestmentPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.delete('/v1/settings/investment-prompt');
      return data;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: settingsKeys.investmentPrompt() }); qc.invalidateQueries({ queryKey: settingsKeys.app() }); },
  });
}

// --- Personal API Key ---

export function usePersonalApiKeyStatus() {
  return useQuery({
    queryKey: settingsKeys.personalApiKey(),
    queryFn: async (): Promise<PersonalApiKeyStatus> => {
      const { data } = await apiClient.get('/v1/settings/personal-api-key');
      return data;
    },
  });
}

export function useGeneratePersonalApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<PersonalApiKeyCreated> => {
      const { data } = await apiClient.post('/v1/settings/personal-api-key');
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.personalApiKey() });
    },
  });
}

export function useRevealPersonalApiKey() {
  return useMutation({
    mutationFn: async (password: string): Promise<PersonalApiKeyRevealed> => {
      const { data } = await apiClient.post('/v1/settings/personal-api-key/reveal', { password });
      return data;
    },
  });
}

export function useRevokePersonalApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.delete('/v1/settings/personal-api-key');
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: settingsKeys.personalApiKey() });
    },
  });
}
