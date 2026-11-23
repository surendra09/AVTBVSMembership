import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Button } from "./Button";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

export function Modal({ open, onClose, title, children, footer, wide }: ModalProps) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && panel.current) {
        const f = panel.current.querySelectorAll<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    setTimeout(() => panel.current?.querySelector<HTMLElement>("textarea, input, select, button:not([aria-label='Close'])")?.focus(), 0);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 p-0 sm:items-center sm:p-6" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={panel} role="dialog" aria-modal="true" aria-labelledby="modal-title"
        className={`max-h-[92vh] w-full overflow-auto rounded-t-lg bg-white shadow-soft sm:rounded-lg ${wide ? "sm:max-w-3xl" : "sm:max-w-lg"}`}>
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <h2 id="modal-title" className="text-xl">{title}</h2>
          <button aria-label="Close" onClick={onClose} className="rounded p-1 text-ink-muted hover:bg-sage hover:text-ink">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-line bg-ivory/50 px-5 py-3">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

interface ConfirmProps {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  danger?: boolean;
  disabled?: boolean;
}

export function ConfirmDialog({ open, title, children, confirmLabel, onConfirm, onCancel, loading, danger, disabled }: ConfirmProps) {
  return (
    <Modal open={open} onClose={onCancel} title={title} footer={<>
      <Button variant="quiet" onClick={onCancel} disabled={loading}>Cancel</Button>
      <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={loading} disabled={disabled}>{confirmLabel}</Button>
    </>}>
      <div className="space-y-3 text-[15px] text-ink-soft">{children}</div>
    </Modal>
  );
}
