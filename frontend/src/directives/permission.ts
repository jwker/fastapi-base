/**
 * v-permission 指令：按钮级权限控制。
 * 用法：<el-button v-permission="'user:delete'">删除</el-button>
 * 无权限时移除元素。
 */
import type { Directive, DirectiveBinding } from 'vue'
import { useUserStore } from '@/stores/user'

function check(el: HTMLElement, binding: DirectiveBinding<string>) {
  const userStore = useUserStore()
  const code = binding.value
  if (!code) return
  if (userStore.isSuperuser) return
  if (!userStore.permissions.includes(code)) {
    el.parentNode?.removeChild(el)
  }
}

const permission: Directive<HTMLElement, string> = {
  mounted: check,
  updated: check,
}

export default permission
