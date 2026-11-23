export type Role = "USER" | "ADMIN" | "SUPER_ADMIN";
export type ApplicationStatus = "DRAFT" | "PENDING" | "CORRECTION_REQUIRED" | "RESUBMITTED" | "APPROVED" | "REJECTED";
export type MembershipStatus = "ACTIVE" | "INACTIVE";
export type MemberSource = "ONLINE_APPLICATION" | "MANUAL_ENTRY";
export type EditRequestStatus = "PENDING" | "APPROVED" | "REJECTED";
export type DocumentType =
  | "PHOTO"
  | "ID_PROOF"
  | "ADDITIONAL_PHOTO_1"
  | "ADDITIONAL_PHOTO_2"
  | "INTRODUCER_SIGNATURE"
  | "APPLICANT_SIGNATURE";

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  role: Role;
  is_active: boolean;
  email_verified: boolean;
  phone_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface MembershipSummary {
  is_member: boolean;
  member_id: number | null;
  membership_number: string | null;
  membership_status: MembershipStatus | null;
  application_id: number | null;
  application_status: ApplicationStatus | null;
  edit_permission_expires_at: string | null;
}

export interface Me {
  user: User;
  membership: MembershipSummary;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DocumentItem {
  id: number;
  doc_type: DocumentType;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  url: string;
}

export interface HistoryItem {
  id: number;
  action: string;
  from_status: string | null;
  to_status: string | null;
  note: string | null;
  actor_name: string | null;
  created_at: string;
}

export interface FormData {
  full_name: string | null;
  father_name: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  pincode: string | null;
  aadhaar_masked: string | null;
  blood_group: string | null;
  date_of_birth: string | null;
  phone: string | null;
  centre_x_no: string | null;
  cell: string | null;
  email: string | null;
  whatsapp_facebook: string | null;
  family_surname: string | null;
  gothram: string | null;
  natchathiram: string | null;
  occupation: string | null;
  occupation_address: string | null;
  native_place_address: string | null;
  introducer_name: string | null;
  introducer_phone: string | null;
  introducer_reg_no: string | null;
  show_contact_in_directory: boolean;
  show_address_in_directory: boolean;
}

export interface Application extends FormData {
  id: number;
  application_number: string;
  status: ApplicationStatus;
  declaration_accepted: boolean;
  declaration_place: string | null;
  declaration_date: string | null;
  correction_notes: string | null;
  rejection_reason: string | null;
  submitted_at: string | null;
  last_submitted_at: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  can_edit: boolean;
  documents: DocumentItem[];
  history: HistoryItem[];
  membership_number: string | null;
}

export interface IntroducerCheck {
  registration_number_found: boolean;
  member_name: string | null;
  member_status: MembershipStatus | null;
  phone_matches: boolean | null;
}

export interface AdminApplication extends Application {
  aadhaar_number: string | null;
  applicant_user_id: number;
  applicant_account_name: string;
  applicant_account_email: string;
  applicant_account_phone: string;
  reviewed_by_name: string | null;
  introducer_check: IntroducerCheck;
  age_years: number | null;
  duplicate_aadhaar_member_numbers: string[];
  member_id: number | null;
}

export interface ApplicationListItem {
  id: number;
  application_number: string;
  full_name: string | null;
  father_name: string | null;
  city: string | null;
  cell: string | null;
  introducer_reg_no: string | null;
  status: ApplicationStatus;
  submitted_at: string | null;
  last_submitted_at: string | null;
  updated_at: string;
  photo_url: string | null;
}

export interface PublicMember {
  id: number;
  full_name: string;
  father_name: string;
}

export interface DirectoryMember {
  id: number;
  membership_number: string;
  full_name: string;
  father_name: string;
  photo_url: string | null;
  city: string;
  state: string;
  country: string;
  blood_group: string | null;
  family_surname: string | null;
  gothram: string | null;
  natchathiram: string | null;
  occupation: string | null;
  native_place_address: string | null;
  enrolled_at: string;
  cell: string | null;
  phone: string | null;
  email: string | null;
  whatsapp_facebook: string | null;
  address_line1: string | null;
  address_line2: string | null;
  pincode: string | null;
  occupation_address: string | null;
}

export interface OfficeUse {
  verified_by: string | null;
  receipt_number: string | null;
  receipt_date: string | null;
  committee_chairman: string | null;
  committee_secretary: string | null;
  committee_president: string | null;
  office_notes: string | null;
}

export interface MyMembership extends FormData {
  member_id: number;
  membership_number: string;
  status: MembershipStatus;
  source: MemberSource;
  enrolled_at: string;
  declaration_place: string | null;
  declaration_date: string | null;
  photo_url: string | null;
  documents: DocumentItem[];
  edit_permission_expires_at: string | null;
  edit_permission_active: boolean;
  pending_edit_request: boolean;
}

export interface ChangeEntry {
  id: number;
  field: string;
  old: string | null;
  new: string | null;
  source: string;
  changed_by: string | null;
  at: string;
}

export interface AdminMember extends FormData, OfficeUse {
  member_id: number;
  member_profile_id: number;
  membership_number: string;
  status: MembershipStatus;
  source: MemberSource;
  enrolled_at: string;
  aadhaar_number: string | null;
  declaration_place: string | null;
  declaration_date: string | null;
  application_id: number | null;
  application_number: string | null;
  linked_user_id: number | null;
  linked_user_email: string | null;
  approved_by_name: string | null;
  deactivated_at: string | null;
  deactivation_reason: string | null;
  photo_url: string | null;
  documents: DocumentItem[];
  change_history: ChangeEntry[];
  edit_permission_expires_at: string | null;
}

export interface AdminMemberListItem {
  id: number;
  membership_number: string;
  full_name: string;
  father_name: string;
  city: string;
  cell: string;
  status: MembershipStatus;
  source: MemberSource;
  enrolled_at: string;
  has_account: boolean;
  photo_url: string | null;
}

export interface EditRequest {
  id: number;
  member_id: number;
  membership_number: string;
  member_name: string;
  reason: string;
  status: EditRequestStatus;
  created_at: string;
  reviewed_at: string | null;
  reviewed_by_name: string | null;
  review_note: string | null;
  permission_starts_at: string | null;
  permission_expires_at: string | null;
  permission_active: boolean;
}

export interface NotificationItem {
  id: number;
  event: string;
  title: string;
  message: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface PublicConfig {
  app_name: string;
  organisation: {
    full_name: string;
    abbreviation: string;
    telugu_name: string;
    formerly_known_as: string;
    registration: string;
    address: string;
    phone: string;
    email: string;
    community_name: string;
  };
  form: {
    blood_groups: string[];
    minimum_age_years: number;
    require_introducer_signature: boolean;
    max_photo_mb: number;
    max_document_mb: number;
    edit_permission_hours: number;
  };
  active_member_count: number;
}

export interface AdminAccount extends User {
  created_by_name: string | null;
  membership_number: string | null;
}
