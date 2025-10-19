import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined })
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen w-screen flex-col items-center justify-center p-4">
          <div className="flex flex-col items-center text-center max-w-md">
            <div className="rounded-full bg-destructive/10 p-6">
              <AlertCircle className="h-10 w-10 text-destructive" />
            </div>
            <h1 className="mt-4 text-2xl font-semibold">出错了</h1>
            <p className="mt-2 text-sm text-muted-foreground">应用遇到了一个意外错误</p>
            {this.state.error && <pre className="mt-4 text-xs text-muted-foreground bg-muted p-2 rounded max-w-full overflow-auto">{this.state.error.message}</pre>}
            <div className="mt-6 flex gap-2">
              <Button onClick={this.handleReset}>重试</Button>
              <Button variant="outline" onClick={() => window.location.reload()}>
                重新加载页面
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
