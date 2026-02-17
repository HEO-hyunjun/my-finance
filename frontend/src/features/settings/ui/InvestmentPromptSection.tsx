import { useState, useEffect } from 'react';
import { useInvestmentPrompt, useUpdateInvestmentPrompt, useDeleteInvestmentPrompt } from '../api/settings-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';

const MAX_LENGTH = 2000;

export function InvestmentPromptSection() {
  const { data, isLoading } = useInvestmentPrompt();
  const update = useUpdateInvestmentPrompt();
  const remove = useDeleteInvestmentPrompt();
  const [prompt, setPrompt] = useState('');

  useEffect(() => {
    if (data?.investment_prompt) {
      setPrompt(data.investment_prompt);
    }
  }, [data]);

  const handleSave = () => {
    if (prompt.trim()) {
      update.mutate(prompt.trim());
    }
  };

  const handleReset = () => {
    remove.mutate(undefined, {
      onSuccess: () => setPrompt(''),
    });
  };

  const hasChanges = prompt.trim() !== (data?.investment_prompt ?? '');
  const isSaving = update.isPending || remove.isPending;

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>투자 철학/전략</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label>나의 투자 전략</Label>
          <p className="text-xs text-muted-foreground mb-2">
            AI 챗봇과 인사이트 분석에 반영됩니다. 뉴스 요약에는 영향을 주지 않습니다.
          </p>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            maxLength={MAX_LENGTH}
            rows={4}
            placeholder="예: 장기 가치투자 선호, 배당주 중심 포트폴리오. 월 100만원 적립식 투자 중이며, 변동성보다 안정적 수익률을 중시합니다."
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm resize-y min-h-[100px]"
          />
          <p className="text-xs text-muted-foreground text-right mt-1">
            {prompt.length}/{MAX_LENGTH}
          </p>
        </div>
        <div className="flex gap-2">
          {hasChanges && prompt.trim() && (
            <Button onClick={handleSave} disabled={isSaving}>
              {update.isPending ? '저장 중...' : '저장'}
            </Button>
          )}
          {data?.investment_prompt && (
            <Button variant="outline" onClick={handleReset} disabled={isSaving}>
              {remove.isPending ? '초기화 중...' : '초기화'}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
