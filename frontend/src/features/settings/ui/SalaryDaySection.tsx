import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Button } from '@/shared/ui/button';

interface Props {
  currentDay: number;
  onUpdate: (day: number) => void;
  isLoading: boolean;
}

export function SalaryDaySection({ currentDay, onUpdate, isLoading }: Props) {
  const [day, setDay] = useState(currentDay);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">급여일 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          급여일을 기준으로 예산 기간이 자동으로 계산됩니다.
        </p>
        <div className="flex items-center gap-3">
          <Label className="text-sm">매월</Label>
          <select
            value={day}
            onChange={(e) => setDay(Number(e.target.value))}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
              <option key={d} value={d}>
                {d}일
              </option>
            ))}
          </select>
          <Button
            onClick={() => onUpdate(day)}
            disabled={isLoading || day === currentDay}
          >
            저장
          </Button>
        </div>
        {day !== 1 && (
          <p className="text-xs text-primary">
            예산 기간: 매월 {day}일 ~ 다음 달 {day - 1}일
          </p>
        )}
      </CardContent>
    </Card>
  );
}
