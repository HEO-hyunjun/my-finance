import { useState, useCallback } from 'react';
import { Plus, AlertCircle, Pencil, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';
import {
  useSchedules,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
  useToggleSchedule,
} from '@/features/schedules/api';
import { useAccounts } from '@/features/accounts/api';
import { CategorySelect } from '@/features/categories/ui/CategorySelect';
import type { RecurringSchedule, ScheduleCreate, ScheduleUpdate, ScheduleType } from '@/entities/schedule/model/types';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Card, CardContent } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/shared/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select';
import {
  Tabs,
  TabsList,
  TabsTrigger,
} from '@/shared/ui/tabs';

// ─── 상수 ─────────────────────────────────────────────────────────────────────

type ScheduleTab = 'all' | ScheduleType;

const SCHEDULE_TYPE_LABELS: Record<ScheduleType, string> = {
  income: '수입',
  expense: '지출',
  transfer: '이체',
};

const SCHEDULE_TYPE_COLORS: Record<ScheduleType, string> = {
  income: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  expense: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  transfer: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
};

const TAB_LABELS: Record<ScheduleTab, string> = {
  all: '전체',
  income: '수입',
  expense: '지출',
  transfer: '이체',
};

const SCHEDULE_TYPE_ORDER: ScheduleType[] = ['income', 'expense', 'transfer'];

// ─── 유틸 ─────────────────────────────────────────────────────────────────────

