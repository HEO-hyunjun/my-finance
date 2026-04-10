export interface PriceResponse {
  symbol: string;
  name: string | null;
  price: number;
  currency: string;
  change: number | null;
  change_percent: number | null;
  is_market_open: boolean;
  cached: boolean;
}

export interface ExchangeRateResponse {
  pair: string;
  rate: number;
  change: number | null;
  change_percent: number | null;
  cached: boolean;
}

export interface MarketTrendItem {
  symbol: string;
  name: string;
  price: number;
  change: number | null;
  change_percent: number | null;
  currency: string;
}

export interface MarketTrendsResponse {
  indices: MarketTrendItem[];
  gainers: MarketTrendItem[];
  losers: MarketTrendItem[];
  cached: boolean;
}

export interface MarketSearchResult {
  symbol: string;
  name: string;
  exchange: string | null;
  asset_type: string | null;
}

export interface MarketSearchResponse {
  query: string;
  results: MarketSearchResult[];
  cached: boolean;
}

export interface RefreshPriceRequest { symbol: string; exchange?: string; }
