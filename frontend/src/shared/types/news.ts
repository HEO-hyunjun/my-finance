export interface NewsSource {
  name: string;
  icon: string | null;
}

export interface NewsArticle {
  id: string;
  title: string;
  link: string;
  source: NewsSource;
  snippet: string | null;
  raw_content: string | null;
  thumbnail: string | null;
  published_at: string;
  category: string;
  related_asset: string | null;
}

export interface NewsListResponse {
  articles: NewsArticle[];
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface MyAssetNewsResponse {
  articles: NewsArticle[];
  asset_queries: string[];
}

export type NewsCategory = 'all' | 'stocks' | 'crypto' | 'economy' | 'my_assets';

export interface NewsArticleDetail {
  id: string;
  title: string;
  link: string;
  source_name: string;
  source_icon: string | null;
  snippet: string | null;
  raw_content: string | null;
  thumbnail: string | null;
  published_at: string;
  category: string;
  related_asset: string | null;
  sentiment: string | null;
  sentiment_score: number | null;
  summary: string | null;
  keywords: string | null;
  processed_at: string | null;
}

export interface NewsCluster {
  id: string;
  title: string;
  summary: string;
  keywords: string[];
  article_count: number;
  importance_score: number;
  sentiment: string;
}

export interface NewsClustersResponse {
  clusters: NewsCluster[];
  is_processing: boolean;
  analyzed_at: string | null;
}
