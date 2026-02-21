import { Link } from 'react-router-dom';
import type { NewsArticle } from '@/shared/types';

interface Props {
  article: NewsArticle;
}

export function NewsCard({ article }: Props) {
  return (
    <Link
      to={`/news/${article.id}`}
      className="flex gap-4 px-4 py-3.5 transition-colors hover:bg-muted/50"
    >
      {/* 썸네일 (데스크톱만 표시) */}
      {article.thumbnail && (
        <img
          src={article.thumbnail}
          alt=""
          className="hidden md:block h-24 w-24 flex-shrink-0 rounded-lg object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      )}

      <div className="min-w-0 flex-1">
        {/* 제목 */}
        <h3 className="text-sm font-medium leading-snug line-clamp-2">
          {article.title}
        </h3>

        {/* 출처 + 시간 */}
        <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
          {article.source.icon && (
            <img
              src={article.source.icon}
              alt=""
              className="h-4 w-4 rounded-full"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          )}
          <span>{article.source.name}</span>
          <span>·</span>
          <span>{article.published_at}</span>
        </div>

        {/* 스니펫 */}
        {article.snippet && (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {article.snippet}
          </p>
        )}

        {/* 관련 자산 태그 */}
        {article.related_asset && (
          <span className="mt-1.5 inline-block rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600">
            {article.related_asset}
          </span>
        )}
      </div>
    </Link>
  );
}
