# Frontend Development Guide

This guide covers frontend development for iDO, including component structure, state management, and best practices.

## Quick Links

- [Components](./components.md) - Component architecture and patterns
- [State Management](./state-management.md) - Zustand stores and data flow
- [Styling](./styling.md) - Tailwind CSS guidelines

## Technology Stack

- **React 19** - UI framework
- **TypeScript 5** - Type safety
- **Vite 6** - Build tool
- **Tailwind CSS 4** - Styling
- **Zustand 5** - State management
- **React Router** - Navigation
- **i18next** - Internationalization

## Project Structure

```
src/
├── views/              # Page-level components (routes)
│   ├── Activity/
│   ├── Dashboard/
│   ├── Agents/
│   └── Settings/
│
├── components/         # Reusable components
│   ├── shared/        # Shared across views
│   ├── activity/      # Activity-specific
│   ├── agents/        # Agent-specific
│   └── settings/      # Settings-specific
│
├── lib/
│   ├── stores/        # Zustand state stores
│   ├── client/        # Auto-generated API client
│   ├── types/         # TypeScript definitions
│   ├── config/        # Configuration
│   └── utils/         # Utilities
│
├── hooks/             # Custom React hooks
├── locales/           # i18n translations
└── assets/            # Static assets
```

## Development Workflow

### Starting Development

```bash
# Frontend only (fastest iteration)
pnpm dev

# Full app with backend
pnpm tauri:dev:gen-ts
```

### Creating a New View

1. Create directory in `src/views/`:
```typescript
// src/views/MyFeature/index.tsx
export default function MyFeatureView() {
  return (
    <div>
      <h1>My Feature</h1>
    </div>
  )
}
```

2. Add route in `src/lib/config/menu.ts`:
```typescript
export const menuItems: MenuItem[] = [
  {
    id: 'myFeature',
    label: 'myFeature.title',
    icon: IconName,
    path: '/my-feature',
    component: lazy(() => import('@/views/MyFeature'))
  }
]
```

3. Add i18n translations:
```typescript
// src/locales/en.ts
export const en = {
  myFeature: {
    title: 'My Feature'
  }
}
```

### Using API Client

The API client is auto-generated from Python handlers:

```typescript
import { apiClient } from '@/lib/client'

// Call backend handler
const result = await apiClient.getActivities({
  startDate: '2024-01-01',
  endDate: '2024-01-31'
})

// Type-safe response
result.activities.forEach(activity => {
  console.log(activity.title)  // TypeScript autocomplete works
})
```

### State Management with Zustand

```typescript
// Define store
const useMyStore = create<MyState>((set, get) => ({
  data: [],
  loading: false,
  
  fetchData: async () => {
    set({ loading: true })
    try {
      const result = await apiClient.getData()
      set({ data: result.data, loading: false })
    } catch (error) {
      set({ loading: false })
      toast.error('Failed to fetch data')
    }
  }
}))

// Use in component
function MyComponent() {
  const { data, loading, fetchData } = useMyStore()
  
  useEffect(() => {
    fetchData()
  }, [fetchData])
  
  if (loading) return <Loading />
  return <div>{data.map(...)}</div>
}
```

## Common Patterns

### Form Handling

```typescript
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email')
})

function MyForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema)
  })
  
  const onSubmit = async (data) => {
    await apiClient.saveData(data)
  }
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} />
      {errors.name && <span>{errors.name.message}</span>}
    </form>
  )
}
```

### Real-Time Updates

```typescript
import { useTauriEvents } from '@/hooks/useTauriEvents'

function ActivityTimeline() {
  const addActivity = useActivityStore(state => state.addActivity)
  
  useTauriEvents({
    'activity-created': (payload) => {
      addActivity(payload)
      toast.success('New activity captured')
    }
  })
  
  return <Timeline />
}
```

### Conditional Rendering

```typescript
function ActivityCard({ activity }) {
  const { t } = useTranslation()
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>{activity.title}</CardTitle>
      </CardHeader>
      <CardContent>
        {activity.screenshots.length > 0 ? (
          <ImageGallery images={activity.screenshots} />
        ) : (
          <p className="text-muted-foreground">
            {t('activity.noScreenshots')}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

## Best Practices

### Performance

```typescript
// ✅ Use React.memo for expensive components
export const ExpensiveComponent = React.memo(({ data }) => {
  // ...
})

// ✅ Use Zustand selectors to prevent unnecessary re-renders
const name = useStore(state => state.user.name)  // Only re-renders when name changes

// ✅ Lazy load routes
const SettingsView = lazy(() => import('@/views/Settings'))

// ✅ Use virtual scrolling for long lists
<StickyTimelineGroup items={1000s_of_items} />
```

### Type Safety

```typescript
// ✅ Define proper types
interface Activity {
  id: string
  title: string
  startTime: Date
}

// ✅ Use type guards
function isActivity(obj: unknown): obj is Activity {
  return typeof obj === 'object' && obj !== null && 'id' in obj
}

// ❌ Avoid any
const data: any = await fetchData()  // Bad

// ✅ Use proper types
const data: Activity[] = await fetchData()  // Good
```

### Error Handling

```typescript
// ✅ Handle errors gracefully
try {
  await apiClient.saveData(data)
  toast.success('Saved successfully')
} catch (error) {
  if (error instanceof ApiError) {
    toast.error(error.message)
  } else {
    toast.error('An unexpected error occurred')
  }
}

// ✅ Use error boundaries
<ErrorBoundary fallback={<ErrorFallback />}>
  <MyComponent />
</ErrorBoundary>
```

## Testing

```typescript
import { render, screen } from '@testing-library/react'
import { ActivityCard } from './ActivityCard'

test('renders activity title', () => {
  const activity = {
    id: '1',
    title: 'Test Activity',
    startTime: new Date()
  }
  
  render(<ActivityCard activity={activity} />)
  expect(screen.getByText('Test Activity')).toBeInTheDocument()
})
```

## Debugging

### React DevTools
- Install React DevTools browser extension
- Inspect component tree
- View props and state
- Profile performance

### Zustand DevTools
```typescript
import { devtools } from 'zustand/middleware'

const useStore = create(
  devtools((set) => ({
    // ... store definition
  }))
)
```

### Browser Console
```typescript
// Debug API calls
console.log('Fetching activities:', { startDate, endDate })

// Debug render cycles
console.log('Component rendered', { props, state })
```

## Next Steps

- 📖 [Component Guide](./components.md) - Learn component patterns
- 📊 [State Management](./state-management.md) - Master Zustand stores  
- 🎨 [Styling Guide](./styling.md) - Use Tailwind CSS effectively
- 🌍 [i18n Guide](../features/i18n.md) - Add translations
- 🏗️ [Architecture](../../architecture/README.md) - Understand the big picture
