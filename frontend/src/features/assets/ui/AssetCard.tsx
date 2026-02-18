import { memo } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { formatKRW } from '@/shared/lib/format';
import { getAssetIcon } from '@/shared/lib/icons';
import { ASSET_TYPE_LABELS } from '@/shared/types';
import type { AssetHolding } from '@/shared/types';

interface Props {
  holding: AssetHolding;
  onClick?: () => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  isDeleting?: boolean;
}

const INTEREST_BASED_TYPES = ['deposit', 'savings', 'parking'];

const Row = memo(({
  label,
  value,
  bold,
  positive,
  negative,
  muted,
}: {
  label: string;
  value: string;
  bold?: boolean;
  positive?: boolean;
  negative?: boolean;
  muted?: boolean;
}) => {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={
          bold
            ? 'font-medium'
            : positive
              ? 'text-green-600 dark:text-green-400'
              : negative
                ? 'text-red-600 dark:text-red-400'
                : muted
                  ? 'text-xs text-muted-foreground'
                  : ''
        }
      >
        {value}
      </span>
    </div>
  );
});

function AssetCardInner({ holding, onClick, onEdit, onDelete, isDeleting }: Props) {
  const isPositive = holding.profit_loss >= 0;
  const isInterestBased = INTEREST_BASED_TYPES.includes(holding.asset_type);
  const isParking = holding.asset_type === 'parking';
  const isSavings = holding.asset_type === 'savings';
  const Icon = getAssetIcon(holding.asset_type);

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`'${holding.name}' 자산을 삭제하시겠습니까?\n관련 거래 내역도 함께 삭제됩니다.`)) {
      onDelete?.(holding.id);
    }
  };

  return (
    <Card
      className="group cursor-pointer transition-shadow hover:shadow-md"
      onClick={onClick}
    >
      <CardContent className="pt-4 pb-4">
        <div className="mb-3 flex items-center gap-2.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
            <Icon className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-semibold">{holding.name}</p>
            <p className="truncate text-xs text-muted-foreground">
              {ASSET_TYPE_LABELS[holding.asset_type] || holding.asset_type}
              {holding.bank_name ? ` | ${holding.bank_name}` : ''}
              {holding.symbol ? ` (${holding.symbol})` : ''}
              {holding.interest_rate != null ? ` | ${holding.interest_rate.toFixed(2)}%` : ''}
            </p>
          </div>
          <div className="flex shrink-0 gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                onClick={(e) => { e.stopPropagation(); onEdit(holding.id); }}
              >
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>

        <div className="space-y-1.5 text-sm">
          {isInterestBased ? (
            isParking ? (
              <>
                <Row label="잔액" value={formatKRW(holding.total_value_krw)} bold />
                {holding.daily_interest != null && (
                  <Row label="일일이자" value={formatKRW(holding.daily_interest)} />
                )}
                {holding.monthly_interest != null && (
                  <Row label="월예상이자 (세후)" value={formatKRW(holding.monthly_interest)} positive />
                )}
              </>
            ) : (
              <>
                <Row label={isSavings ? '총 납입액' : '원금'} value={formatKRW(holding.total_invested_krw)} />
                {holding.accrued_interest_aftertax != null && (
                  <Row label="경과이자 (세후)" value={`+${formatKRW(holding.accrued_interest_aftertax)}`} positive />
                )}
                <Row label="평가금액" value={formatKRW(holding.total_value_krw)} bold />
                {holding.maturity_amount != null && (
                  <Row label="만기 예상" value={formatKRW(holding.maturity_amount)} />
                )}
                {holding.maturity_date && holding.elapsed_months != null && holding.total_months != null && (
                  <Row
                    label="만기일"
                    value={`${holding.maturity_date} (${holding.elapsed_months}/${holding.total_months}개월)`}
                    muted
                  />
                )}
              </>
            )
          ) : (
            <>
              <Row label="보유량" value={holding.quantity.toLocaleString()} />
              <Row label="평가금액" value={formatKRW(holding.total_value_krw)} bold />
              <Row
                label="수익/손실"
                value={`${isPositive ? '+' : ''}${formatKRW(holding.profit_loss)} (${isPositive ? '+' : ''}${holding.profit_loss_rate.toFixed(1)}%)`}
                positive={isPositive}
                negative={!isPositive}
              />
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export const AssetCard = memo(AssetCardInner);
