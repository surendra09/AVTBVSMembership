import { z } from "zod";

/** Client-side validation mirrors the FastAPI rules (the server re-validates everything). */
export const phoneSchema = z.string().trim().transform((v) => v.replace(/[\s\-()]/g, ""))
  .refine((v) => /^\+?[0-9]{7,15}$/.test(v), "Enter a valid mobile number");

export const optionalPhone = z.string().trim().transform((v) => v.replace(/[\s\-()]/g, ""))
  .refine((v) => v === "" || /^\+?[0-9]{7,15}$/.test(v), "Enter a valid phone number");

export const passwordSchema = z.string()
  .min(10, "Use at least 10 characters")
  .max(128, "Use at most 128 characters")
  .refine((v) => /[A-Za-z]/.test(v), "Include at least one letter")
  .refine((v) => /[0-9]/.test(v), "Include at least one number");

const D = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],
  [5,9,8,7,6,0,4,3,2,1],[6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]];
const P = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],
  [4,2,8,6,5,7,3,9,0,1],[2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]];

export function isValidAadhaar(raw: string): boolean {
  const v = raw.replace(/[\s-]/g, "");
  if (!/^[2-9][0-9]{11}$/.test(v)) return false;
  let c = 0;
  v.split("").reverse().forEach((ch, i) => { c = D[c][P[i % 8][Number(ch)]]; });
  return c === 0;
}

export function ageOn(dob: string, today = new Date()): number {
  const d = new Date(dob);
  let age = today.getFullYear() - d.getFullYear();
  const m = today.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age--;
  return age;
}

export const isValidPincode = (pin: string, country: string) =>
  (country || "India").trim().toLowerCase() === "india" ? /^[1-9][0-9]{5}$/.test(pin) : /^[A-Za-z0-9 -]{3,10}$/.test(pin);
