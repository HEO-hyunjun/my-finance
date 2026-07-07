import { CreateEntryDialog } from '@/features/entries/ui/CreateEntryDialog';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function GlobalCreateEntryDialog({ isOpen, onClose }: Props) {
  return <CreateEntryDialog isOpen={isOpen} onClose={onClose} />;
}
