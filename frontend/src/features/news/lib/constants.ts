import type { NewsCategory } from '@/shared/types';

export const NEWS_CATEGORIES: { value: NewsCategory; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'my_assets', label: '내 보유자산' },
  { value: 'stock_kr', label: '국내주식' },
  { value: 'stock_us', label: '해외주식' },
  { value: 'gold', label: '금' },
  { value: 'economy', label: '경제' },
];
