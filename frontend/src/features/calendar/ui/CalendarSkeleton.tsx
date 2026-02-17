import { Skeleton } from '@/shared/ui/skeleton';
import { Card, CardContent } from '@/shared/ui/card';

export function CalendarSkeleton() {
  return (
    <div className="space-y-4">
      {/* 월 요약 스켈레톤 */}
      <Card>
        <CardContent className="p-4">
          <Skeleton className="h-4 w-16" />
          <div className="mt-3 grid grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i}>
                <Skeleton className="h-3 w-12" />
                <Skeleton className="mt-1 h-6 w-24" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 캘린더 그리드 스켈레톤 */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: 35 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded md:h-20" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
