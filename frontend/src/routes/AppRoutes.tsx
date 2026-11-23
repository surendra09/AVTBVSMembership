import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import {
  Activity, BarChart3, Bell, ClipboardEdit, FileText, FolderCheck, FolderX, Home, IdCard, Inbox, LayoutDashboard,
  ListChecks, Settings, ShieldCheck, User, UserPlus, Users,
} from "lucide-react";
import { Loading } from "@/components/ui/Feedback";
import { homePathFor, isAdmin, useAuth } from "@/features/auth/AuthContext";
import { DashboardLayout, type NavGroup } from "@/layouts/DashboardLayout";
import { PublicLayout } from "@/layouts/PublicLayout";
import AddMemberPage from "@/pages/admin/AddMemberPage";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import AdminNotificationsPage from "@/pages/admin/AdminNotificationsPage";
import ApplicationReviewPage from "@/pages/admin/ApplicationReviewPage";
import ApplicationsPage from "@/pages/admin/ApplicationsPage";
import EditRequestsPage from "@/pages/admin/EditRequestsPage";
import MemberDetailPage from "@/pages/admin/MemberDetailPage";
import MembersPage from "@/pages/admin/MembersPage";
import ReportsPage from "@/pages/admin/ReportsPage";
import { ForgotPasswordPage, LoginPage, NotFoundPage, RegisterPage, ResetPasswordPage } from "@/pages/public/AuthPages";
import BeriChettyOverviewPage from "@/pages/public/BeriChettyOverviewPage";
import DirectoryPage from "@/pages/public/DirectoryPage";
import HomePage from "@/pages/public/HomePage";
import AccountPage from "@/pages/shared/AccountPage";
import NotificationsPage from "@/pages/shared/NotificationsPage";
import { AdminPrintPage, MyPrintPage } from "@/pages/shared/PrintPages";
import { AdminManagementPage, AuditLogPage, SuperAdminDashboard, SystemSettingsPage } from "@/pages/super-admin/SuperAdminPages";
import ApplicationPage from "@/pages/user/ApplicationPage";
import MemberDirectoryPage, { MemberProfilePage } from "@/pages/user/MemberDirectoryPage";
import MemberEditPage from "@/pages/user/MemberEditPage";
import MyMembershipPage from "@/pages/user/MyMembershipPage";
import UserDashboard from "@/pages/user/UserDashboard";
import type { Role } from "@/types";

