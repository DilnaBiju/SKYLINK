import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, tokenStore } from './api.js'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!tokenStore.get())

  useEffect(() => {
    if (!tokenStore.get()) return
    api.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setReady(true))
  }, [])

  const logout = useCallback(() => { tokenStore.clear(); setUser(null) }, [])
  useEffect(() => {
    window.addEventListener('skylink:unauthorized', logout)
    return () => window.removeEventListener('skylink:unauthorized', logout)
  }, [logout])

  const accept = (res) => { tokenStore.set(res.token); setUser(res.user); return res.user }
  const value = {
    user, ready, setUser, logout,
    login: async (email, password) => accept(await api.login({ email, password })),
    register: async (data) => accept(await api.register(data)),
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
