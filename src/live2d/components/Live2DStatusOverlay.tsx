import type { CSSProperties, FC } from 'react'

type Live2DStatusOverlayProps = {
  status: 'loading' | 'ready' | 'error'
  errorMessage?: string | null
}

const baseStyle: CSSProperties = {
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  borderRadius: '12px',
  padding: '16px 24px',
  fontSize: '14px',
  color: '#ffffffcc',
  backdropFilter: 'blur(12px)',
  boxShadow: 'none'
}

export const Live2DStatusOverlay: FC<Live2DStatusOverlayProps> = ({ status, errorMessage }) => {
  if (status === 'loading') {
    return <div style={{ ...baseStyle, background: 'rgba(32, 33, 36, 0.75)' }}>Loading model...</div>
  }

  if (status === 'error') {
    return (
      <div style={{ ...baseStyle, background: 'rgba(209, 67, 67, 0.8)', color: '#fff' }}>
        <div>模型加载失败</div>
        {errorMessage && <div style={{ marginTop: '6px', fontSize: '12px', opacity: 0.9 }}>{errorMessage}</div>}
      </div>
    )
  }

  return null
}
