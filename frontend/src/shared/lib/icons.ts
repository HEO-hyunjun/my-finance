import {
  TrendingUp,
  Coins,
  Banknote,
  PiggyBank,
  Building2,
  Landmark,
  Wallet,
  TrendingDown,
  AlertCircle,
  CheckCircle2,
  Utensils,
  Bus,
  ShoppingBag,
  Home,
  Zap,
  Heart,
  GraduationCap,
  Gift,
  Smartphone,
  MoreHorizontal,
  type LucideIcon,
} from 'lucide-react';

export const ASSET_TYPE_ICONS: Record<string, LucideIcon> = {
  STOCK: TrendingUp,
  GOLD: Coins,
  CASH: Banknote,
  DEPOSIT: PiggyBank,
  SAVINGS: Landmark,
  REAL_ESTATE: Building2,
  CRYPTO: Wallet,
  DEFAULT: Wallet,
};

export const CATEGORY_ICONS: Record<string, LucideIcon> = {
  식비: Utensils,
  교통: Bus,
  쇼핑: ShoppingBag,
  주거: Home,
  통신: Smartphone,
  공과금: Zap,
  의료: Heart,
  교육: GraduationCap,
  경조사: Gift,
  기타: MoreHorizontal,
  DEFAULT: MoreHorizontal,
};

export const STATUS_ICONS = {
  profit: TrendingUp,
  loss: TrendingDown,
  warning: AlertCircle,
  success: CheckCircle2,
} as const;

export function getAssetIcon(type: string): LucideIcon {
  return ASSET_TYPE_ICONS[type] || ASSET_TYPE_ICONS.DEFAULT;
}

export function getCategoryIcon(name: string): LucideIcon {
  return CATEGORY_ICONS[name] || CATEGORY_ICONS.DEFAULT;
}