function formatCurrency(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString('ko-KR')} ${currency}`;
  }
}

// ─── 폼 상태 ──────────────────────────────────────────────────────────────────

interface ScheduleFormState {
  type: ScheduleType;
  name: string;
  amount: string;
  currency: string;
  schedule_day: string;
  start_date: string;
  end_date: string;
  total_count: string;
  source_account_id: string | null;
  target_account_id: string | null;
  category_id: string | null;
  memo: string;
}

function emptyForm(): ScheduleFormState {
  return {
    type: 'expense',
    name: '',
    amount: '',
    currency: 'KRW',
    schedule_day: '1',
    start_date: new Date().toISOString().slice(0, 10),
    end_date: '',
    total_count: '',
    source_account_id: null,
    target_account_id: null,
    category_id: null,
    memo: '',
  };
}

function scheduleToForm(s: RecurringSchedule): ScheduleFormState {
  return {
    type: s.type,
    name: s.name,
    amount: String(s.amount),
    currency: s.currency,
    schedule_day: String(s.schedule_day),
    start_date: s.start_date,
    end_date: s.end_date ?? '',
    total_count: s.total_count != null ? String(s.total_count) : '',
    source_account_id: s.source_account_id,
    target_account_id: s.target_account_id,
    category_id: s.category_id,
    memo: s.memo ?? '',
  };
}

// ─── ScheduleFormFields ───────────────────────────────────────────────────────

interface ScheduleFormFieldsProps {
  form: ScheduleFormState;
  isCreate: boolean;
  onChange: (field: keyof ScheduleFormState, value: string | null) => void;
}

function ScheduleFormFields({ form, isCreate, onChange }: ScheduleFormFieldsProps) {
  const { data: accounts = [] } = useAccounts();
  const isTransfer = form.type === 'transfer';
  const categoryDirection = form.type === 'income' ? 'income' : 'expense';

  return (
    <div className="space-y-4">
      {/* 타입 (생성 시에만) */}
      {isCreate && (
        <div className="space-y-1.5">
          <Label htmlFor="type">유형 *</Label>
          <Select value={form.type} onValueChange={(v) => onChange('type', v)}>
            <SelectTrigger id="type" className="w-full">
              <SelectValue placeholder="유형 선택" />
            </SelectTrigger>
            <SelectContent>
              {SCHEDULE_TYPE_ORDER.map((t) => (
                <SelectItem key={t} value={t}>
                  {SCHEDULE_TYPE_LABELS[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* 이름 */}
      <div className="space-y-1.5">
        <Label htmlFor="name">이름 *</Label>
        <Input
          id="name"
          value={form.name}
          onChange={(e) => onChange('name', e.target.value)}
          placeholder="예: 월세, 구독료"
        />
      </div>

      {/* 금액 / 통화 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="amount">금액 *</Label>
          <Input
            id="amount"
            type="number"
            min="0"
            value={form.amount}
            onChange={(e) => onChange('amount', e.target.value)}
            placeholder="0"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="currency">통화</Label>
          <Input
            id="currency"
            value={form.currency}
            onChange={(e) => onChange('currency', e.target.value.toUpperCase())}
            placeholder="KRW"
          />
        </div>
      </div>

      {/* 결제일 */}
      <div className="space-y-1.5">
        <Label htmlFor="schedule_day">매월 결제일 *</Label>
        <Input
          id="schedule_day"
          type="number"
          min="1"
          max="31"
          value={form.schedule_day}
          onChange={(e) => onChange('schedule_day', e.target.value)}
          placeholder="1~31"
        />
      </div>

      {/* 시작일 / 종료일 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="start_date">시작일 *</Label>
          <Input
            id="start_date"
            type="date"
            value={form.start_date}
            onChange={(e) => onChange('start_date', e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="end_date">종료일</Label>
          <Input
            id="end_date"
            type="date"
            value={form.end_date}
            onChange={(e) => onChange('end_date', e.target.value)}
          />
        </div>
      </div>

      {/* 총 횟수 (할부/정기) */}
      <div className="space-y-1.5">
        <Label htmlFor="total_count">총 횟수 (할부/정기, 선택)</Label>
        <Input
          id="total_count"
          type="number"
          min="1"
          value={form.total_count}
          onChange={(e) => onChange('total_count', e.target.value)}
          placeholder="미입력 시 무기한"
        />
      </div>

      {/* 이체 계좌 */}
      {isTransfer ? (
        <>
          <div className="space-y-1.5">
            <Label htmlFor="source_account_id">출금 계좌</Label>
            <Select
              value={form.source_account_id ?? ''}
              onValueChange={(v) => onChange('source_account_id', v || null)}
            >
              <SelectTrigger id="source_account_id" className="w-full">
                <SelectValue placeholder="출금 계좌 선택" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((a) => (
                  <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="target_account_id">입금 계좌</Label>
            <Select
              value={form.target_account_id ?? ''}
              onValueChange={(v) => onChange('target_account_id', v || null)}
            >
              <SelectTrigger id="target_account_id" className="w-full">
                <SelectValue placeholder="입금 계좌 선택" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map((a) => (
                  <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      ) : (
        <div className="space-y-1.5">
          <Label>카테고리</Label>
          <CategorySelect
            direction={categoryDirection}
            value={form.category_id}
            onChange={(v) => onChange('category_id', v)}
          />
        </div>
      )}

      {/* 메모 */}
      <div className="space-y-1.5">
        <Label htmlFor="memo">메모</Label>
        <Input
          id="memo"
          value={form.memo}
          onChange={(e) => onChange('memo', e.target.value)}
          placeholder="메모 (선택)"
        />
      </div>
    </div>
  );
}

// ─── CreateScheduleDialog ─────────────────────────────────────────────────────

interface CreateScheduleDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

function CreateScheduleDialog({ isOpen, onClose }: CreateScheduleDialogProps) {
  const [form, setForm] = useState<ScheduleFormState>(emptyForm);
  const createSchedule = useCreateSchedule();

  const handleChange = useCallback((field: keyof ScheduleFormState, value: string | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.amount) return;

    const payload: ScheduleCreate = {
      type: form.type,
      name: form.name.trim(),
      amount: Number(form.amount),
      currency: form.currency || 'KRW',
      schedule_day: Number(form.schedule_day),
      start_date: form.start_date,
      end_date: form.end_date || null,
      total_count: form.total_count ? Number(form.total_count) : null,
      source_account_id: form.source_account_id,
      target_account_id: form.target_account_id,
      category_id: form.category_id,
      memo: form.memo || null,
    };

    createSchedule.mutate(payload, {
      onSuccess: () => {
        setForm(emptyForm());
        onClose();
      },
    });
  };

  const handleClose = () => {
    setForm(emptyForm());
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>반복 일정 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <ScheduleFormFields form={form} isCreate onChange={handleChange} />
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={handleClose}>
              취소
            </Button>
            <Button
              type="submit"
              disabled={createSchedule.isPending || !form.name.trim() || !form.amount}
            >
              {createSchedule.isPending ? '추가 중...' : '추가'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── EditScheduleDialog ───────────────────────────────────────────────────────

interface EditScheduleDialogProps {
  schedule: RecurringSchedule;
  isOpen: boolean;
  onClose: () => void;
}

function EditScheduleDialog({ schedule, isOpen, onClose }: EditScheduleDialogProps) {
  const [form, setForm] = useState<ScheduleFormState>(() => scheduleToForm(schedule));
  const updateSchedule = useUpdateSchedule();

  const handleChange = useCallback((field: keyof ScheduleFormState, value: string | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;

    const payload: ScheduleUpdate & { id: string } = {
      id: schedule.id,
      name: form.name.trim(),
      amount: form.amount ? Number(form.amount) : undefined,
      schedule_day: form.schedule_day ? Number(form.schedule_day) : undefined,
      end_date: form.end_date || null,
      source_account_id: form.source_account_id,
      target_account_id: form.target_account_id,
      category_id: form.category_id,
      memo: form.memo || null,
    };

    updateSchedule.mutate(payload, { onSuccess: onClose });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>반복 일정 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <ScheduleFormFields form={form} isCreate={false} onChange={handleChange} />
          <DialogFooter className="mt-6">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={updateSchedule.isPending || !form.name.trim()}>
              {updateSchedule.isPending ? '수정 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── ScheduleCard ─────────────────────────────────────────────────────────────

interface ScheduleCardProps {
  schedule: RecurringSchedule;
  onEdit: () => void;
  onDelete: () => void;
}

function ScheduleCard({ schedule, onEdit, onDelete }: ScheduleCardProps) {
  const toggleSchedule = useToggleSchedule();
  const isInstallment = schedule.total_count != null;
  const progress = isInstallment
    ? Math.min((schedule.executed_count / schedule.total_count!) * 100, 100)
    : null;
  const remaining = isInstallment
    ? schedule.total_count! - schedule.executed_count
    : null;

  return (
    <div className="rounded-lg border bg-card px-4 py-3 space-y-2">
      {/* 헤더 행 */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${SCHEDULE_TYPE_COLORS[schedule.type]}`}
          >
            {SCHEDULE_TYPE_LABELS[schedule.type]}
          </span>
          <span className={`font-medium ${!schedule.is_active ? 'text-muted-foreground line-through' : ''}`}>
            {schedule.name}
          </span>
        </div>
        {/* 토글 */}
        <button
          type="button"
          onClick={() => toggleSchedule.mutate(schedule.id)}
          disabled={toggleSchedule.isPending}
          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
          aria-label={schedule.is_active ? '비활성화' : '활성화'}
        >
          {schedule.is_active ? (
            <ToggleRight className="h-5 w-5 text-primary" />
          ) : (
            <ToggleLeft className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* 금액 / 주기 */}
      <div className="flex items-center justify-between text-sm">
        <span className="font-semibold text-base">
          {formatCurrency(schedule.amount, schedule.currency)}
        </span>
        <span className="text-muted-foreground">매월 {schedule.schedule_day}일</span>
      </div>

      {/* 할부 진행바 */}
      {isInstallment && progress !== null && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{schedule.executed_count}/{schedule.total_count}회</span>
            <span>남은 {remaining}회</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* 종료일 / 메모 */}
      {(schedule.end_date || schedule.memo) && (
        <div className="flex flex-wrap gap-x-4 text-xs text-muted-foreground">
          {schedule.end_date && <span>종료: {schedule.end_date}</span>}
          {schedule.memo && <span>{schedule.memo}</span>}
        </div>
      )}

      {/* 액션 버튼 */}
      <div className="flex gap-2 pt-1">
        <Button variant="outline" size="sm" onClick={onEdit}>
          <Pencil className="mr-1.5 h-3.5 w-3.5" />
          수정
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          onClick={onDelete}
        >
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
          삭제
        </Button>
      </div>
    </div>
  );
}

