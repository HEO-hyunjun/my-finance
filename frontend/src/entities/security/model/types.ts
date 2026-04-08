export type AssetClass = 'equity_kr' | 'equity_us' | 'commodity' | 'currency_pair';
export type DataSource = 'yahoo' | 'manual';

export interface Security {
  id: string;
  symbol: string;
  name: string;
  currency: string;
  asset_class: AssetClass;
  data_source: DataSource;
  exchange: string | null;
  created_at: string;
}

export interface SecurityPrice {
  id: string;
  security_id: string;
  price_date: string;
  close_price: number;
  currency: string;
  created_at: string;
}
