import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '@/widgets/layout/AppLayout';
import { AuthGuard } from '@/features/auth/ui/AuthGuard';

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
    element: <AuthGuard><AppLayout /></AuthGuard>,
    children: [
      {
        path: '/',
        lazy: () => import('@/pages/dashboard'),
      },
      {
        path: '/accounts',
        lazy: () => import('@/pages/accounts'),
      },
      {
        path: '/entries',
        lazy: () => import('@/pages/entries'),
      },
      {
        path: '/schedules',
        lazy: () => import('@/pages/schedules'),
      },
      {
        path: '/budget',
        lazy: () => import('@/pages/budget'),
      },
      {
        path: '/portfolio',
        lazy: () => import('@/pages/portfolio'),
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
        path: '/settings',
        lazy: () => import('@/pages/settings'),
      },
    ],
  },
]);
