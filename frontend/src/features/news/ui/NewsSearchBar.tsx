import { Search } from 'lucide-react';
import { Input } from '@/shared/ui/input';

interface Props {
  value: string;
  onChange: (q: string) => void;
}

export function NewsSearchBar({ value, onChange }: Props) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="뉴스 검색..."
        className="pl-9"
      />
    </div>
  );
}
