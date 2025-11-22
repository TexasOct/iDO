import { createClientTokenAuthentication } from 'alova/client'
import { createAlova } from 'alova'
import { jwtDecode } from 'jwt-decode'
import ReactHook from 'alova/react'

import adapterTauriFetch from './tauriFetch'
// import { refreshToken } from './user/auth'
import { useUserStore } from '../stores/user'

// Temporary refreshToken function
const refreshToken = async () => {
  // TODO: Implement refresh token logic
  return { token: '', refresh_token: '' }
}

interface ResponseModel {
  code: number
  message: string
  data?: any
}

enum AuthRole {
  Login = 'login',
  Logout = 'logout',
  Auth = 'auth',
  NoAuth = 'noAuth',
  RefreshToken = 'refreshToken',
  Unknown = 'unknown'
}

const { onAuthRequired, onResponseRefreshToken } = createClientTokenAuthentication({
  refreshToken: {
    isExpired: (method) => {
      const user = useUserStore((state) => state)

      let claims
      switch (method.config.meta?.authRole) {
        case AuthRole.Auth:
          // If token or the exp claim is missing, treat it as expired
          if (!user.token) {
            return true
          }
          claims = jwtDecode(user.token as string)
          break
        // Allow logout uploads to pass through directly
        case AuthRole.Logout:
          // Missing refresh token also counts as expired
          if (!user.refreshToken) {
            return true
          }
          claims = jwtDecode(user.token as string)
          break
        // Refresh token requests are validated by the handler
        case AuthRole.RefreshToken:
          return false
        // Public endpoints do not require auth; return false
        case AuthRole.Login:
        case AuthRole.NoAuth:
        default:
          return false
      }

      if (!claims.exp) {
        return true
      }

      // JWT exp is in seconds but Date.now() is ms, so divide by 1000
      return claims.exp < Math.floor(Date.now() / 1000)
    },

    handler: async (_method) => {
      const user = useUserStore((state) => state)

      // Refresh token request
      try {
        if (!user.refreshToken) {
          throw new Error('No refresh token')
        }

        const claims = jwtDecode(user.refreshToken)

        if (!!!claims.exp || claims.exp < Math.floor(Date.now() / 1000)) {
          console.log('claims.exp', claims.exp, Date.now())
          throw new Error('Token expired')
        }

        const { token, refresh_token } = await refreshToken()
        user.tokenRefresh(token, refresh_token)
      } catch (error) {
        console.error('Failed to refresh token:', error)
        throw error
      }
    }
  },
  assignToken: (method) => {
    const user = useUserStore((state) => state)

    console.log('assign token', method)
    switch (method.config.meta?.authRole) {
      case AuthRole.Auth:
        method.config.headers.Authorization = `${user.token}`
        break
      case AuthRole.RefreshToken:
      case AuthRole.Logout:
        method.config.headers.Authorization = `${user.refreshToken}`
        break
      case AuthRole.Login:
      case AuthRole.NoAuth:
      default:
        break
    }
  }
})

export const alovaInstance = createAlova({
  baseURL: import.meta.env.VITE_API_URL,
  statesHook: ReactHook,
  cacheFor: null,
  requestAdapter: adapterTauriFetch(),
  beforeRequest: onAuthRequired((method) => {
    console.log(method)
  }),
  responded: onResponseRefreshToken({
    onSuccess: async (response, _method) => {
      console.log(_method)
      // ...original successful response interceptor
      const { status } = response
      // Error handling
      if (status > 500) {
        throw new Error(response.statusText)
      }

      const extract: ResponseModel = await response.json()

      if (status < 200 || (status >= 400 && status <= 500)) {
        throw new Error(extract.message)
      }

      return extract.data
    },
    onError: (error, method) => {
      console.log(method, error)
      throw error
    },
    onComplete: (_method) => {}
  })
})
