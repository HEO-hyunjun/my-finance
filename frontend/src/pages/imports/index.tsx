import { useState } from 'react';
import { UploadCard } from '@/features/imports/ui/UploadCard';
import { BatchList } from '@/features/imports/ui/BatchList';
import { ImportReview } from '@/features/imports/ui/ImportReview';

export function Component() {
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-6">
      <div>
        <h1 className="text-2xl font-bold">가져오기</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          엑셀·CSV·PDF 거래내역을 업로드하고 검토 후 반영합니다.
        </p>
      </div>

      {selectedBatchId ? (
        <ImportReview batchId={selectedBatchId} onBack={() => setSelectedBatchId(null)} />
      ) : (
        <>
          <UploadCard />
          <BatchList onSelect={setSelectedBatchId} />
        </>
      )}
    </div>
  );
}
