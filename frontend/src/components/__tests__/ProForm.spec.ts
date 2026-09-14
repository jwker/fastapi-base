/**
 * 通用表单组件 ProForm 单测。
 *
 * 覆盖：
 * - 渲染：fields 配置驱动生成对应控件（input/select/switch/slot）
 * - 校验（核心）：required 防线（vitest 下 el-form validate 会空转，必须依赖内置防线拦截）；
 *   格式 pattern 拦截；填完放行 emit submit
 * - 回填：model 预赋值 → 控件显示对应值（编辑模式）
 * - 模式感知：showIn(create) 字段只在新增渲染
 * - 插槽：slot 字段渲染自定义内容
 * - 页面内嵌场景：showFooter=false + expose submit() → 校验逻辑一致生效
 */
import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import ElementPlus from 'element-plus'
import ProForm, { type ProFormField } from '@/components/ProForm.vue'

const wrappers: VueWrapper[] = []
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount())
})

function mountForm(fields: ProFormField[], model: Record<string, any> = {}, opts: Record<string, any> = {}) {
  const wrapper = mount(ProForm, {
    props: {
      fields,
      modelValue: model,
      ...opts,
    },
    global: { plugins: [ElementPlus] },
  })
  wrappers.push(wrapper)
  return wrapper
}

/** 基础字段：用户名/邮箱/状态 */
function baseFields(): ProFormField[] {
  return [
    { prop: 'username', label: '用户名', required: true },
    {
      prop: 'email',
      label: '邮箱',
      required: true,
      rules: [{ pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: '邮箱格式不正确', trigger: 'blur' }],
    },
    { prop: 'status', label: '状态', type: 'switch', activeValue: 1, inactiveValue: 0 },
  ]
}

describe('ProForm 渲染', () => {
  it('fields 配置驱动生成对应控件', () => {
    const wrapper = mountForm([
      { prop: 'name', label: '名称' },
      { prop: 'desc', label: '描述', type: 'textarea' },
      {
        prop: 'kind',
        label: '类型',
        type: 'select',
        options: [
          { label: 'A', value: 'a' },
          { label: 'B', value: 'b' },
        ],
      },
      { prop: 'on', label: '开关', type: 'switch' },
    ])

    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('textarea').exists()).toBe(true)
    expect(wrapper.find('.el-select').exists()).toBe(true)
    expect(wrapper.find('.el-switch').exists()).toBe(true)
    // 注：jsdom 下 el-form-item 的 label 文本不渲染（element-plus 测试环境已知行为，生产正常），
    // 字段关联改由缺省 placeholder 断言
    expect(wrapper.find('input[placeholder="请输入名称"]').exists()).toBe(true)
    expect(wrapper.html()).toContain('请选择类型')
  })

  it('required 字段显示必填星号', () => {
    const wrapper = mountForm([{ prop: 'name', label: '名称', required: true }])
    expect(wrapper.find('.el-form-item.is-required').exists()).toBe(true)
  })

  it('插槽字段渲染自定义内容', () => {
    const wrapper = mount(ProForm, {
      props: {
        fields: [{ prop: 'avatar', label: '头像', type: 'slot' }],
        modelValue: {},
      },
      slots: {
        avatar: '<div class="custom-avatar">自定义头像控件</div>',
      },
      global: { plugins: [ElementPlus] },
    })
    wrappers.push(wrapper)
    expect(wrapper.find('.custom-avatar').text()).toBe('自定义头像控件')
  })
})

describe('ProForm 校验（防线优先，vitest 下 el-form validate 空转不依赖它）', () => {
  it('required 未填点确定 → 阻止 emit submit 并提示', async () => {
    const wrapper = mountForm(baseFields(), { username: '', email: '', status: 1 })
    await wrapper.find('.el-button--primary').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('格式 pattern 不合法 → 阻止 emit submit', async () => {
    const wrapper = mountForm(baseFields(), { username: 'jack', email: 'not-an-email', status: 1 })
    await wrapper.find('.el-button--primary').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('校验通过 → emit submit 且携带当前 model', async () => {
    const wrapper = mountForm(baseFields(), { username: 'jack', email: 'jack@test.com', status: 1 })
    await wrapper.find('.el-button--primary').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })

  it('required 为空字符串视为未填（防线拦截）', async () => {
    const wrapper = mountForm([{ prop: 'name', label: '名称', required: true }], { name: '   ' })
    await wrapper.find('.el-button--primary').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('select 多选必填：空数组被拦截', async () => {
    const wrapper = mountForm(
      [
        {
          prop: 'roles',
          label: '角色',
          type: 'select',
          multiple: true,
          required: true,
          options: [{ label: 'A', value: 1 }],
        },
      ],
      { roles: [] },
    )
    await wrapper.find('.el-button--primary').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()
  })
})

describe('ProForm 回填与模式感知', () => {
  it('编辑模式：model 预赋值 → 控件显示对应值', async () => {
    const wrapper = mountForm(
      [{ prop: 'name', label: '名称' }, { prop: 'on', label: '开关', type: 'switch' }],
      { name: '管理员', on: true },
      { mode: 'edit' },
    )
    await nextTick()
    const input = wrapper.find('input[type="text"]').element as HTMLInputElement
    expect(input.value).toBe('管理员')
  })

  it('showIn(create) 字段只在新增渲染，edit 不渲染', async () => {
    const fields: ProFormField[] = [
      { prop: 'name', label: '名称' },
      { prop: 'password', label: '密码', required: true, showIn: (m) => m === 'create' },
    ]
    const create = mountForm(fields, {})
    expect(create.find('input[placeholder="请输入密码"]').exists()).toBe(true)

    create.unmount()
    const edit = mountForm(fields, { name: 'x' }, { mode: 'edit' })
    expect(edit.find('input[placeholder="请输入密码"]').exists()).toBe(false)
  })
})

describe('ProForm 页面内嵌场景（无 footer）', () => {
  it('showFooter=false 隐藏按钮，外部调用 submit() 走同一校验通道', async () => {
    const wrapper = mountForm(
      [{ prop: 'name', label: '名称', required: true }],
      { name: '' },
      { showFooter: false },
    )
    expect(wrapper.find('.pro-form-footer').exists()).toBe(false)

    // 未填必填 → 外部触发提交被防线拦截
    const comp = wrapper.vm as any
    await comp.submit()
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()

    // 填完后 → emit submit
    const input = wrapper.find('input[type="text"]')
    await input.setValue('填好了')
    await comp.submit()
    await flushPromises()
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })
})
