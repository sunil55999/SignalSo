import { useState, useEffect } from 'react';

type ToastVariant = 'default' | 'destructive';

interface Toast {
  id: string;
  title?: string;
  description?: string;
  action?: React.ReactElement;
  variant?: ToastVariant;
}

let toastList: Toast[] = [];
let listeners: (() => void)[] = [];

const notifyListeners = () => {
  listeners.forEach((listener) => listener());
};

const addToast = (toast: Omit<Toast, 'id'>) => {
  const id = Math.random().toString(36).substring(2, 9);
  toastList.push({ ...toast, id });
  notifyListeners();
  
  // Auto-remove toast after 5 seconds
  setTimeout(() => {
    toastList = toastList.filter((t) => t.id !== id);
    notifyListeners();
  }, 5000);
};

const removeToast = (id: string) => {
  toastList = toastList.filter((t) => t.id !== id);
  notifyListeners();
};

export const useToast = () => {
  const [toasts, setToasts] = useState<Toast[]>(toastList);

  useEffect(() => {
    const listener = () => setToasts([...toastList]);
    listeners.push(listener);

    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  }, []);

  const toast = (toast: Omit<Toast, 'id'>) => {
    addToast(toast);
  };

  const dismiss = (id: string) => {
    removeToast(id);
  };

  return {
    toasts,
    toast,
    dismiss,
  };
};