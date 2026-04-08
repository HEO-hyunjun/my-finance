export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface ApiError {
  detail: string;
}

export type UUID = string;

export type AssetType =
  | 'stock_kr' | 'stock_us' | 'gold' | 'cash_krw' | 'cash_usd'
  | 'deposit' | 'savings' | 'parking' | 'crypto' | 'real_estate' | 'other';

export const ASSET_TYPE_LABELS: Record<string, string> = {
  stock_kr: '국내주식',
  stock_us: '해외주식',
  gold: '금',
  cash_krw: '원화현금',
  cash_usd: '달러현금',
  deposit: '예금',
  savings: '적금',
  parking: '파킹통장',
  crypto: '암호화폐',
  real_estate: '부동산',
  other: '기타',
};

export const TRANSACTION_TYPE_LABELS: Record<string, string> = {
  buy: '매수',
  sell: '매도',
  exchange: '환전',
  deposit_in: '입금',
  withdraw: '출금',
  interest: '이자',
  dividend: '배당',
};

export interface Asset {
  id: string;
  name: string;
  asset_type: AssetType;
  currency: string;
  quantity: number;
  unit_price: number;
  current_price: number | null;
  value_krw: number;
  invested_krw: number;
  profit_loss: number;
  profit_loss_rate: number;
  bank_name: string | null;
  account_number: string | null;
  maturity_date: string | null;
  annual_rate: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}
