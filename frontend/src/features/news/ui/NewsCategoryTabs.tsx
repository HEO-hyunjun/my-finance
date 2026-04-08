import type { NewsCategory } from '@/shared/types/news';
import { NEWS_CATEGORIES } from '../lib/constants';
import { Button } from '@/shared/ui/button';

interface Props {
  activeCategory: NewsCategory;
  onChange: (cat: NewsCategory) => void;
}

export function NewsCategoryTabs({ activeCategory, onChange }: Props) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {NEWS_CATEGORIES.map((cat) => (
        <Button
          key={cat.value}
          variant={activeCategory === cat.value ? 'default' : 'secondary'}
          size="sm"
          onClick={() => onChange(cat.value)}
          className="whitespace-nowrap rounded-full"
        >
          {cat.label}
        </Button>
      ))}
    </div>
  );
}
