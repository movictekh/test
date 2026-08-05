import { createContext } from 'react'

import type { ToastContextValue } from './toast.types'

export const ToastContext = createContext<ToastContextValue | undefined>(undefined)
