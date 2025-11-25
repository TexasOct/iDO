import type { InsightTodo } from '@/lib/services/insights'

export type TodoDragView = 'month' | 'week' | 'day'

export interface DraggedTodoData {
  id: string
  title?: string
  description?: string
}

export interface TodoDragTarget {
  view: TodoDragView
  date: string
  time?: string
  key: string
}

type DropHandler = (todo: DraggedTodoData, target: TodoDragTarget) => void | Promise<void>

const TARGET_CHANGE_EVENT = 'todo-drag-target-change'
const DRAG_END_EVENT = 'todo-drag-end'

interface DragSession {
  pointerId: number
  payload: DraggedTodoData
  sourceElement: HTMLElement
  preview?: HTMLElement
  started: boolean
  startX: number
  startY: number
  previewOffsetX: number
  previewOffsetY: number
  currentTarget?: TodoDragTarget
  clickSuppressor?: (event: MouseEvent) => void
}

const DRAG_THRESHOLD = 4 // px
const PREVIEW_OFFSET_X = 16
const PREVIEW_OFFSET_Y = 12

let activeSession: DragSession | null = null
let dropHandler: DropHandler | null = null

export function registerTodoDropHandler(handler: DropHandler) {
  dropHandler = handler
}

export function unregisterTodoDropHandler(handler: DropHandler) {
  if (dropHandler === handler) {
    dropHandler = null
  }
}

export function beginTodoPointerDrag(event: React.PointerEvent<HTMLElement>, todo: InsightTodo) {
  if (event.button !== 0) return
  if (activeSession) {
    cancelDrag()
  }

  event.preventDefault()

  const payload: DraggedTodoData = {
    id: todo.id,
    title: todo.title,
    description: todo.description
  }

  console.log('[Drag] Begin drag:', payload.title)

  const sourceElement = event.currentTarget as HTMLElement
  const rect = sourceElement.getBoundingClientRect()

  activeSession = {
    pointerId: event.pointerId,
    payload,
    sourceElement,
    started: false,
    startX: event.clientX,
    startY: event.clientY,
    previewOffsetX: event.clientX - rect.left,
    previewOffsetY: event.clientY - rect.top
  }

  sourceElement.setPointerCapture?.(event.pointerId)

  window.addEventListener('pointermove', handlePointerMove, true)
  window.addEventListener('pointerup', handlePointerUp, true)
  window.addEventListener('pointercancel', handlePointerCancel, true)
  window.addEventListener('keydown', handleKeyDown, true)
}

function handlePointerMove(event: PointerEvent) {
  if (!activeSession || event.pointerId !== activeSession.pointerId) return

  if (!activeSession.started) {
    const deltaX = event.clientX - activeSession.startX
    const deltaY = event.clientY - activeSession.startY
    if (Math.abs(deltaX) + Math.abs(deltaY) < DRAG_THRESHOLD) {
      return
    }
    startDrag(event)
  }

  event.preventDefault()
  updatePreviewPosition(event.clientX, event.clientY)
  updateDropTarget(event.clientX, event.clientY)
}

function handlePointerUp(event: PointerEvent) {
  if (!activeSession || event.pointerId !== activeSession.pointerId) return

  event.preventDefault()
  finishDrag(true)
}

function handlePointerCancel(event: PointerEvent) {
  if (!activeSession || event.pointerId !== activeSession.pointerId) return
  finishDrag(false)
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape' && activeSession) {
    event.preventDefault()
    finishDrag(false)
  }
}

function startDrag(event: PointerEvent) {
  if (!activeSession) return
  activeSession.started = true

  // Use the Card element directly (sourceElement), not the container
  const source = activeSession.sourceElement
  const container = source.closest('[data-todo-container]') as HTMLElement | null

  const preview = createDragPreviewElement(source)
  document.body.appendChild(preview)
  activeSession.preview = preview

  // Add opacity to container if it exists, otherwise to source
  const targetForOpacity = container || source
  targetForOpacity.classList.add('opacity-50')

  const suppressClick = (clickEvent: MouseEvent) => {
    clickEvent.stopPropagation()
    clickEvent.preventDefault()
  }
  source.addEventListener('click', suppressClick, true)
  activeSession.clickSuppressor = suppressClick
  updatePreviewPosition(event.clientX, event.clientY)
}

function updatePreviewPosition(clientX: number, clientY: number) {
  if (!activeSession?.preview) return
  const x = clientX - activeSession.previewOffsetX + PREVIEW_OFFSET_X
  const y = clientY - activeSession.previewOffsetY + PREVIEW_OFFSET_Y
  activeSession.preview.style.transform = `translate(${x}px, ${y}px)`
}

