import { useState } from 'react';
import type { UserProfile, ProfileUpdateRequest } from '@/shared/types/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';

const CURRENCIES = [
  { code: 'KRW', label: '대한민국 원 (₩)' },
  { code: 'USD', label: '미국 달러 ($)' },
  { code: 'JPY', label: '일본 엔 (¥)' },
  { code: 'EUR', label: '유로 (€)' },
  { code: 'GBP', label: '영국 파운드 (£)' },
  { code: 'CNY', label: '중국 위안 (¥)' },
];

interface Props {
  profile: UserProfile;
  onSave: (data: ProfileUpdateRequest) => void;
  isSaving: boolean;
}

export function ProfileSection({ profile, onSave, isSaving }: Props) {
  const [name, setName] = useState(profile.name);
  const [currency, setCurrency] = useState(profile.default_currency);

  const hasChanges = name !== profile.name || currency !== profile.default_currency;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasChanges) return;
    const data: ProfileUpdateRequest = {};
    if (name !== profile.name) data.name = name;
    if (currency !== profile.default_currency) data.default_currency = currency;
    onSave(data);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>프로필 정보</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>이름</Label>
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <Label>이메일</Label>
            <Input
              type="email"
              value={profile.email}
              readOnly
              className="bg-muted cursor-not-allowed"
            />
          </div>

          <div>
            <Label>기본 통화</Label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {CURRENCIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={!hasChanges || isSaving}>
              {isSaving ? '저장 중...' : '저장'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
