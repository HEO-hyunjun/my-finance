import { useState } from 'react';
import { useApiKeys, useUpsertApiKey, useDeleteApiKey } from '../api/settings-api';
import { API_SERVICE_LABELS } from '@/shared/types/settings';
import type { ApiServiceType } from '@/shared/types/settings';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';

export function ApiKeySection() {
  const { data: keys, isLoading } = useApiKeys();
  const upsert = useUpsertApiKey();
  const remove = useDeleteApiKey();
  const [editing, setEditing] = useState<string | null>(null);
  const [keyValue, setKeyValue] = useState('');

  const handleSave = (service: ApiServiceType) => {
    if (!keyValue.trim()) return;
    upsert.mutate({ service, api_key: keyValue }, {
      onSuccess: () => { setEditing(null); setKeyValue(''); },
    });
  };

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>API 키 관리</CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          API 키는 서버에서 암호화되어 안전하게 저장됩니다.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {keys?.map((k) => (
          <div key={k.service} className="flex items-center justify-between rounded-lg border border-border p-3">
            <div className="flex-1">
              <span className="font-medium text-sm">{API_SERVICE_LABELS[k.service as ApiServiceType]}</span>
              {editing === k.service ? (
                <div className="flex items-center gap-2 mt-2">
                  <Input
                    type="password"
                    value={keyValue}
                    onChange={(e) => setKeyValue(e.target.value)}
                    placeholder="API 키를 입력하세요"
                    className="flex-1"
                    autoFocus
                  />
                  <Button
                    size="sm"
                    onClick={() => handleSave(k.service as ApiServiceType)}
                    disabled={upsert.isPending}
                  >
                    저장
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => { setEditing(null); setKeyValue(''); }}
                  >
                    취소
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground mt-0.5">
                  {k.is_set ? k.masked_key : '미설정'}
                </p>
              )}
            </div>
            {editing !== k.service && (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => { setEditing(k.service); setKeyValue(''); }}
                >
                  {k.is_set ? '변경' : '설정'}
                </Button>
                {k.is_set && (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => remove.mutate(k.service)}
                    disabled={remove.isPending}
                  >
                    삭제
                  </Button>
                )}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
