import { useState } from 'react';
import { ArrowLeft, AlertTriangle, Loader2 } from 'lucide-react';
import { useImportDetail, useUpdateRow, useCommitImport } from '@/features/imports/api';
import { DEDUP_META, STATUS_META, formatKRW } from '@/features/imports/lib/status';
import { CategorySelect } from '@/features/categories/ui/CategorySelect';
import type { StagedEntry, ImportMerge } from '@/entities/import/model/types';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/ui/select';

const TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: 'income', label: '수입' },
  { value: 'expense', label: '지출' },
  { value: 'dividend', label: '배당' },
  { value: 'fee', label: '수수료' },
];

interface Props {
  batchId: string;
  onBack: () => void;
}

function rowDirection(row: StagedEntry): 'income' | 'expense' {
  const type = row.suggested_type;
  if (type === 'income' || type === 'dividend') return 'income';
  if (type === 'expense' || type === 'fee') return 'expense';
  return Number(row.amount) >= 0 ? 'income' : 'expense';
}

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' });
}

export function ImportReview({ batchId, onBack }: Props) {
  const { data, isLoading } = useImportDetail(batchId);
  const updateRow = useUpdateRow(batchId);
  const commit = useCommitImport(batchId);
  const [createAdjustment, setCreateAdjustment] = useState(false);
  const [mergeOverrides, setMergeOverrides] = useState<Record<string, boolean>>({});
  const [confirmOpen, setConfirmOpen] = useState(false);

  const backButton = (
    <Button variant="ghost" size="sm" onClick={onBack} className="mb-3">
      <ArrowLeft className="mr-1 h-4 w-4" />
      목록으로
    </Button>
  );

  if (isLoading || !data) {
    return (
      <div>
        {backButton}
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      </div>
    );
  }

  const { batch, staged_entries: rows, balance_check: bc, period_overlap } = data;
  const meta = STATUS_META[batch.status];
  const isCommitted = batch.status === 'committed';
  const inProgress = batch.status === 'uploaded' || batch.status === 'parsing';
  const editable = batch.status === 'review';

  if (inProgress) {
    return (
      <div>
        {backButton}
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">파일을 분석하고 있습니다…</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (batch.status === 'failed') {
    return (
      <div>
        {backButton}
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm text-destructive">{batch.error ?? '분석에 실패했습니다.'}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // 이체 후보 행의 병합 여부: 기본 켜짐, 사용자가 끄면 override
  const isMerging = (row: StagedEntry) =>
    row.transfer_candidate ? (mergeOverrides[row.id] ?? true) : false;

  const selectedCount = rows.filter((r) => r.is_selected).length;
  const mergeCount = rows.filter((r) => r.is_selected && isMerging(r)).length;
  const hasBalanceDiff = bc.difference != null && Number(bc.difference) !== 0;

  const buildMerges = (): ImportMerge[] =>
    rows
      .filter((r) => r.is_selected && isMerging(r) && r.transfer_candidate)
      .map((r) => ({ row_id: r.id, counterpart_entry_id: r.transfer_candidate!.entry_id }));

  const handleCommit = () => {
    commit.mutate(
      { create_adjustment: createAdjustment && hasBalanceDiff, merges: buildMerges() },
      { onSuccess: onBack },
    );
  };

  return (
    <div>
      {backButton}

      <div className="mb-4 flex items-center gap-2">
        <h2 className="text-lg font-semibold">{batch.filename}</h2>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${meta.className}`}>{meta.label}</span>
      </div>

      {period_overlap && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>기존 거래와 기간이 겹칩니다. 중복 항목이 기본 해제되어 있는지 확인하세요.</span>
        </div>
      )}

      {/* 잔액 검증 패널 */}
      {(bc.file_balance != null || bc.ledger_balance != null) && (
        <Card className="mb-4">
          <CardContent className="space-y-2 py-4 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">파일 잔액</span>
              <span>{bc.file_balance != null ? formatKRW(Number(bc.file_balance)) : '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">원장 잔액</span>
              <span>{bc.ledger_balance != null ? formatKRW(Number(bc.ledger_balance)) : '—'}</span>
            </div>
            <div className="flex justify-between border-t pt-2 font-medium">
              <span className="text-muted-foreground">차이</span>
              <span className={hasBalanceDiff ? 'text-destructive' : 'text-green-600'}>
                {bc.difference != null ? formatKRW(Number(bc.difference)) : '—'}
              </span>
            </div>
            {editable && hasBalanceDiff && (
              <label className="mt-2 flex items-center gap-2 rounded-lg border px-3 py-2">
                <input
                  type="checkbox"
                  checked={createAdjustment}
                  onChange={(e) => setCreateAdjustment(e.target.checked)}
                  className="h-4 w-4 rounded"
                />
                <span className="text-sm">차이를 보정 거래로 생성</span>
              </label>
            )}
          </CardContent>
        </Card>
      )}

      {/* 행 테이블 */}
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="bg-muted/50 text-left">
            <tr>
              <th className="w-10 px-3 py-2"></th>
              <th className="px-3 py-2 font-medium">일자</th>
              <th className="px-3 py-2 font-medium">내용</th>
              <th className="px-3 py-2 text-right font-medium">금액</th>
              <th className="px-3 py-2 font-medium">유형</th>
              <th className="px-3 py-2 font-medium">카테고리</th>
              <th className="px-3 py-2 font-medium">중복</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const amount = Number(row.amount);
              const dedup = DEDUP_META[row.dedup_status];
              const disabled = !editable;
              const merging = isMerging(row);
              const cand = row.transfer_candidate;
              return (
                <tr key={row.id} className="border-t align-top">
                  <td className="px-3 py-3">
                    <input
                      type="checkbox"
                      checked={row.is_selected}
                      disabled={disabled}
                      onChange={(e) => updateRow.mutate({ rowId: row.id, is_selected: e.target.checked })}
                      className="h-4 w-4 rounded"
                    />
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-xs text-muted-foreground">
                    {shortDate(row.transacted_at)}
                  </td>
                  <td className="max-w-[220px] px-3 py-3">
                    <span className="block truncate">{row.description ?? '—'}</span>
                    {cand && (
                      <div className="mt-1 space-y-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
                            이체 후보
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {cand.account_name} · {shortDate(cand.transacted_at)} · {formatKRW(Number(cand.amount))}
                          </span>
                        </div>
                        <label className="flex items-center gap-1.5 text-xs">
                          <input
                            type="checkbox"
                            checked={merging}
                            disabled={disabled}
                            onChange={(e) => setMergeOverrides((prev) => ({ ...prev, [row.id]: e.target.checked }))}
                            className="h-3.5 w-3.5 rounded"
                          />
                          <span>이체로 묶기</span>
                        </label>
                      </div>
                    )}
                  </td>
                  <td className={`whitespace-nowrap px-3 py-3 text-right font-medium tabular-nums ${amount < 0 ? 'text-destructive' : 'text-green-600'}`}>
                    {formatKRW(amount)}
                  </td>
                  <td className="px-3 py-3">
                    <Select
                      value={row.suggested_type ?? rowDirection(row)}
                      onValueChange={(v) => updateRow.mutate({ rowId: row.id, suggested_type: v })}
                      disabled={disabled || merging}
                    >
                      <SelectTrigger className="h-8 w-24 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {TYPE_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="px-3 py-3">
                    <div className="w-40">
                      {merging ? (
                        <span className="text-xs text-muted-foreground">이체 (카테고리 없음)</span>
                      ) : (
                        <CategorySelect
                          direction={rowDirection(row)}
                          value={row.suggested_category_id}
                          onChange={(v) => updateRow.mutate({ rowId: row.id, suggested_category_id: v })}
                        />
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${dedup.className}`}>
                      {dedup.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 커밋 푸터 */}
      {editable ? (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            선택 <span className="font-semibold text-foreground">{selectedCount}</span> / {rows.length}건
            {mergeCount > 0 && <span> · 이체 병합 {mergeCount}건</span>}
          </p>
          <Button
            disabled={selectedCount === 0 || commit.isPending}
            onClick={() => setConfirmOpen(true)}
          >
            {commit.isPending ? '반영 중...' : `${selectedCount}건 반영`}
          </Button>
        </div>
      ) : isCommitted ? (
        <p className="mt-4 text-center text-sm text-muted-foreground">이미 커밋된 배치입니다.</p>
      ) : null}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="선택한 내역을 반영하시겠습니까?"
        description={
          `선택 ${selectedCount}건을 거래로 반영합니다.` +
          (mergeCount > 0 ? ` 그중 ${mergeCount}건은 이체로 병합됩니다.` : '') +
          (createAdjustment && hasBalanceDiff ? ' 잔액 차이는 보정 거래로 생성됩니다.' : '')
        }
        confirmLabel="반영"
        onConfirm={handleCommit}
      />
    </div>
  );
}
