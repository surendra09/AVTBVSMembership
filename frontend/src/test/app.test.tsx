import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { submissionSchema, toFormValues, toPayload } from "@/features/registration/formModel";
import { ageOn, isValidAadhaar, isValidPincode } from "@/utils/validation";
import { timeRemaining } from "@/utils/format";

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() } };
});
import { api } from "@/services/api";
import { PublicDirectoryList } from "@/features/members/PublicDirectoryList";
import { FileUpload } from "@/components/FileUpload";

const validForm = () => ({
  ...toFormValues({}),
  full_name: "Ramesh Kumar", father_name: "Venkata Rao", address_line1: "12 Main St", city: "Chennai", state: "Tamil Nadu",
  country: "India", pincode: "600003", date_of_birth: "1980-01-01", cell: "9876543210",
  introducer_name: "Sri Subramanyam", introducer_phone: "9840012345", introducer_reg_no: "1001",
  declaration_accepted: true, declaration_place: "Chennai",
});

describe("validation helpers", () => {
  it("validates Aadhaar with the Verhoeff checksum", () => {
    expect(isValidAadhaar("234567890124")).toBe(isValidAadhaar("2345 6789 0124"));
    expect(isValidAadhaar("123456789012")).toBe(false);
    expect(isValidAadhaar("2345")).toBe(false);
  });
  it("validates Indian pincodes", () => {
    expect(isValidPincode("600003", "India")).toBe(true);
    expect(isValidPincode("060003", "India")).toBe(false);
    expect(isValidPincode("SW1A 1AA", "United Kingdom")).toBe(true);
  });
  it("computes age", () => {
    expect(ageOn("2000-06-15", new Date("2018-06-14"))).toBe(17);
    expect(ageOn("2000-06-15", new Date("2018-06-15"))).toBe(18);
  });
  it("formats remaining edit time", () => {
    const now = Date.now();
    expect(timeRemaining(new Date(now + 90 * 60_000).toISOString(), now)).toBe("1 h 30 min left");
    expect(timeRemaining(new Date(now - 1000).toISOString(), now)).toBe("expired");
  });
});

describe("membership form rules", () => {
  it("accepts a complete application", () => {
    expect(submissionSchema().safeParse(validForm()).success).toBe(true);
  });
  it.each(["introducer_name", "introducer_phone", "introducer_reg_no"])("requires %s", (field) => {
    const r = submissionSchema().safeParse({ ...validForm(), [field]: "" });
    expect(r.success).toBe(false);
    expect(r.error!.issues.some((i) => i.path[0] === field && /mandatory/.test(i.message))).toBe(true);
  });
  it("requires the declaration", () => {
    const r = submissionSchema().safeParse({ ...validForm(), declaration_accepted: false });
    expect(r.success).toBe(false);
  });
  it("rejects applicants under 18", () => {
    const young = new Date();
    young.setFullYear(young.getFullYear() - 17);
    const r = submissionSchema().safeParse({ ...validForm(), date_of_birth: young.toISOString().slice(0, 10) });
    expect(r.error!.issues[0].message).toMatch(/18 years/);
  });
  it("builds a payload: blanks become null and a blank Aadhaar is omitted", () => {
    const p = toPayload({ ...validForm(), address_line2: "  ", aadhaar_number: "" });
    expect(p.address_line2).toBeNull();
    expect("aadhaar_number" in p).toBe(false);
    expect(p.declaration_accepted).toBe(true);
  });
  it("can omit introducer fields for member self-edit", () => {
    const p = toPayload(validForm(), { includeIntroducer: false, includeDeclaration: false });
    expect(Object.keys(p).some((k) => k.startsWith("introducer_") || k.startsWith("declaration_"))).toBe(false);
  });
});

describe("public directory", () => {
  beforeEach(() => vi.mocked(api.get).mockReset());
  it("renders only names and fathers' names from the public endpoint", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [{ id: 1, full_name: "Lakshmi Devi", father_name: "Ranga Rao" }], total: 1, page: 1, page_size: 20, pages: 1 } });
    render(<MemoryRouter><PublicDirectoryList /></MemoryRouter>);
    expect(await screen.findByText("Lakshmi Devi")).toBeInTheDocument();
    expect(screen.getByText("Ranga Rao")).toBeInTheDocument();
    expect(vi.mocked(api.get).mock.calls[0][0]).toBe("/members/public");
    expect(screen.queryByRole("img")).toBeNull();
  });
  it("shows an empty state for no matches", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 20, pages: 1 } });
    render(<MemoryRouter><PublicDirectoryList /></MemoryRouter>);
    expect(await screen.findByText(/register is empty/i)).toBeInTheDocument();
  });
});

describe("file upload", () => {
  it("rejects wrong file types before uploading", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<FileUpload docType="PHOTO" uploadUrl="/x" accept="image" maxMb={2} onUploaded={() => undefined} />);
    const input = screen.getByLabelText(/Upload Recent passport-size photograph/);
    await user.upload(input, new File(["%PDF"], "doc.pdf", { type: "application/pdf" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/JPG, JPEG, PNG/));
    expect(api.post).not.toHaveBeenCalled();
  });
});
