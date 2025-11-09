import { App } from '@/views/App'
import { MainLayout } from '@/layouts/MainLayout'
import { createBrowserRouter, Navigate } from 'react-router'
import { lazy, Suspense } from 'react'
import { LoadingPage } from '@/components/shared/LoadingPage'

// 懒加载页面组件
const ActivityView = lazy(() => import('@/views/Activity'))
const RecentEventsView = lazy(() => import('@/views/RecentEvents'))
const AIKnowledgeView = lazy(() => import('@/views/AIKnowledge'))
const AITodosView = lazy(() => import('@/views/AITodos'))
const AIDiaryView = lazy(() => import('@/views/AIDiary'))
const DashboardView = lazy(() => import('@/views/Dashboard'))
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
            element: <Navigate to="/insights/knowledge" replace />
          },
          {
            path: 'insights/knowledge',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <AIKnowledgeView />
              </Suspense>
            )
          },
          {
            path: 'insights/todos',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <AITodosView />
              </Suspense>
            )
          },
          {
            path: 'insights/diary',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <AIDiaryView />
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
