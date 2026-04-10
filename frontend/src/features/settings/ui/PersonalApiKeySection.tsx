import { useState } from 'react';
import { Copy, Eye, RefreshCw, Trash2, Key } from 'lucide-react';
import {
  usePersonalApiKeyStatus,
  useGeneratePersonalApiKey,
  useRevealPersonalApiKey,
  useRevokePersonalApiKey,
} from '../api/settings-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Skeleton } from '@/shared/ui/skeleton';
import { toast } from 'sonner';

export function PersonalApiKeySection() {
  const { data: status, isLoading } = usePersonalApiKeyStatus();
  const generate = useGeneratePersonalApiKey();
  const reveal = useRevealPersonalApiKey();
  const revoke = useRevokePersonalApiKey();

  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [passwordInput, setPasswordInput] = useState('');
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [confirmRevoke, setConfirmRevoke] = useState(false);

  const handleGenerate = () => {
    if (status?.is_set) {
      if (!confirm('기존 키가 폐기되고 새 키가 발급됩니다. 계속할까요?')) return;
    }
    generate.mutate(undefined, {
      onSuccess: (data) => {
        setGeneratedKey(data.api_key);
        setRevealedKey(null);
        toast.success('API Key가 발급되었습니다');
      },
    });
  };

  const handleReveal = () => {
    reveal.mutate(passwordInput, {
      onSuccess: (data) => {
        setRevealedKey(data.api_key);
        setShowPasswordModal(false);
        setPasswordInput('');
      },
      onError: () => {
        toast.error('비밀번호가 올바르지 않습니다');
      },
    });
  };

  const handleRevoke = () => {
    revoke.mutate(undefined, {
      onSuccess: () => {
        setGeneratedKey(null);
        setRevealedKey(null);
        setConfirmRevoke(false);
        toast.success('API Key가 폐기되었습니다');
      },
    });
  };

  const handleCopy = (key: string) => {
    navigator.clipboard.writeText(key);
    toast.success('클립보드에 복사되었습니다');
  };

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  const displayKey = generatedKey || revealedKey;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Key className="h-5 w-5" />
          Personal API Key
        </CardTitle>
        <p className="text-sm text-muted-foreground mt-1">
          외부 AI 모델에서 MyFinance API에 접근할 때 사용합니다.
          요청 시 <code className="text-xs bg-muted px-1 py-0.5 rounded">X-API-Key</code> 헤더에 키를 포함하세요.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 발급된 키 표시 영역 */}
        {displayKey && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-green-600 dark:text-green-400">
              {generatedKey ? '키가 발급되었습니다. 복사하여 안전한 곳에 보관하세요.' : '키 원본:'}
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-lg border border-border bg-muted px-3 py-2 text-sm font-mono break-all">
                {displayKey}
              </code>
              <Button size="icon" variant="outline" onClick={() => handleCopy(displayKey)}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* 키 상태 및 액션 */}
        {!status?.is_set && !generatedKey ? (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground mb-3">발급된 API Key가 없습니다.</p>
            <Button onClick={handleGenerate} disabled={generate.isPending}>
              키 발급하기
            </Button>
          </div>
        ) : status?.is_set && (
          <div className="flex items-center justify-between">
            <div>
              <span className="font-mono text-sm">{status.prefix}****</span>
              <span className="text-xs text-muted-foreground ml-2">
                {status.created_at && new Date(status.created_at).toLocaleDateString('ko-KR')} 발급
              </span>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => { setShowPasswordModal(true); setRevealedKey(null); }}
              >
                <Eye className="h-4 w-4 mr-1" />
                키 보기
              </Button>
              <Button size="sm" variant="outline" onClick={handleGenerate} disabled={generate.isPending}>
                <RefreshCw className="h-4 w-4 mr-1" />
                재발급
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => setConfirmRevoke(true)}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                폐기
              </Button>
            </div>
          </div>
        )}

        {/* 비밀번호 입력 모달 (인라인) */}
        {showPasswordModal && (
          <div className="rounded-lg border border-border p-4 space-y-3 bg-muted/50">
            <p className="text-sm font-medium">비밀번호를 입력하세요</p>
            <div className="flex items-center gap-2">
              <Input
                type="password"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                placeholder="비밀번호"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && passwordInput && handleReveal()}
              />
              <Button size="sm" onClick={handleReveal} disabled={!passwordInput || reveal.isPending}>
                확인
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setShowPasswordModal(false); setPasswordInput(''); }}>
                취소
              </Button>
            </div>
          </div>
        )}

        {/* 폐기 확인 */}
        {confirmRevoke && (
          <div className="rounded-lg border border-destructive/50 p-4 space-y-3 bg-destructive/5">
            <p className="text-sm font-medium text-destructive">
              API Key를 폐기하면 이 키를 사용하는 모든 외부 연동이 중단됩니다.
            </p>
            <div className="flex gap-2">
              <Button size="sm" variant="destructive" onClick={handleRevoke} disabled={revoke.isPending}>
                폐기 확인
              </Button>
              <Button size="sm" variant="outline" onClick={() => setConfirmRevoke(false)}>
                취소
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
