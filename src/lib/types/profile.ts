/**
 * User profile and authentication types
 */

export interface UserProfile {
  id: string
  username: string
  email: string
  avatar?: string
  createdAt?: string
  updatedAt?: string
}

export interface AuthTokens {
  token: string
  refreshToken: string
}

export interface UserState {
  // User profile data
  profile: UserProfile | null

  // Authentication tokens
  token: string | null
  refreshToken: string | null

  // Loading state
  isLoading: boolean
  error: string | null

  // Whether user is authenticated
  isAuthenticated: boolean
}
