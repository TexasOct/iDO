import { App } from '@/views/App'
import { MainLayout } from '@/layouts/MainLayout'
import { createBrowserRouter, Navigate } from 'react-router'
import { lazy, Suspense } from 'react'
import { LoadingPage } from '@/components/shared/LoadingPage'

// 懒加载页面组件
const ActivityView = lazy(() => import('@/views/Activity'))
const RecentEventsView = lazy(() => import('@/views/RecentEvents'))
const AISummaryView = lazy(() => import('@/views/AISummary'))
const DashboardView = lazy(() => import('@/views/Dashboard'))
const AgentsView = lazy(() => import('@/views/Agents'))
const ChatView = lazy(() => import('@/views/Chat'))
const SettingsView = lazy(() => import('@/views/Settings'))

export const router = createBrowserRouter([
  {
    path: '/',
    Component: App,
    children: [
      {
        path: '/',
        Component: MainLayout,
        children: [
          {
            index: true,
            element: <Navigate to="/activity" replace />
          },
          {
            path: 'activity',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <ActivityView />
              </Suspense>
            )
          },
          {
            path: 'events',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <RecentEventsView />
              </Suspense>
            )
          },
          {
            path: 'insights',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <AISummaryView />
              </Suspense>
            )
          },
          {
            path: 'dashboard',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <DashboardView />
              </Suspense>
            )
          },
          {
            path: 'agents',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <AgentsView />
              </Suspense>
            )
          },
          {
            path: 'chat',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <ChatView />
              </Suspense>
            )
          },
          {
            path: 'settings',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <SettingsView />
              </Suspense>
            )
          }
        ]
      }
    ]
  }
])
