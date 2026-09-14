<script setup lang="ts">
/**
 * 通用表单组件：字段配置驱动渲染，与 ProTable（列配置驱动表格）对称。
 *
 * props:
 *  - fields: 字段配置 [{ prop, label, type?, required?, rules?, options?, ... }]
 *  - mode: 'create' | 'edit' —— 模式感知（showIn 显隐 / required 生效范围）
 *  - submitLoading: 确定按钮 loading（提交中禁用）
 *  - showFooter: 是否渲染「取消/确定」footer（页面内嵌表单时隐藏，由页面按钮触发）
 *  - labelWidth: el-form 标签宽度
 *
 * v-model: model —— 表单值（编辑模式父组件直接赋 editRow 即回填）
 *
 * events:
 *  - submit: 点击确定/外部调 submit() 且校验通过后触发
 *  - cancel: 点击取消触发
 *
 * 校验（分层，吸收 Profile 双重防线教训）：
 *  1. el-form rules（输入即时反馈）：required 自动 + 自定义 rules（pattern/validator）
 *  2. 内置"提交防线"：确定性必填/格式检查，不依赖 el-form 校验时机（vitest 下 el-form validate 会空转），
 *     保证提交拦截在任何环境都生效
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormItemRule } from 'element-plus'

export type ProFormMode = 'create' | 'edit'

export interface ProFormField {
  /** 绑定字段名 */
  prop: string
  /** 标签 */
  label: string
  /** 控件类型，缺省 input；slot 时渲染具名插槽（slot 名 = field.slot ?? field.prop） */
  type?: 'input' | 'textarea' | 'number' | 'select' | 'switch' | 'slot'
  /** input 原生类型（如 password 显示密码框） */
  inputType?: 'text' | 'password'
  /** placeholder：字符串或按模式函数（如编辑模式"留空则不修改"） */
  placeholder?: string | ((mode: ProFormMode) => string)
  /** 必填：布尔或按模式函数（如密码仅 create 必填）——自动星号 + 校验 + 提交防线 */
  required?: boolean | ((mode: ProFormMode) => boolean)
  /** 额外规则（格式正则/长度/自定义 validator），与 required 合并 */
  rules?: FormItemRule[]
  /** select 选项 */
  options?: { label: string; value: string | number; disabled?: boolean }[]
  /** select 多选 */
  multiple?: boolean
  /** switch 开/关绑定值（默认 true/false，如 status 用 1/0） */
  activeValue?: unknown
  inactiveValue?: unknown
  /** switch 开/关旁文字 */
  activeText?: string
  inactiveText?: string
  /** disabled：布尔或函数（如编辑模式禁用编码） */
  disabled?: boolean | ((model: Record<string, any>) => boolean)
  /** textarea 行数 */
  rows?: number
  /** number 边界 */
  min?: number
  max?: number
  /** 一行多列：占 24 份（默认 24 全宽） */
  colSpan?: number
  /** 模式显隐：如密码 showIn: m => m === 'create' */
  showIn?: (mode: ProFormMode) => boolean
  /** type='slot' 时的插槽名 */
  slot?: string
}

const props = withDefaults(
  defineProps<{
    fields: ProFormField[]
    mode?: ProFormMode
    submitLoading?: boolean
    showFooter?: boolean
    submitText?: string
    labelWidth?: string
  }>(),
  {
    mode: 'create',
    submitLoading: false,
    showFooter: true,
    submitText: '确定',
    labelWidth: '70px',
  },
)

const model = defineModel<Record<string, any>>({ default: () => ({}) })
const emit = defineEmits<{ (e: 'submit'): void; (e: 'cancel'): void }>()

const formRef = ref<FormInstance>()

/** 模式感知后的可见字段 */
const visibleFields = computed(() =>
  props.fields.filter((f) => (f.showIn ? f.showIn(props.mode) : true)),
)

function resolveRequired(f: ProFormField): boolean {
  return typeof f.required === 'function' ? f.required(props.mode) : f.required ?? false
}

/** el-form rules：required 自动生成 + 自定义规则合并 */
const formRules = computed<Record<string, FormItemRule[]>>(() => {
  const rules: Record<string, FormItemRule[]> = {}
  for (const f of visibleFields.value) {
    const list: FormItemRule[] = []
    if (resolveRequired(f)) {
      list.push({ required: true, message: `请输入${f.label}`, trigger: 'blur' })
    }
    if (f.rules?.length) list.push(...f.rules)
    if (list.length) rules[f.prop] = list
  }
  return rules
})

function resolveDisabled(f: ProFormField): boolean {
  if (typeof f.disabled === 'function') return f.disabled(model.value)
  return f.disabled ?? false
}

