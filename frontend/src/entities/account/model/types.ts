export type AccountType = 'cash' | 'deposit' | 'savings' | 'parking' | 'investment';
export type InterestType = 'simple' | 'compound';

export interface Account {
  id: string;
  account_type: AccountType;
  name: string;
  currency: string;
  institution: string | null;
  interest_rate: number | null;
  interest_type: InterestType | null;
  monthly_amount: number | null;
  start_date: string | null;
  maturity_date: string | null;
  tax_rate: number | null;
  is_active: boolean;
  created_at: string;
}

export interface HoldingItem {
  security_id: string;
  symbol: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  currency: string;
  value: number;
  profit_loss: number;
  profit_loss_rate: number;
}

export interface AccountSummary {
  id: string;
  name: string;
  account_type: AccountType;
  currency: string;
  balance: number;
  cash_balance: number | null;
  holdings: HoldingItem[] | null;
}

export interface AccountCreate {
  account_type: AccountType;
  name: string;
  currency?: string;
  institution?: string | null;
  interest_rate?: number | null;
  interest_type?: InterestType | null;
  monthly_amount?: number | null;
  start_date?: string | null;
  maturity_date?: string | null;
  tax_rate?: number | null;
}

export interface AccountUpdate {
  name?: string | null;
  institution?: string | null;
  interest_rate?: number | null;
  interest_type?: InterestType | null;
  monthly_amount?: number | null;
  start_date?: string | null;
  maturity_date?: string | null;
  tax_rate?: number | null;
  is_active?: boolean | null;
}

export interface AdjustBalanceRequest {
  target_balance: number;
  currency?: string;
  memo?: string | null;
  security_id?: string | null;
  target_quantity?: number | null;
  unit_price?: number | null;
}
