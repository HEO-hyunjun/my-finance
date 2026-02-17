import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { TransactionFilter } from '@/features/transaction/ui/TransactionFilter';
import { useFilteredTransactions } from '@/features/transaction/api';
import { TransactionList } from '@/features/assets/ui/TransactionList';
import { useDeleteTransaction } from '@/features/assets/api';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Skeleton } from '@/shared/ui/skeleton';

interface Filters {
  asset_type?: string;
  tx_type?: string;
  start_date?: string;
  end_date?: string;
}

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<Filters>({});
  const page = Number(searchParams.get('page')) || 1;
  const perPage = 20;

  const { data, isLoading, isError, refetch } = useFilteredTransactions({
    ...filters,
    page,
    per_page: perPage,
  });
  const deleteTx = useDeleteTransaction();

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(newFilters);
    setSearchParams((prev) => { prev.delete('page'); return prev; });
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Filter */}
      <TransactionFilter onFilterChange={handleFilterChange} />

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-12 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" aria-hidden="true" />
            <p className="text-muted-foreground mb-4">거래 내역을 불러올 수 없습니다.</p>
            <Button onClick={() => refetch()}>다시 시도</Button>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {data && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              총 <span className="font-semibold text-foreground">{data.total.toLocaleString()}</span>건
            </p>
          </div>

          <TransactionList
            transactions={data.data}
            total={data.total}
            page={page}
            perPage={perPage}
            onPageChange={(p) => setSearchParams((prev) => { prev.set('page', String(p)); return prev; })}
            onDelete={(id) => deleteTx.mutate(id)}
          />
        </>
      )}
    </div>
  );
}
