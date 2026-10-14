import RoleAreaLayout from "@/components/RoleAreaLayout";

// Human review of flagged sessions.
const ROLES = ["admin", "reviewer"];

export default function ReviewerLayout({ children }: { children: React.ReactNode }) {
  return <RoleAreaLayout roles={ROLES}>{children}</RoleAreaLayout>;
}
