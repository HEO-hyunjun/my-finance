import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useNewsFeed } from '@/features/news/api';
import { NewsCategoryTabs } from '@/features/news/ui/NewsCategoryTabs';
import { NewsSearchBar } from '@/features/news/ui/NewsSearchBar';
import { NewsCard } from '@/features/news/ui/NewsCard';
import { NewsCardSkeleton } from '@/features/news/ui/NewsCardSkeleton';
import { NewsClusterView } from '@/features/news/ui/NewsClusterView';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/shared/ui/tabs';
import { Card, CardContent } from '@/shared/ui/card';
import type { NewsCategory } from '@/shared/types';

type NewsViewTab = 'latest' | 'clusters';

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams();
  const viewTab = (searchParams.get('view') as NewsViewTab) || 'latest';
  const [category, setCategory] = useState<NewsCategory>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // 디바운스
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useNewsFeed(category, debouncedSearch);

  // Intersection Observer로 무한 스크롤
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const articles = data?.pages.flatMap((p) => p.articles) ?? [];

  return (
    <div className="p-6 space-y-4">
      {/* 뷰 탭: 최신 뉴스 | 이슈별 보기 */}
      <Tabs value={viewTab} onValueChange={(v) => setSearchParams((prev) => { prev.set('view', v); return prev; })}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="latest">최신 뉴스</TabsTrigger>
          <TabsTrigger value="clusters">이슈별 보기</TabsTrigger>
        </TabsList>

        <TabsContent value="latest" className="space-y-4">
          <NewsCategoryTabs activeCategory={category} onChange={setCategory} />
          <NewsSearchBar value={search} onChange={setSearch} />

          {isLoading && (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <NewsCardSkeleton key={i} />
              ))}
            </div>
          )}

          {isError && (
            <Card>
              <CardContent className="p-12 text-center">
                <p className="text-muted-foreground">뉴스를 불러올 수 없습니다.</p>
              </CardContent>
            </Card>
          )}

          {!isLoading && !isError && articles.length === 0 && (
            <Card>
              <CardContent className="p-12 text-center">
                <p className="text-muted-foreground">뉴스가 없습니다.</p>
                {category === 'my_assets' && (
                  <p className="mt-2 text-sm text-muted-foreground/70">
                    자산을 등록하면 관련 뉴스를 볼 수 있어요.
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {articles.length > 0 && (
            <div className="divide-y rounded-xl border border-border bg-card">
              {articles.map((article) => (
                <NewsCard key={article.id} article={article} />
              ))}
            </div>
          )}

          {/* 무한 스크롤 센티넬 */}
          <div ref={sentinelRef} className="h-4" />

          {isFetchingNextPage && (
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <NewsCardSkeleton key={`loading-${i}`} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="clusters">
          <NewsClusterView />
        </TabsContent>
      </Tabs>
    </div>
  );
}
