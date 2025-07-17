import { useState, useCallback } from 'react';

type ToastType = 'default' | 'success' | 'error' | 'warning';

interface Toast {
  id: string;
  title?: string;
  description?: string;
  type?: ToastType;
  action?: React.ReactNode;
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
}

let toastId = 0;

export function useToast() {
  const [state, setState] = useState<ToastState>({ toasts: [] });

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${toastId++}`;
    const newToast: Toast = {
      id,
      duration: 5000,
      type: 'default',
      ...toast,
    };

    setState((prevState) => ({
      toasts: [...prevState.toasts, newToast],
    }));

    // Auto-remove toast after duration
    setTimeout(() => {
      setState((prevState) => ({
        toasts: prevState.toasts.filter((t) => t.id !== id),
      }));
    }, newToast.duration);

    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setState((prevState) => ({
      toasts: prevState.toasts.filter((t) => t.id !== id),
    }));
  }, []);

  const toast = useCallback((toast: Omit<Toast, 'id'>) => {
    return addToast(toast);
  }, [addToast]);

  toast.success = useCallback((toast: Omit<Toast, 'id' | 'type'>) => {
    return addToast({ ...toast, type: 'success' });
  }, [addToast]);

  toast.error = useCallback((toast: Omit<Toast, 'id' | 'type'>) => {
    return addToast({ ...toast, type: 'error' });
  }, [addToast]);

  toast.warning = useCallback((toast: Omit<Toast, 'id' | 'type'>) => {
    return addToast({ ...toast, type: 'warning' });
  }, [addToast]);

  return {
    toasts: state.toasts,
    toast,
    removeToast,
  };
}