import { useRef, useState } from "react";
import { FileText, RefreshCw, Trash2, Upload } from "lucide-react";
import { api, parseApiError } from "@/services/api";
import type { DocumentItem, DocumentType } from "@/types";
import { DOC_LABEL, bytes } from "@/utils/format";
import { Spinner } from "./ui/Feedback";

interface Props {
  docType: DocumentType;
  uploadUrl: string;
  current?: DocumentItem;
  required?: boolean;
  disabled?: boolean;
  accept: "image" | "image-or-pdf";
  maxMb: number;
  hint?: string;
  error?: string;
  onUploaded: (doc: DocumentItem) => void;
  onRemove?: (doc: DocumentItem) => Promise<void> | void;
}

export function FileUpload({ docType, uploadUrl, current, required, disabled, accept, maxMb, hint, error, onUploaded, onRemove }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const acceptAttr = accept === "image" ? ".jpg,.jpeg,.png,image/jpeg,image/png" : ".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf";
  const label = DOC_LABEL[docType];

  async function handle(file: File) {
    setLocalError(null);
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    const allowed = accept === "image" ? ["jpg", "jpeg", "png"] : ["jpg", "jpeg", "png", "pdf"];
    if (!allowed.includes(ext)) return setLocalError(`Choose a ${allowed.map((a) => a.toUpperCase()).join(", ")} file.`);
    if (file.size > maxMb * 1024 * 1024) return setLocalError(`The file is larger than ${maxMb} MB.`);
    const fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("file", file);
    setBusy(true);
    try {
      const { data } = await api.post<DocumentItem>(uploadUrl, fd);
      onUploaded(data);
    } catch (e) {
      setLocalError(parseApiError(e, "Upload failed.").message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  const shownError = localError ?? error;
  const isImage = current?.content_type.startsWith("image/");
  return (
    <div className={`flex gap-4 border bg-white p-3 ${shownError ? "border-danger" : "border-line"}`}>
      <div className="flex h-24 w-20 shrink-0 items-center justify-center overflow-hidden border border-dashed border-forest/30 bg-ivory">
        {current && isImage ? (
          <img src={current.url} alt={label} className="h-full w-full object-cover" />
        ) : current ? (
          <FileText className="h-8 w-8 text-forest/70" aria-hidden="true" />
        ) : (
          <Upload className="h-6 w-6 text-forest/40" aria-hidden="true" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[15px] font-medium text-ink">
          {label}{required && <span className="ml-0.5 text-register" aria-hidden="true">*</span>}
        </p>
        {current ? (
          <p className="truncate text-sm text-ink-soft">
            <a href={current.url} target="_blank" rel="noreferrer" className="underline decoration-forest/30 hover:text-forest">{current.original_filename}</a>
            {" "}({bytes(current.size_bytes)})
          </p>
        ) : (
          <p className="text-sm text-ink-muted">{hint ?? (accept === "image" ? `JPG or PNG, up to ${maxMb} MB` : `JPG, PNG or PDF, up to ${maxMb} MB`)}</p>
        )}
        {shownError && <p className="mt-1 text-[13px] text-danger" role="alert">{shownError}</p>}
        {!disabled && (
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" onClick={() => input.current?.click()} disabled={busy}
              className="inline-flex items-center gap-1.5 rounded border border-forest/40 px-2.5 py-1 text-sm text-forest hover:bg-forest-50 disabled:opacity-60">
              {busy ? <Spinner className="h-4 w-4" /> : current ? <RefreshCw className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
              {current ? "Replace" : "Upload"}
            </button>
            {current && onRemove && (
              <button type="button" onClick={() => onRemove(current)} disabled={busy}
                className="inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-sm text-ink-soft hover:bg-sage">
                <Trash2 className="h-4 w-4" /> Remove
              </button>
            )}
            <input ref={input} type="file" accept={acceptAttr} className="sr-only" aria-label={`Upload ${label}`}
              onChange={(e) => e.target.files?.[0] && handle(e.target.files[0])} />
          </div>
        )}
      </div>
    </div>
  );
}
