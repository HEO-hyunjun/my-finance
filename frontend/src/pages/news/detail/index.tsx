import { useParams, useNavigate } from 'react-router-dom';
import { useNewsArticleDetail } from '@/features/news/api';
import { Card, CardContent } from '@/shared/ui/card';

const SENTIMENT_LABELS: Record<string, { text: string; color: string }> = {
  positive: { text: '긍정', color: 'text-green-600 bg-green-50' },
  negative: { text: '부정', color: 'text-red-600 bg-red-50' },
  neutral: { text: '중립', color: 'text-gray-600 bg-gray-50' },
};

export function Component() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: article, isLoading, isError } = useNewsArticleDetail(id ?? '');

  if (isLoading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-8 w-3/4 rounded bg-gray-200" />
        <div className="h-4 w-1/4 rounded bg-gray-100" />
        <div className="h-64 rounded bg-gray-100" />
      </div>
    );
  }

  if (isError || !article) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-muted-foreground">기사를 찾을 수 없습니다.</p>
            <button
              onClick={() => navigate('/news')}
              className="mt-4 text-sm text-blue-600 hover:text-blue-800"
            >
              뉴스 목록으로 돌아가기
            </button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const sentiment = SENTIMENT_LABELS[article.sentiment ?? ''] ?? SENTIMENT_LABELS.neutral;
  const keywords = article.keywords?.split(',').map((k) => k.trim()).filter(Boolean) ?? [];

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* 뒤로가기 */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        돌아가기
      </button>

      {/* 헤더 */}
      <div>
        <h1 className="text-xl font-bold leading-tight">{article.title}</h1>
        <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
          {article.source_icon && (
            <img
              src={article.source_icon}
              alt=""
              className="h-4 w-4 rounded-full"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
          <span>{article.source_name}</span>
          <span>·</span>
          <span>{article.published_at}</span>
        </div>
      </div>

      {/* 썸네일 */}
      {article.thumbnail && (
        <img
          src={article.thumbnail}
          alt=""
          className="w-full rounded-xl object-cover max-h-80"
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
      )}

      {/* LLM 분석 결과 */}
      {article.processed_at && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold">AI 분석</h2>
              <span className={`text-xs px-2 py-0.5 rounded-full ${sentiment.color}`}>
                {sentiment.text}
                {article.sentiment_score != null && (
                  <span className="ml-1">({article.sentiment_score > 0 ? '+' : ''}{article.sentiment_score.toFixed(1)})</span>
                )}
              </span>
            </div>

            {article.summary && (
              <p className="text-sm text-muted-foreground leading-relaxed">
                {article.summary}
              </p>
            )}

            {keywords.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {keywords.map((kw) => (
                  <span
                    key={kw}
                    className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 본문 */}
      <Card>
        <CardContent className="p-4">
          {article.raw_content ? (
            <div className="prose prose-sm max-w-none text-sm leading-relaxed whitespace-pre-line">
              {article.raw_content}
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground leading-relaxed">
                {article.snippet || '본문 내용이 없습니다.'}
              </p>
              <a
                href={article.link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
              >
                원문 보기
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 원문 링크 */}
      {article.raw_content && (
        <div className="text-center">
          <a
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            원문 보기
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      )}
    </div>
  );
}
