import { defineStore } from 'pinia'

type ThemeMode = 'light' | 'dark'

interface AppState {
  theme: ThemeMode
  sidebarCollapsed: boolean
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    theme: 'light',
    sidebarCollapsed: false,
  }),
  actions: {
    toggleTheme() {
      this.theme = this.theme === 'light' ? 'dark' : 'light'
      this.applyTheme()
    },
    applyTheme() {
      const el = document.documentElement
      if (this.theme === 'dark') el.classList.add('dark')
      else el.classList.remove('dark')
    },
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
  },
  persist: {
    key: 'fb-app',
    pick: ['theme', 'sidebarCollapsed'],
  },
})