function updateDropTarget(clientX: number, clientY: number) {
  if (!activeSession) return

  // Hide preview temporarily to allow elementFromPoint to find the element behind it
  const preview = activeSession.preview
  if (preview) {
    preview.style.pointerEvents = 'none'
  }

  const element = document.elementFromPoint(clientX, clientY)

  // Restore preview visibility
  if (preview) {
    preview.style.pointerEvents = 'none' // Keep it as none
  }

  console.log('[Drag] elementFromPoint:', element?.tagName, element?.className, (element as HTMLElement)?.dataset)

  const targetElement = element?.closest<HTMLElement>('[data-todo-dropzone]')

  if (!targetElement) {
    if (activeSession.currentTarget) {
      console.log('[Drag] No dropzone found')
      activeSession.currentTarget = undefined
      dispatchTargetChange(null)
    }
    return
  }

  const target = extractDropTarget(targetElement)
  if (!target) {
    if (activeSession.currentTarget) {
      console.log('[Drag] Invalid target element:', targetElement.dataset)
      activeSession.currentTarget = undefined
      dispatchTargetChange(null)
    }
    return
  }

  if (activeSession.currentTarget?.key !== target.key) {
    console.log('[Drag] Target changed:', target)
    activeSession.currentTarget = target
    dispatchTargetChange(target)
  }
}

function extractDropTarget(element: HTMLElement): TodoDragTarget | null {
  const view = element.dataset.todoDropzone as TodoDragView | undefined
  const date = element.dataset.dropDate
  if (!view || !date) {
    return null
  }
  const time = element.dataset.dropTime
  const key = element.dataset.dropKey || `${view}-${date}-${time ?? 'all'}`
  return { view, date, time: time || undefined, key }
}

function dispatchTargetChange(target: TodoDragTarget | null) {
  window.dispatchEvent(new CustomEvent(TARGET_CHANGE_EVENT, { detail: target }))
}

function finishDrag(shouldDrop: boolean) {
  if (!activeSession) return
  const { preview, sourceElement, currentTarget, payload, started, clickSuppressor } = activeSession

  console.log('[Drag] Finish drag:', {
    shouldDrop,
    started,
    hasTarget: !!currentTarget,
    hasHandler: !!dropHandler,
    target: currentTarget
  })

  preview?.remove()

  // Remove opacity from container or source
  const container = sourceElement.closest('[data-todo-container]') as HTMLElement | null
  const targetForOpacity = container || sourceElement
  targetForOpacity.classList.remove('opacity-50')

  sourceElement.releasePointerCapture?.(activeSession.pointerId)
  if (clickSuppressor) {
    sourceElement.removeEventListener('click', clickSuppressor, true)
  }
  dispatchTargetChange(null)
  window.dispatchEvent(new CustomEvent(DRAG_END_EVENT))

  cleanupListeners()
  const session = activeSession
  activeSession = null

  if (shouldDrop && started && currentTarget && dropHandler) {
    console.log('[Drag] Calling dropHandler with:', payload, currentTarget)
    Promise.resolve(dropHandler(payload, currentTarget)).catch((error) => {
      console.error('Failed to handle todo drop:', error)
    })
  } else {
    console.log('[Drag] Drop cancelled or no target')
  }

  return session
}

function cancelDrag() {
  if (!activeSession) return
  finishDrag(false)
}

function cleanupListeners() {
  window.removeEventListener('pointermove', handlePointerMove, true)
  window.removeEventListener('pointerup', handlePointerUp, true)
  window.removeEventListener('pointercancel', handlePointerCancel, true)
  window.removeEventListener('keydown', handleKeyDown, true)
}

export const todoDragEvents = {
  TARGET_CHANGE_EVENT,
  DRAG_END_EVENT
}

function createDragPreviewElement(source: HTMLElement): HTMLElement {
  const preview = source.cloneNode(true) as HTMLElement
  const rect = source.getBoundingClientRect()

  // Set essential styles
  preview.style.position = 'fixed'
  preview.style.width = `${rect.width}px`
  preview.style.pointerEvents = 'none'
  preview.style.zIndex = '9999'
  preview.style.transform = 'translate(-9999px, -9999px)'
  preview.style.opacity = '0.9'
  preview.style.boxShadow = '0 20px 45px rgba(15, 23, 42, 0.45)'
  preview.style.borderRadius = '12px'
  preview.style.transition = 'none'
  preview.style.willChange = 'transform'

  // Get computed background, but ensure it's visible
  const computedBg = window.getComputedStyle(source).backgroundColor
  if (computedBg && computedBg !== 'rgba(0, 0, 0, 0)' && computedBg !== 'transparent') {
    preview.style.background = computedBg
  } else {
    preview.style.background = 'rgba(15,23,42,0.95)'
  }

  const computedBorder = window.getComputedStyle(source).border
  preview.style.border = computedBorder || '1px solid rgba(59,130,246,0.4)'

  preview.classList.add('todo-drag-preview')

  // Ensure all children also have pointer-events: none
  preview.querySelectorAll('*').forEach((child) => {
    ;(child as HTMLElement).style.pointerEvents = 'none'
  })

  return preview
}
