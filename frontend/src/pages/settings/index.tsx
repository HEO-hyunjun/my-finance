import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import {
  useProfile,
  useUpdateProfile,
  useChangePassword,
  useUpdateNotifications,
  useDeleteAccount,
} from '@/features/settings/api';
import { useAuthStore } from '@/features/auth/model/auth-store';
import { useBudgetPeriod, useUpdateBudgetPeriod } from '@/features/budget/api';
import { ProfileSection } from '@/features/settings/ui/ProfileSection';
import { PasswordSection } from '@/features/settings/ui/PasswordSection';
import { NotificationSection } from '@/features/settings/ui/NotificationSection';
import { ThemeSection } from '@/features/settings/ui/ThemeSection';
import { InvestmentPromptSection } from '@/features/settings/ui/InvestmentPromptSection';
import { PersonalApiKeySection } from '@/features/settings/ui/PersonalApiKeySection';
import { DangerZone } from '@/features/settings/ui/DangerZone';
import { DeleteAccountModal } from '@/features/settings/ui/DeleteAccountModal';
import { Separator } from '@/shared/ui/separator';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import type {
  ProfileUpdateRequest,
  PasswordChangeRequest,
  NotificationPreferences,
} from '@/shared/types/auth';

function BudgetPeriodSection() {
  const { data: period } = useBudgetPeriod();
  const updatePeriod = useUpdateBudgetPeriod();
  const [day, setDay] = useState<number | null>(null);

  const currentDay = period?.period_start_day ?? 1;
  const displayDay = day ?? currentDay;

  const hasChanges = day !== null && day !== currentDay;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">예산 기간 설정</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          예산 시작일을 설정합니다. 이 날짜 기준으로 매월 예산 기간이 계산됩니다.
        </p>
        <div className="flex items-center gap-3">
          <span className="w-20 shrink-0 text-sm">시작일</span>
          <select
            value={displayDay}
            onChange={(e) => setDay(Number(e.target.value))}
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
              <option key={d} value={d}>
                매월 {d}일
              </option>
            ))}
          </select>
          <Button
            onClick={() => {
              if (day !== null) updatePeriod.mutate({ period_start_day: day });
            }}
            disabled={!hasChanges || updatePeriod.isPending}
            size="sm"
          >
            저장
          </Button>
        </div>
        {displayDay !== 1 && (
          <p className="text-xs text-muted-foreground">
            예산 기간: 매월 {displayDay}일 ~ 다음 달 {displayDay - 1}일
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function Component() {
  const navigate = useNavigate();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const updateNotifications = useUpdateNotifications();
  const deleteAccount = useDeleteAccount();
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleDeleteAccount = (password: string) => {
    deleteAccount.mutate(
      { password },
      {
        onSuccess: () => {
          logout();
          navigate('/login');
        },
      },
    );
  };

  if (isLoading || !profile) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <ProfileSection
        profile={profile}
        onSave={(data: ProfileUpdateRequest) => updateProfile.mutate(data)}
        isSaving={updateProfile.isPending}
      />

      <Separator />

      <BudgetPeriodSection />

      <Separator />

      <PasswordSection
        onSubmit={(data: PasswordChangeRequest, callbacks) => changePassword.mutate(data, callbacks)}
        isSubmitting={changePassword.isPending}
      />

      <Separator />

      <NotificationSection
        preferences={
          profile.notification_preferences || {
            budget_alert: true,
            maturity_alert: true,
            market_alert: false,
            email_notifications: false,
          }
        }
        onToggle={(key: string, value: boolean) => {
          const current: NotificationPreferences = profile.notification_preferences || {
            budget_alert: true,
            maturity_alert: true,
            market_alert: false,
            email_notifications: false,
          };
          updateNotifications.mutate({ ...current, [key]: value });
        }}
      />

      <Separator />

      <ThemeSection />

      <Separator />

      <InvestmentPromptSection />

      <Separator />

      <PersonalApiKeySection />

      <Separator />

      <DangerZone
        onLogout={handleLogout}
        onDeleteAccount={() => setDeleteModalOpen(true)}
      />

      <DeleteAccountModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={handleDeleteAccount}
        isDeleting={deleteAccount.isPending}
      />
    </div>
  );
}
