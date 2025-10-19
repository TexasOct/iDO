import { createClientTokenAuthentication } from 'alova/client'
import { createAlova } from 'alova'
import { jwtDecode } from 'jwt-decode'
import ReactHook from 'alova/react'

import adapterTauriFetch from './tauriFetch'
// import { refreshToken } from './user/auth'
import { useUserStore } from '../stores/user'

// 临时 refreshToken 函数
const refreshToken = async () => {
  // TODO: 实现刷新 token 的逻辑
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
          // token 不存在判断过期, claims 的 exp 字段判断不存在也视为过期
          if (!user.token) {
            return true
          }
          claims = jwtDecode(user.token as string)
          break
        // 登出上传 token， 默认直接放行
        case AuthRole.Logout:
          // refresh token 不存在也判断不存在也视为过期
          if (!user.refreshToken) {
            return true
          }
          claims = jwtDecode(user.token as string)
          break
        // 刷新 token，由 handler 判断问题
        case AuthRole.RefreshToken:
          return false
        // 不需要鉴权的接口, 直接返回 false
        case AuthRole.Login:
        case AuthRole.NoAuth:
        default:
          return false
      }

      if (!claims.exp) {
        return true
      }

      // JWT的exp字段以秒为单位，而Date.now()返回的是毫秒，需要除以1000转换为秒
      return claims.exp < Math.floor(Date.now() / 1000)
    },

    handler: async (_method) => {
      const user = useUserStore((state) => state)

      // 刷新 token 请求
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
      //...原响应成功拦截器
      const { status } = response
      // 异常处理
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
