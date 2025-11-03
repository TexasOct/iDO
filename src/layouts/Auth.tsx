import { GalleryVerticalEnd } from 'lucide-react'
import { Outlet } from 'react-router'
import { ThemeToggle } from '@/components/system/theme/theme-toggle'

function AuthLayout() {
  return (
    <div className="relative flex min-h-svh flex-col">
      <div className="grid flex-1 grid-cols-5">
        <div className="col-span-2 flex flex-col gap-4 p-6 md:p-10">
          <div className="flex w-full items-center justify-between">
            <a href="#" className="flex items-center gap-2 font-medium">
              <div className="bg-primary text-primary-foreground flex h-6 w-6 items-center justify-center rounded-md">
                <GalleryVerticalEnd className="size-4" />
              </div>
              Acme Inc.
            </a>
            <ThemeToggle />
          </div>
          <div className="flex flex-1 items-center justify-center">
            <div className="w-full max-w-xs">
              <Outlet />
            </div>
          </div>
        </div>
        <div className="bg-muted relative col-span-3">
          <img
            src="/src-tauri/icons/Square310x310Logo.png"
            alt="Image"
            className="absolute inset-0 h-full w-full object-cover dark:brightness-[0.2] dark:grayscale"
          />
        </div>
      </div>
    </div>
  )
}

export { AuthLayout }
