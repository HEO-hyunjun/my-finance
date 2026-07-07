import { TrendingUp, TrendingDown } from 'lucide-react';
import { useExchangeRate, useMarketPrice } from '@/features/market/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { WidgetError } from './WidgetError';

export function MarketInfoWidget() {
  const { data: exchangeRate, isLoading, isError } = useExchangeRate();
  const { data: goldPrice } = useMarketPrice('KRX:GOLD');

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">시세 정보</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : isError ? (
          <WidgetError />
        ) : (
          <div className="space-y-3">
            {/* USD/KRW 환율 */}
            {exchangeRate && (
              <div className="flex items-center justify-between rounded-lg bg-muted/40 p-3">
                <div>
                  <p className="text-xs text-muted-foreground">{exchangeRate.pair}</p>
                  <p className="text-lg font-bold">
                    {exchangeRate.rate.toLocaleString('ko-KR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">원</span>
                  </p>
                </div>
                {exchangeRate.change != null && (
                  <div className="text-right">
                    <p
                      className={`flex items-center gap-0.5 text-sm font-medium ${
                        exchangeRate.change >= 0 ? 'text-destructive' : 'text-green-600'
                      }`}
                    >
                      {exchangeRate.change >= 0 ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {Math.abs(exchangeRate.change).toFixed(2)}
                    </p>
                    {exchangeRate.change_percent != null && (
                      <p className="text-xs text-muted-foreground">
                        {exchangeRate.change_percent >= 0 ? '+' : ''}
                        {exchangeRate.change_percent.toFixed(2)}%
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
            {/* 금 시세 */}
            {goldPrice && (
              <div className="flex items-center justify-between rounded-lg bg-muted/40 p-3">
                <div>
                  <p className="text-xs text-muted-foreground">{goldPrice.name ?? '금 (KRX)'}</p>
                  <p className="text-lg font-bold">
                    {goldPrice.price.toLocaleString('ko-KR')}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">원/g</span>
                  </p>
                </div>
                {goldPrice.change != null && (
                  <div className="text-right">
                    <p
                      className={`flex items-center gap-0.5 text-sm font-medium ${
                        goldPrice.change >= 0 ? 'text-green-600' : 'text-destructive'
                      }`}
                    >
                      {goldPrice.change >= 0 ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {Math.abs(goldPrice.change).toLocaleString('ko-KR')}
                    </p>
                    {goldPrice.change_percent != null && (
                      <p className="text-xs text-muted-foreground">
                        {goldPrice.change_percent >= 0 ? '+' : ''}
                        {goldPrice.change_percent.toFixed(2)}%
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
