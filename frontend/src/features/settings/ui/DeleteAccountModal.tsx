import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (password: string) => void;
  isDeleting: boolean;
}

export function DeleteAccountModal({ isOpen, onClose, onConfirm, isDeleting }: Props) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleConfirm = () => {
    if (!password) return;
    setError('');
    onConfirm(password);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>계정 삭제 확인</DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            이 작업은 되돌릴 수 없으며, 모든 데이터가 영구적으로 삭제됩니다:
          </p>
          <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
            <li>자산 정보</li>
            <li>거래 내역</li>
            <li>예산 설정</li>
            <li>대화 기록</li>
          </ul>
        </div>

        <div className="space-y-2">
          <Label>비밀번호 확인</Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setError('');
            }}
            placeholder="비밀번호를 입력하세요"
          />
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>

        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isDeleting}
          >
            취소
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={!password || isDeleting}
          >
            {isDeleting ? '삭제 중...' : '계정 영구 삭제'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
