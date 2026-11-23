import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

interface FieldProps {
  label: string;
  error?: string;
  hint?: ReactNode;
  required?: boolean;
  children: (id: string, describedBy: string | undefined) => ReactNode;
  className?: string;
}

export function Field({ label, error, hint, required, children, className = "" }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errId = error ? `${id}-err` : undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-ink">
        {label}
        {required && <span className="ml-0.5 text-register" aria-hidden="true">*</span>}
      </label>
      {children(id, [hintId, errId].filter(Boolean).join(" ") || undefined)}
      {hint && !error && <p id={hintId} className="mt-1 text-[13px] text-ink-muted">{hint}</p>}
      {error && <p id={errId} className="mt-1 text-[13px] text-danger">{error}</p>}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: ReactNode; wrapperClassName?: string };

export const TextField = forwardRef<HTMLInputElement, InputProps>(function TextField(
  { label, error, hint, required, wrapperClassName, className = "", ...rest }, ref) {
  return (
    <Field label={label} error={error} hint={hint} required={required} className={wrapperClassName}>
      {(id, describedBy) => (
        <input ref={ref} id={id} aria-invalid={!!error || undefined} aria-describedby={describedBy}
          aria-required={required || undefined} className={`field-input ${className}`} {...rest} />
      )}
    </Field>
  );
});

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; error?: string; hint?: ReactNode; wrapperClassName?: string };

export const TextAreaField = forwardRef<HTMLTextAreaElement, TextareaProps>(function TextAreaField(
  { label, error, hint, required, wrapperClassName, className = "", rows = 3, ...rest }, ref) {
  return (
    <Field label={label} error={error} hint={hint} required={required} className={wrapperClassName}>
      {(id, describedBy) => (
        <textarea ref={ref} id={id} rows={rows} aria-invalid={!!error || undefined} aria-describedby={describedBy}
          aria-required={required || undefined} className={`field-input resize-y ${className}`} {...rest} />
      )}
    </Field>
  );
});

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { label: string; error?: string; hint?: ReactNode; options: { value: string; label: string }[]; placeholder?: string; wrapperClassName?: string };

export const SelectField = forwardRef<HTMLSelectElement, SelectProps>(function SelectField(
  { label, error, hint, required, options, placeholder, wrapperClassName, className = "", ...rest }, ref) {
  return (
    <Field label={label} error={error} hint={hint} required={required} className={wrapperClassName}>
      {(id, describedBy) => (
        <select ref={ref} id={id} aria-invalid={!!error || undefined} aria-describedby={describedBy}
          className={`field-input ${className}`} {...rest}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      )}
    </Field>
  );
});

type CheckboxProps = InputHTMLAttributes<HTMLInputElement> & { label: ReactNode; error?: string; description?: ReactNode };

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, error, description, className = "", ...rest }, ref) {
  const id = useId();
  return (
    <div className={className}>
      <div className="flex items-start gap-3">
        <input ref={ref} id={id} type="checkbox" aria-invalid={!!error || undefined}
          className="mt-1 h-4 w-4 shrink-0 rounded-sm border-line accent-forest" {...rest} />
        <label htmlFor={id} className="text-[15px] text-ink">
          {label}
          {description && <span className="mt-0.5 block text-sm text-ink-muted">{description}</span>}
        </label>
      </div>
      {error && <p className="ml-7 mt-1 text-[13px] text-danger">{error}</p>}
    </div>
  );
});
