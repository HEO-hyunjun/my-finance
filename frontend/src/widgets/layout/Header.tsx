import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Sun, Moon, Menu, Plus, ArrowLeftRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { useTheme } from "@/app/providers/ThemeProvider";
import { useCategories, useCreateExpense } from "@/features/budget/api";
import { AddExpenseModal } from "@/features/budget/ui/AddExpenseModal";
import { useAssets, useCreateTransaction } from "@/features/assets/api";
import { AddTransactionModal } from "@/features/assets/ui/AddTransactionModal";

const PAGE_TITLES: Record<string, string> = {
  "/": "대시보드",
  "/assets": "자산 관리",
  "/budget": "예산 관리",
  "/calendar": "캘린더",
  "/transactions": "거래 내역",
  "/news": "뉴스",
  "/chatbot": "AI 챗봇",
  "/settings": "설정",
};

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const location = useLocation();
  const { resolvedTheme, setTheme } = useTheme();
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showTxModal, setShowTxModal] = useState(false);

  const { data: categories = [] } = useCategories();
  const createExpense = useCreateExpense();
  const { data: assets = [] } = useAssets();
  const createTx = useCreateTransaction();

  const title = PAGE_TITLES[location.pathname] || "";

  const toggleTheme = () => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  };

  return (
    <>
      <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur-sm md:px-6">
        {/* Mobile menu button */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onMenuClick}
          aria-label="메뉴 열기"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <h1 className="text-lg font-semibold">{title}</h1>

        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="default"
            size="sm"
            onClick={() => setShowExpenseModal(true)}
            className="gap-1.5"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">지출 추가</span>
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowTxModal(true)}
            className="gap-1.5"
          >
            <ArrowLeftRight className="h-4 w-4" />
            <span className="hidden sm:inline">거래 기록</span>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="h-9 w-9"
            aria-label="테마 전환"
          >
            {resolvedTheme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
        </div>
      </header>

      <AddExpenseModal
        categories={categories}
        isOpen={showExpenseModal}
        onClose={() => setShowExpenseModal(false)}
        onSubmit={(data) => createExpense.mutate(data)}
        isLoading={createExpense.isPending}
      />

      <AddTransactionModal
        isOpen={showTxModal}
        onClose={() => setShowTxModal(false)}
        onSubmit={(data) => createTx.mutate(data, { onSuccess: () => setShowTxModal(false) })}
        assets={assets}
        isLoading={createTx.isPending}
      />
    </>
  );
}
