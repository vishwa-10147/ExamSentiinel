import RoleAreaLayout from "@/components/RoleAreaLayout";

// Staff area; reviewers use /admin/review.
const ROLES = ["admin", "proctor", "reviewer"];

export default function AdminAreaLayout({ children }: { children: React.ReactNode }) {
  return <RoleAreaLayout roles={ROLES}>{children}</RoleAreaLayout>;
}
