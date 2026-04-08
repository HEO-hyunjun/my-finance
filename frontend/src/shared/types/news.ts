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
