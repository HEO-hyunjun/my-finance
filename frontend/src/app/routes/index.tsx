import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '@/widgets/layout/AppLayout';

export const router = createBrowserRouter([
  // Auth pages (no layout)
  {
    path: '/login',
    lazy: () => import('@/pages/auth/login'),
  },
  {
    path: '/register',
    lazy: () => import('@/pages/auth/register'),
  },
  // App pages (with layout)
  {
    element: <AppLayout />,
    children: [
      {
        path: '/',
        lazy: () => import('@/pages/dashboard'),
      },
      {
        path: '/assets',
        lazy: () => import('@/pages/assets'),
      },
      {
        path: '/budget',
        lazy: () => import('@/pages/budget'),
      },
      {
        path: '/news',
        lazy: () => import('@/pages/news'),
      },
      {
        path: '/calendar',
        lazy: () => import('@/pages/calendar'),
      },
      {
        path: '/chatbot',
        lazy: () => import('@/pages/chatbot'),
      },
      {
        path: '/expenses',
        lazy: () => import('@/pages/expenses'),
      },
      {
        path: '/transactions',
        lazy: () => import('@/pages/transactions'),
      },
      {
        path: '/settings',
        lazy: () => import('@/pages/settings'),
      },
    ],
  },
]);
