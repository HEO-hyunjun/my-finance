import { useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { useAccounts } from '@/features/accounts/api';
import { useCreateImport } from '@/features/imports/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/shared/ui/select';

const ACCEPT = '.xlsx,.xls,.csv,.pdf';

export function UploadCard() {
  const { data: accounts = [] } = useAccounts();
  const createImport = useCreateImport();

  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [accountId, setAccountId] = useState<string>('');
  const [password, setPassword] = useState('');

  const reset = () => {
    setFile(null);
    setAccountId('');
    setPassword('');
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleUpload = () => {
    if (!file) return;
    createImport.mutate(
      { file, accountId: accountId || undefined, password: password || undefined },
      { onSuccess: reset },
    );
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Upload className="h-4 w-4" />
          파일 가져오기
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="import-file">파일 (xlsx / xls / csv / pdf) *</Label>
          <Input
            id="import-file"
            ref={fileRef}
            type="file"
            accept={ACCEPT}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>계좌 (선택)</Label>
            <Select value={accountId} onValueChange={setAccountId}>
              <SelectTrigger><SelectValue placeholder="자동 판별 / 계좌 선택" /></SelectTrigger>
              <SelectContent>
                {accounts.map((a) => (
                  <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="import-pw">비밀번호 (암호화 파일)</Label>
            <Input
              id="import-pw"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="선택"
              autoComplete="off"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={handleUpload} disabled={!file || createImport.isPending}>
            {createImport.isPending ? '업로드 중...' : '업로드'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
