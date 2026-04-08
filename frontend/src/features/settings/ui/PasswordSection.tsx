import { useState } from 'react';
import type { PasswordChangeRequest } from '@/shared/types/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';

function getPasswordStrength(password: string): 'weak' | 'medium' | 'strong' {
  if (password.length < 8) return 'weak';
  const hasUpper = /[A-Z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
  if (hasUpper && hasNumber && hasSpecial) return 'strong';
  return 'medium';
}

const STRENGTH_CONFIG = {
  weak: { label: '약함', color: 'bg-red-500', width: 'w-1/3' },
  medium: { label: '보통', color: 'bg-orange-500', width: 'w-2/3' },
  strong: { label: '강함', color: 'bg-green-500', width: 'w-full' },
};

interface Props {
  onSubmit: (
    data: PasswordChangeRequest,
    callbacks: { onSuccess: () => void; onError: (error: unknown) => void },
  ) => void;
  isSubmitting: boolean;
}

export function PasswordSection({ onSubmit, isSubmitting }: Props) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const strength = newPassword ? getPasswordStrength(newPassword) : null;
  const passwordsMatch = newPassword === confirmPassword;
  const canSubmit = currentPassword && newPassword.length >= 8 && passwordsMatch && !isSubmitting;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setMessage(null);
    onSubmit(
      { current_password: currentPassword, new_password: newPassword },
      {
        onSuccess: () => {
          setCurrentPassword('');
          setNewPassword('');
          setConfirmPassword('');
          setMessage({ type: 'success', text: '비밀번호가 변경되었습니다' });
        },
        onError: (error: unknown) => {
          const axiosError = error as { response?: { data?: { detail?: string } } };
          const msg = axiosError?.response?.data?.detail || '비밀번호 변경에 실패했습니다';
          setMessage({ type: 'error', text: msg });
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>비밀번호 변경</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">

          {message && (
            <div
              className={`rounded-md px-3 py-2 text-sm ${
                message.type === 'success'
                  ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                  : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
              }`}
            >
              {message.text}
            </div>
          )}

          <div>
            <Label>현재 비밀번호</Label>
            <div className="relative">
              <Input
                type={showCurrent ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowCurrent(!showCurrent)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-sm"
              >
                {showCurrent ? '숨김' : '보기'}
              </button>
            </div>
          </div>

          <div>
            <Label>새 비밀번호</Label>
            <div className="relative">
              <Input
                type={showNew ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowNew(!showNew)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-sm"
              >
                {showNew ? '숨김' : '보기'}
              </button>
            </div>
            {strength && (
              <div className="mt-2">
                <div className="h-1.5 w-full rounded-full bg-muted">
                  <div
                    className={`h-1.5 rounded-full transition-[width] ${STRENGTH_CONFIG[strength].color} ${STRENGTH_CONFIG[strength].width}`}
                  />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {STRENGTH_CONFIG[strength].label}
                  {strength === 'weak' && ' (8자 이상 필요)'}
                  {strength === 'medium' && ' (8자 이상 충족)'}
                  {strength === 'strong' && ' (대문자+숫자+특수문자 포함)'}
                </p>
              </div>
            )}
          </div>

          <div>
            <Label>새 비밀번호 확인</Label>
            <div className="relative">
              <Input
                type={showConfirm ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowConfirm(!showConfirm)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-sm"
              >
                {showConfirm ? '숨김' : '보기'}
              </button>
            </div>
            {confirmPassword && !passwordsMatch && (
              <p className="mt-1 text-xs text-destructive">비밀번호가 일치하지 않습니다</p>
            )}
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={!canSubmit}>
              {isSubmitting ? '변경 중...' : '비밀번호 변경'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
