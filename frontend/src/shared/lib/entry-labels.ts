export const ENTRY_TYPE_LABELS: Record<string, string> = {
  income: '수입',
  expense: '지출',
  transfer_in: '입금(이체)',
  transfer_out: '출금(이체)',
  buy: '매수',
  sell: '매도',
  dividend: '배당',
  interest: '이자',
  fee: '수수료',
  adjustment: '조정',
};

export const ENTRY_TYPE_BG: Record<string, string> = {
  income: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  expense: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  transfer_in: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  transfer_out: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
  buy: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  sell: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  dividend: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  interest: 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-500',
  fee: 'bg-red-50 text-red-500 dark:bg-red-900/20 dark:text-red-400',
  adjustment: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};