// ─── Page Component ───────────────────────────────────────────────────────────

export function Component() {
  const { data: schedules = [], isLoading, isError, refetch } = useSchedules();
  const deleteSchedule = useDeleteSchedule();

  const [activeTab, setActiveTab] = useState<ScheduleTab>('all');
  const [showCreate, setShowCreate] = useState(false);
  const [editTarget, setEditTarget] = useState<RecurringSchedule | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const handleOpenCreate = useCallback(() => setShowCreate(true), []);
  const handleCloseCreate = useCallback(() => setShowCreate(false), []);

  const handleDeleteRequest = useCallback((id: string) => {
    setConfirmDelete(id);
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (confirmDelete) {
      deleteSchedule.mutate(confirmDelete);
      setConfirmDelete(null);
    }
  }, [confirmDelete, deleteSchedule]);

  const filtered = schedules.filter((s) =>
    activeTab === 'all' ? true : s.type === activeTab,
  );

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">반복 일정</h1>
        <Button onClick={handleOpenCreate}>
          <Plus className="mr-2 h-4 w-4" />
          일정 추가
        </Button>
      </div>

      {/* 탭 필터 */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ScheduleTab)}>
        <TabsList className="grid w-full grid-cols-4">
          {(Object.keys(TAB_LABELS) as ScheduleTab[]).map((tab) => (
            <TabsTrigger key={tab} value={tab}>
              {TAB_LABELS[tab]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}

      {/* 에러 */}
      {isError && (
        <Card>
          <CardContent className="flex flex-col items-center py-12">
            <AlertCircle className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">반복 일정을 불러올 수 없습니다.</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
              다시 시도
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 목록 */}
      {!isLoading && !isError && (
        <>
          {filtered.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center py-16">
                <p className="text-muted-foreground">등록된 반복 일정이 없습니다.</p>
                <Button className="mt-4" onClick={handleOpenCreate}>
                  <Plus className="mr-2 h-4 w-4" />
                  첫 일정 추가하기
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filtered.map((schedule) => (
                <ScheduleCard
                  key={schedule.id}
                  schedule={schedule}
                  onEdit={() => setEditTarget(schedule)}
                  onDelete={() => handleDeleteRequest(schedule.id)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* 추가 모달 */}
      <CreateScheduleDialog isOpen={showCreate} onClose={handleCloseCreate} />

      {/* 수정 모달 */}
      {editTarget && (
        <EditScheduleDialog
          schedule={editTarget}
          isOpen={editTarget !== null}
          onClose={() => setEditTarget(null)}
        />
      )}

      {/* 삭제 확인 모달 */}
      <ConfirmDialog
        open={confirmDelete !== null}
        onOpenChange={(open) => { if (!open) setConfirmDelete(null); }}
        title="반복 일정을 삭제하시겠습니까?"
        description="이 작업은 되돌릴 수 없습니다."
        confirmLabel="삭제"
        onConfirm={handleConfirmDelete}
        variant="destructive"
      />
    </div>
  );
}
