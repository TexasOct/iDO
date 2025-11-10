import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { UserProfile, UserState } from '@/lib/types/profile'

interface UserStoreState extends UserState {
  // Actions
  login: (token: string, refreshToken: string, profile?: UserProfile) => void
  logout: () => void
  tokenRefresh: (token: string, refreshToken: string) => void
  updateProfile: (profile: UserProfile) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

const initialState: UserState = {
  profile: null,
  token: null,
  refreshToken: null,
  isLoading: false,
  error: null,
  isAuthenticated: false
}

export const useUserStore = create<UserStoreState>()(
  persist(
    (set) => ({
      ...initialState,

      login: (token, refreshToken, profile) =>
        set({
          token,
          refreshToken,
          profile: profile || null,
          isAuthenticated: true,
          error: null
        }),

      logout: () =>
        set({
          ...initialState,
          isAuthenticated: false
        }),

      tokenRefresh: (token, refreshToken) =>
        set({
          token,
          refreshToken
        }),

      updateProfile: (profile) =>
        set({
          profile
        }),

      setLoading: (isLoading) =>
        set({
          isLoading
        }),

      setError: (error) =>
        set({
          error
        })
    }),
    {
      name: 'ido-user',
      // Only persist authentication tokens and profile
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        profile: state.profile,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)