/** placeholder 缺省自动生成（提示 + 便于测试/无障碍） */
function resolvePlaceholder(f: ProFormField): string | undefined {
  const raw = typeof f.placeholder === 'function' ? f.placeholder(props.mode) : f.placeholder
  if (raw) return raw
  if (f.type === 'select') return `请选择${f.label}`
  return `请输入${f.label}`
}

/**
 * 提交防线：确定性必填/格式检查，不依赖 el-form 校验时机。
 * 与 rules 同源（均由 fields 配置生成），返回第一条错误文案或 null。
 */
function guardMessage(): string | null {
  for (const f of visibleFields.value) {
    if (!resolveRequired(f)) continue
    const v = model.value[f.prop]
    if (f.type === 'select' && f.multiple) {
      if (Array.isArray(v) && !v.length) return `请选择${f.label}`
    } else if (typeof v === 'string' ? !v.trim() : v === null || v === undefined) {
      return `请输入${f.label}`
    }
  }
  for (const f of visibleFields.value) {
    for (const r of f.rules ?? []) {
      if (r.pattern instanceof RegExp && typeof model.value[f.prop] === 'string') {
        const v = (model.value[f.prop] as string).trim()
        if (v && !r.pattern.test(v)) return (r.message as string) || `${f.label}格式不正确`
      }
    }
  }
  return null
}

async function submit() {
  const guard = guardMessage()
  if (guard) {
    ElMessage.warning(guard)
    return
  }
  // el-form validate 兜底（覆盖异步 validator / 跨字段一致性等防线不覆盖的规则）
  const valid = await formRef.value?.validate().catch(() => false)
  if (valid === false) return
  emit('submit')
}

defineExpose({ submit })
</script>

<template>
  <div class="pro-form">
    <el-form
      ref="formRef"
      :model="model"
      :rules="formRules"
      :label-width="labelWidth"
      @submit.prevent
    >
      <el-form-item
        v-for="f in visibleFields"
        :key="f.prop"
        :label="f.label"
        :prop="f.prop"
        :required="resolveRequired(f)"
        class="pro-form-item"
        :class="{ 'pro-form-item-wide': (f.colSpan ?? 24) >= 24 }"
        :style="f.colSpan && f.colSpan < 24 ? { width: `${(f.colSpan / 24) * 100}%` } : undefined"
      >
        <!-- input -->
        <el-input
          v-if="!f.type || f.type === 'input'"
          v-model="model[f.prop]"
          :type="f.inputType ?? 'text'"
          :show-password="f.inputType === 'password'"
          :placeholder="resolvePlaceholder(f)"
          :disabled="resolveDisabled(f)"
          clearable
        />
        <!-- textarea -->
        <el-input
          v-else-if="f.type === 'textarea'"
          v-model="model[f.prop]"
          type="textarea"
          :rows="f.rows ?? 2"
          :placeholder="resolvePlaceholder(f)"
          :disabled="resolveDisabled(f)"
        />
        <!-- number -->
        <el-input-number
          v-else-if="f.type === 'number'"
          v-model="model[f.prop]"
          :min="f.min"
          :max="f.max"
          :disabled="resolveDisabled(f)"
        />
        <!-- select -->
        <el-select
          v-else-if="f.type === 'select'"
          v-model="model[f.prop]"
          :placeholder="resolvePlaceholder(f)"
          :multiple="f.multiple"
          :disabled="resolveDisabled(f)"
          clearable
        >
          <el-option
            v-for="o in f.options ?? []"
            :key="o.value"
            :label="o.label"
            :value="o.value"
            :disabled="o.disabled"
          />
        </el-select>
        <!-- switch -->
        <el-switch
          v-else-if="f.type === 'switch'"
          v-model="model[f.prop]"
          :active-value="f.activeValue ?? true"
          :inactive-value="f.inactiveValue ?? false"
          :active-text="f.activeText"
          :inactive-text="f.inactiveText"
          :disabled="resolveDisabled(f)"
        />
        <!-- slot：复杂控件（头像 FileUpload、图标选择、级联树等） -->
        <slot
          v-else-if="f.type === 'slot'"
          :name="f.slot ?? f.prop"
          :model="model"
        />
        <!-- 兜底：未知类型渲染 input，避免白屏 -->
        <el-input v-else v-model="model[f.prop]" :placeholder="resolvePlaceholder(f)" />
      </el-form-item>
    </el-form>

    <div v-if="showFooter" class="pro-form-footer">
      <el-button :disabled="submitLoading" @click="emit('cancel')">取消</el-button>
      <el-button type="primary" :loading="submitLoading" @click="submit">
        {{ submitText }}
      </el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.pro-form-item {
  margin-bottom: 18px;

  &.pro-form-item-wide {
    width: 100%;
  }
}

.pro-form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
</style>
