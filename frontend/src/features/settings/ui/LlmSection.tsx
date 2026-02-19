import { useState, useEffect } from 'react';
import { useLlmSettings, useUpdateLlmSettings } from '../api/settings-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';

const MODEL_OPTIONS = [
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
  { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
];

export function LlmSection() {
  const { data: settings, isLoading } = useLlmSettings();
  const update = useUpdateLlmSettings();
  const [defaultModel, setDefaultModel] = useState('gpt-4o');
  const [inferenceModel, setInferenceModel] = useState('gpt-4o');

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (settings) {
      setDefaultModel(settings.default_model);
      setInferenceModel(settings.inference_model);
    }
  }, [settings]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSave = () => {
    update.mutate({ default_model: defaultModel, inference_model: inferenceModel });
  };

  const hasChanges = settings && (defaultModel !== settings.default_model || inferenceModel !== settings.inference_model);

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI/LLM 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label>기본 모델</Label>
          <p className="text-xs text-muted-foreground mb-1">
            대시보드 인사이트, 뉴스 요약 등에 사용됩니다.
          </p>
          <select
            value={defaultModel}
            onChange={(e) => setDefaultModel(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            {MODEL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <Label>추론 모델</Label>
          <p className="text-xs text-muted-foreground mb-1">
            챗봇 대화에 사용할 모델입니다.
          </p>
          <select
            value={inferenceModel}
            onChange={(e) => setInferenceModel(e.target.value)}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            {MODEL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        {hasChanges && (
          <Button onClick={handleSave} disabled={update.isPending}>
            {update.isPending ? '저장 중...' : '저장'}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
