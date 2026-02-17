import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/shared/ui/button';

interface Props {
  year: number;
  month: number;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}

export function CalendarHeader({ year, month, onPrev, onNext, onToday }: Props) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onPrev}
          aria-label="이전 달"
        >
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <h2 className="text-lg font-semibold">
          {year}년 {month}월
        </h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={onNext}
          aria-label="다음 달"
        >
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={onToday}
      >
        오늘
      </Button>
    </div>
  );
}
