import { Button } from '@/shared/ui/button';

interface Props {
  onSelect: (question: string) => void;
}

const SUGGESTIONS = [
  '내 자산 포트폴리오를 분석해줘',
  '이번 달 예산 사용 현황을 알려줘',
  '투자 포트폴리오 리밸런싱이 필요할까?',
  '이번 달 절약할 수 있는 부분이 있을까?',
  '현재 환율 기준으로 달러 자산 가치는?',
  '예금/적금 만기 일정을 정리해줘',
];

export function SuggestedQuestions({ onSelect }: Props) {
  return (
    <div className="flex flex-wrap justify-center gap-2 px-4">
      {SUGGESTIONS.map((q) => (
        <Button
          key={q}
          variant="outline"
          onClick={() => onSelect(q)}
          className="rounded-full text-xs sm:text-sm"
          aria-label={`질문하기: ${q}`}
        >
          {q}
        </Button>
      ))}
    </div>
  );
}
