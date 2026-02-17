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
import { ProfileSection } from '@/features/settings/ui/ProfileSection';
import { SalaryDaySection } from '@/features/settings/ui/SalaryDaySection';
import { PasswordSection } from '@/features/settings/ui/PasswordSection';
import { NotificationSection } from '@/features/settings/ui/NotificationSection';
import { IncomeSection } from '@/features/settings/ui/IncomeSection';
import { CarryoverSection } from '@/features/settings/ui/CarryoverSection';
import { ThemeSection } from '@/features/settings/ui/ThemeSection';
import { InvestmentPromptSection } from '@/features/settings/ui/InvestmentPromptSection';
import { DangerZone } from '@/features/settings/ui/DangerZone';
import { DeleteAccountModal } from '@/features/settings/ui/DeleteAccountModal';
import { Separator } from '@/shared/ui/separator';
import type {
  ProfileUpdateRequest,
  PasswordChangeRequest,
  NotificationPreferences,
} from '@/shared/types';

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
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <ProfileSection
        profile={profile}
        onSave={(data: ProfileUpdateRequest) => updateProfile.mutate(data)}
        isSaving={updateProfile.isPending}
      />

      <Separator />

      <SalaryDaySection
        currentDay={profile.salary_day ?? 1}
        onUpdate={(day: number) => updateProfile.mutate({ salary_day: day })}
        isLoading={updateProfile.isPending}
      />

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

      <IncomeSection />

      <Separator />

      <CarryoverSection />

      <Separator />

      <ThemeSection />

      <Separator />

      <InvestmentPromptSection />

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
