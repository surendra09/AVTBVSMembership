import { Alert } from "@/components/ui/Feedback";
import { ButtonLink } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/AuthContext";
import { PublicDirectoryList } from "@/features/members/PublicDirectoryList";

export default function DirectoryPage() {
  const { me } = useAuth();
  const fullAccess = me && (me.membership.is_member || me.user.role !== "USER");
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <h1>Member directory</h1>
      <p className="mb-6 mt-1 text-ink-soft">Search the Sabha's register by member name or father's name.</p>
      {fullAccess ? (
        <div className="mb-6">
          <Alert tone="info" title="You have full directory access"
            action={<ButtonLink size="sm" to={me!.user.role === "USER" ? "/dashboard/directory" : "/admin/members"}>Open full directory</ButtonLink>}>
            Photographs, contact details and family information are shown in your dashboard.
          </Alert>
        </div>
      ) : (
        <p className="mb-6 text-[15px] text-ink-muted">
          Contact details, photographs and family information are visible only to approved members after logging in.
        </p>
      )}
      <PublicDirectoryList pageSize={25} />
    </div>
  );
}
