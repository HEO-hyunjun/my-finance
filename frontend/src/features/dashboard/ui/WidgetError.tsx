import { AlertCircle } from 'lucide-react';

export function WidgetError({ message = '데이터를 불러올 수 없습니다' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <AlertCircle className="mb-2 h-6 w-6 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
