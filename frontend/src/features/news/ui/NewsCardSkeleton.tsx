import { Skeleton } from '@/shared/ui/skeleton';

export function NewsCardSkeleton() {
  return (
    <div className="flex gap-4 px-4 py-3.5">
      {/* 썸네일 스켈레톤 (데스크톱) */}
      <Skeleton className="hidden md:block h-24 w-24 flex-shrink-0 rounded-lg" />

      <div className="min-w-0 flex-1 space-y-2">
        {/* 제목 */}
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />

        {/* 출처 + 시간 */}
        <div className="flex gap-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-12" />
        </div>

        {/* 스니펫 */}
        <Skeleton className="h-3 w-full" />
      </div>
    </div>
  );
}