function RequireAuth({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { me, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Loading label="Checking your session" />;
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  // UI guard only – every API endpoint enforces the same rules on the server.
  if (roles && !roles.includes(me.user.role)) return <Navigate to={homePathFor(me)} replace />;
  return <>{children}</>;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  return me ? <Navigate to={homePathFor(me)} replace /> : <>{children}</>;
}

function UserArea() {
  const { me } = useAuth();
  const member = me?.membership.is_member;
  const groups: NavGroup[] = member ? [{
    items: [
      { to: "/dashboard", label: "Dashboard", icon: Home, end: true },
      { to: "/dashboard/membership", label: "My membership", icon: IdCard, end: true },
      { to: "/dashboard/directory", label: "Member directory", icon: Users },
      { to: "/dashboard/membership/edit", label: "Edit my details", icon: ClipboardEdit },
      { to: "/dashboard/notifications", label: "Notifications", icon: Bell },
      { to: "/dashboard/account", label: "My account", icon: User },
    ],
  }] : [{
    items: [
      { to: "/dashboard", label: "Dashboard", icon: Home, end: true },
      { to: "/dashboard/application", label: me?.membership.application_status && me.membership.application_status !== "DRAFT" ? "Application status" : "Membership application", icon: FileText },
      { to: "/dashboard/directory", label: "Member directory", icon: Users },
      { to: "/dashboard/notifications", label: "Notifications", icon: Bell },
      { to: "/dashboard/account", label: "My account", icon: User },
    ],
  }];
  return <DashboardLayout groups={groups} notificationsHref="/dashboard/notifications" homeHref="/dashboard" />;
}

const ADMIN_GROUPS: NavGroup[] = [
  { items: [{ to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true }] },
  {
    title: "Applications",
    items: [
      { to: "/admin/applications", label: "All applications", icon: Inbox, end: true },
      { to: "/admin/applications/pending", label: "Pending", icon: ListChecks },
      { to: "/admin/applications/corrections", label: "Correction requests", icon: ClipboardEdit },
      { to: "/admin/applications/approved", label: "Approved", icon: FolderCheck },
      { to: "/admin/applications/rejected", label: "Rejected", icon: FolderX },
    ],
  },
  {
    title: "Members",
    items: [
      { to: "/admin/members", label: "All members", icon: Users, end: true },
      { to: "/admin/members/new", label: "Add existing member", icon: UserPlus },
      { to: "/admin/edit-requests", label: "Profile edit requests", icon: ClipboardEdit },
    ],
  },
  {
    title: "Office",
    items: [
      { to: "/admin/notifications", label: "Notifications", icon: Bell },
      { to: "/admin/reports", label: "Reports", icon: BarChart3 },
      { to: "/admin/account", label: "My profile", icon: User },
    ],
  },
];

const SUPER_GROUP: NavGroup = {
  title: "Super Admin",
  items: [
    { to: "/super-admin", label: "Super Admin dashboard", icon: ShieldCheck, end: true },
    { to: "/super-admin/admins", label: "Admin management", icon: Users, end: true },
    { to: "/super-admin/admins/new", label: "Create admin", icon: UserPlus },
    { to: "/super-admin/activity", label: "Admin activity logs", icon: Activity },
    { to: "/super-admin/settings", label: "System settings", icon: Settings },
  ],
};

function AdminArea() {
  const { me } = useAuth();
  const groups = me?.user.role === "SUPER_ADMIN" ? [SUPER_GROUP, ...ADMIN_GROUPS] : ADMIN_GROUPS;
  return <DashboardLayout groups={groups} notificationsHref="/admin/notifications" homeHref={me?.user.role === "SUPER_ADMIN" ? "/super-admin" : "/admin"} />;
}

function DashboardIndexRedirect() {
  const { me } = useAuth();
  if (me && isAdmin(me)) return <Navigate to={homePathFor(me)} replace />;
  return <UserDashboard />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<HomePage />} />
        <Route path="beri-chetty-overview" element={<BeriChettyOverviewPage />} />
        <Route path="directory" element={<DirectoryPage />} />
        <Route path="login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route path="dashboard" element={<RequireAuth><UserArea /></RequireAuth>}>
        <Route index element={<DashboardIndexRedirect />} />
        <Route path="application" element={<RequireAuth roles={["USER"]}><ApplicationPage /></RequireAuth>} />
        <Route path="membership" element={<MyMembershipPage />} />
        <Route path="membership/edit" element={<MemberEditPage />} />
        <Route path="membership/print" element={<MyPrintPage />} />
        <Route path="directory" element={<MemberDirectoryPage />} />
        <Route path="directory/:id" element={<MemberProfilePage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="account" element={<AccountPage />} />
      </Route>

      <Route path="admin" element={<RequireAuth roles={["ADMIN", "SUPER_ADMIN"]}><AdminArea /></RequireAuth>}>
        <Route index element={<AdminDashboard />} />
        <Route path="applications" element={<ApplicationsPage />} />
        <Route path="applications/:id" element={<ReviewOrList />} />
        <Route path="members" element={<MembersPage />} />
        <Route path="members/new" element={<AddMemberPage />} />
        <Route path="members/:id" element={<MemberDetailPage />} />
        <Route path="members/:id/print" element={<AdminPrintPage />} />
        <Route path="edit-requests" element={<EditRequestsPage />} />
        <Route path="notifications" element={<AdminNotificationsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="account" element={<AccountPage />} />
      </Route>

      <Route path="super-admin" element={<RequireAuth roles={["SUPER_ADMIN"]}><AdminArea /></RequireAuth>}>
        <Route index element={<SuperAdminDashboard />} />
        <Route path="admins" element={<AdminManagementPage />} />
        <Route path="admins/new" element={<AdminManagementPage startCreate key="create" />} />
        <Route path="activity" element={<AuditLogPage />} />
        <Route path="settings" element={<SystemSettingsPage />} />
      </Route>
    </Routes>
  );
}

/** /admin/applications/:id is either a status view (pending, corrections, …) or an application id. */
function ReviewOrList() {
  const location = useLocation();
  const last = location.pathname.split("/").pop() ?? "";
  return /^\d+$/.test(last) ? <ApplicationReviewPage /> : <ApplicationsPage />;
}
