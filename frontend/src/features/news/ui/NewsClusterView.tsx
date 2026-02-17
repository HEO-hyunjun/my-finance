import { useState } from 'react';
import { useNewsClusters, useTriggerClustering } from '@/features/news/api';
import type { NewsCluster } from '@/shared/types';

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'text-green-600 bg-green-50',
  negative: 'text-red-600 bg-red-50',
  neutral: 'text-gray-600 bg-gray-50',
};

function ClusterCard({ cluster }: { cluster: NewsCluster }) {
  const [expanded, setExpanded] = useState(false);
  const sentimentStyle = SENTIMENT_COLORS[cluster.sentiment] ?? SENTIMENT_COLORS.neutral;

  return (
    <div className="border rounded-lg p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-sm truncate">{cluster.title}</h3>
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${sentimentStyle}`}>
              {cluster.sentiment === 'positive' ? '긍정' : cluster.sentiment === 'negative' ? '부정' : '중립'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <span>기사 {cluster.article_count}건</span>
            <span>중요도 {Math.round(cluster.importance_score * 100)}%</span>
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-blue-500 hover:text-blue-700 flex-shrink-0"
        >
          {expanded ? '접기' : '펼치기'}
        </button>
      </div>

      {/* 키워드 태그 */}
      <div className="flex flex-wrap gap-1 mb-2">
        {cluster.keywords.slice(0, 5).map((kw) => (
          <span
            key={kw}
            className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600"
          >
            {kw}
          </span>
        ))}
      </div>

      {/* 확장 영역: 요약 */}
      {expanded && (
        <div className="mt-2 pt-2 border-t text-sm text-gray-600">
          {cluster.summary}
        </div>
      )}
    </div>
  );
}

export function NewsClusterView() {
  const { data, isLoading, isError } = useNewsClusters();
  const triggerMutation = useTriggerClustering();

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-lg bg-gray-100" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border bg-white p-12 text-center">
        <p className="text-gray-500">클러스터 데이터를 불러올 수 없습니다.</p>
      </div>
    );
  }

  const clusters = data?.clusters ?? [];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {clusters.length > 0 ? `${clusters.length}개 이슈 감지` : '분석된 이슈가 없습니다'}
        </p>
        <button
          onClick={() => triggerMutation.mutate(undefined)}
          disabled={triggerMutation.isPending}
          className="text-xs px-3 py-1.5 rounded-lg border border-blue-200 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
        >
          {triggerMutation.isPending ? '분석 중...' : '새로 분석'}
        </button>
      </div>

      {clusters.length > 0 && (
        <div className="divide-y rounded-xl border bg-white">
          {clusters.map((cluster) => (
            <ClusterCard key={cluster.id} cluster={cluster} />
          ))}
        </div>
      )}
    </div>
  );
}
