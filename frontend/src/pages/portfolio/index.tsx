import { TargetsEditor } from '@/features/portfolio/ui/TargetsEditor';
import { RebalancingPanel } from '@/features/portfolio/ui/RebalancingPanel';
import { AlertsList } from '@/features/portfolio/ui/AlertsList';

export function Component() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">포트폴리오</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          자산 유형별 목표 비중을 설정하고 리밸런싱 상태를 점검합니다.
        </p>
      </div>
      <TargetsEditor />
      <RebalancingPanel />
      <AlertsList />
    </div>
  );
}
