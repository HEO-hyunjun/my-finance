import { useAppSettings, useUpdateAppSettings } from '../api/settings-api';
import type { ThemeMode } from '@/shared/types/settings';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { cn } from '@/shared/lib/utils';

const THEME_OPTIONS: { value: ThemeMode; label: string; icon: string }[] = [
  { value: 'light', label: '라이트', icon: '☀️' },
  { value: 'dark', label: '다크', icon: '🌙' },
  { value: 'system', label: '시스템', icon: '💻' },
];

export function ThemeSection() {
  const { data: settings, isLoading } = useAppSettings();
  const update = useUpdateAppSettings();

  const handleChange = (theme: ThemeMode) => {
    update.mutate({ theme });
  };

  if (isLoading) return <Skeleton className="h-32 w-full" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>테마 설정</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-3">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleChange(opt.value)}
              disabled={update.isPending}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 rounded-lg border-2 p-3 text-sm font-medium transition-colors',
                settings?.theme === opt.value
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border hover:bg-accent',
              )}
            >
              <span>{opt.icon}</span>
              <span>{opt.label}</span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
