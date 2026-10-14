import RoleAreaLayout from "@/components/RoleAreaLayout";

// Admins may open candidate pages to preview practice problems.
const ROLES = ["candidate", "admin"];

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return <RoleAreaLayout roles={ROLES}>{children}</RoleAreaLayout>;
}
