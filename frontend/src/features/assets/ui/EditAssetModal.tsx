import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import type { Asset, AssetUpdateRequest } from '@/shared/types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: AssetUpdateRequest) => void;
  asset: Asset | null;
  isLoading: boolean;
}

const INTEREST_BASED_TYPES = ['deposit', 'savings', 'parking'];

export function EditAssetModal({ isOpen, onClose, onSubmit, asset, isLoading }: Props) {
  const [name, setName] = useState('');
  const [principal, setPrincipal] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [monthlyAmount, setMonthlyAmount] = useState('');
  const [bankName, setBankName] = useState('');
  const [taxRate, setTaxRate] = useState('');
  const [startDate, setStartDate] = useState('');
  const [maturityDate, setMaturityDate] = useState('');

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (asset) {
      setName(asset.name ?? '');
      setPrincipal(asset.principal?.toString() ?? '');
      setInterestRate(asset.interest_rate?.toString() ?? '');
      setMonthlyAmount(asset.monthly_amount?.toString() ?? '');
      setBankName(asset.bank_name ?? '');
      setTaxRate(asset.tax_rate?.toString() ?? '');
      setStartDate(asset.start_date ?? '');
      setMaturityDate(asset.maturity_date ?? '');
    }
  }, [asset]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (!asset) return null;

  const isInterestBased = INTEREST_BASED_TYPES.includes(asset.asset_type);
  const isSavings = asset.asset_type === 'savings';
  const isDeposit = asset.asset_type === 'deposit';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: AssetUpdateRequest = {};
    if (name !== asset.name) data.name = name;
    if (!isInterestBased && principal && Number(principal) !== asset.principal) data.principal = Number(principal);
    if (interestRate && Number(interestRate) !== asset.interest_rate) data.interest_rate = Number(interestRate);
    if (isSavings && monthlyAmount && Number(monthlyAmount) !== asset.monthly_amount) data.monthly_amount = Number(monthlyAmount);
    if (bankName !== (asset.bank_name ?? '')) data.bank_name = bankName || undefined;
    if (taxRate && Number(taxRate) !== asset.tax_rate) data.tax_rate = Number(taxRate);
    if (startDate && startDate !== asset.start_date) data.start_date = startDate;
    if (maturityDate && maturityDate !== asset.maturity_date) data.maturity_date = maturityDate;

    if (Object.keys(data).length > 0) {
      onSubmit(data);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>자산 수정</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>자산명</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          {isInterestBased && (
            <>
              <div>
                <Label>연이율 (%)</Label>
                <Input type="number" value={interestRate} onChange={(e) => setInterestRate(e.target.value)} step="0.01" min="0" required />
              </div>

              {isSavings && (
                <div>
                  <Label>월 납입액 (원)</Label>
                  <Input type="number" value={monthlyAmount} onChange={(e) => setMonthlyAmount(e.target.value)} min="0" required />
                </div>
              )}

              <div>
                <Label>은행/증권사</Label>
                <Input value={bankName} onChange={(e) => setBankName(e.target.value)} placeholder="은행명 입력" />
              </div>

              {(isDeposit || isSavings) && (
                <>
                  <div>
                    <Label>세율 (%)</Label>
                    <Input type="number" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} step="0.1" min="0" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>가입일</Label>
                      <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                    </div>
                    <div>
                      <Label>만기일</Label>
                      <Input type="date" value={maturityDate} onChange={(e) => setMaturityDate(e.target.value)} />
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              취소
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? '저장 중...' : '저장'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
