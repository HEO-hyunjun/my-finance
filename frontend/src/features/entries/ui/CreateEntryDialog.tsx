import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/shared/ui/dialog';
import { EntryForm } from './EntryForm';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateEntryDialog({ isOpen, onClose }: Props) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>거래 추가</DialogTitle>
        </DialogHeader>
        {isOpen && <EntryForm onSuccess={onClose} onCancel={onClose} />}
      </DialogContent>
    </Dialog>
  );
}
