import type { NotificationPreferences } from '@/shared/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Switch } from '@/shared/ui/switch';
import { Label } from '@/shared/ui/label';

const NOTIFICATION_ITEMS: {
  key: keyof NotificationPreferences;
  label: string;
  description: string;
}[] = [
  { key: 'budget_alert', label: '예산 초과 알림', description: '설정된 예산을 초과하면 알림을 받습니다' },
  { key: 'maturity_alert', label: '만기 알림', description: '예금/적금 만기일이 가까워지면 알림을 받습니다' },
  { key: 'market_alert', label: '시장 변동 알림', description: '환율/시세 큰 변동 시 알림을 받습니다' },
  { key: 'email_notifications', label: '이메일 알림', description: '중요 알림을 이메일로도 받습니다' },
];

interface Props {
  preferences: NotificationPreferences;
  onToggle: (key: string, value: boolean) => void;
}

export function NotificationSection({ preferences, onToggle }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>알림 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {NOTIFICATION_ITEMS.map((item) => (
          <div key={item.key} className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-sm font-medium">{item.label}</Label>
              <p className="text-xs text-muted-foreground">{item.description}</p>
            </div>
            <Switch
              checked={preferences[item.key]}
              onCheckedChange={(checked) => onToggle(item.key, checked)}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
