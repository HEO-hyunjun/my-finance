import { LogOut, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Separator } from '@/shared/ui/separator';

interface Props {
  onLogout: () => void;
  onDeleteAccount: () => void;
}

export function DangerZone({ onLogout, onDeleteAccount }: Props) {
  return (
    <Card className="border-destructive/50 bg-destructive/5">
      <CardHeader>
        <CardTitle className="text-destructive">계정 관리</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <p className="text-sm font-medium flex items-center gap-2">
              <LogOut className="h-4 w-4" />
              로그아웃
            </p>
            <p className="text-xs text-muted-foreground">현재 세션에서 로그아웃합니다.</p>
          </div>
          <Button variant="outline" onClick={onLogout}>
            로그아웃
          </Button>
        </div>

        <Separator />

        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <p className="text-sm font-medium flex items-center gap-2">
              <Shield className="h-4 w-4" />
              계정 삭제
            </p>
            <p className="text-xs text-muted-foreground">
              계정과 모든 데이터가 영구적으로 삭제됩니다.
              <br />
              이 작업은 되돌릴 수 없습니다.
            </p>
          </div>
          <Button variant="destructive" onClick={onDeleteAccount}>
            계정 삭제
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
