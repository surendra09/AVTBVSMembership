import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { PublicConfig } from "@/types";

let cache: PublicConfig | null = null;
let pending: Promise<PublicConfig> | null = null;

export const FALLBACK_CONFIG: PublicConfig = {
  app_name: "AVTBVS Membership",
  organisation: {
    full_name: "Ayira Vaisyar Telugu Beri Vysya Sabha",
    abbreviation: "AVTBVS",
    telugu_name: "ఆయిర వైశ్యర్ తెలుగు బేరి వైశ్య సభ",
    formerly_known_as: "Telugu Beri Vysya Kulabhimana Sabha",
    registration: "Regd. No. 101/1955",
    address: "28, (Old No. 4), Kalappachari Street, Park Town, Chennai - 600 003",
    phone: "044-25330821",
    email: "avtbvsabha.1955@gmail.com",
    community_name: "Ayira Vaisyar Telugu Beri Vysya Chetty Community",
  },
  form: {
    blood_groups: ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"],
    minimum_age_years: 18,
    require_introducer_signature: false,
    max_photo_mb: 2,
    max_document_mb: 5,
    edit_permission_hours: 24,
  },
  active_member_count: 0,
};

export function usePublicConfig(): PublicConfig {
  const [config, setConfig] = useState<PublicConfig>(cache ?? FALLBACK_CONFIG);
  useEffect(() => {
    if (cache) return;
    pending = pending ?? api.get<PublicConfig>("/public/config").then((r) => (cache = r.data));
    pending.then(setConfig).catch(() => undefined);
  }, []);
  return config;
}
