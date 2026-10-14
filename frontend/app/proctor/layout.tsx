import RoleAreaLayout from "@/components/RoleAreaLayout";

// Live proctoring.
const ROLES = ["admin", "proctor"];

export default function ProctorLayout({ children }: { children: React.ReactNode }) {
  return <RoleAreaLayout roles={ROLES}>{children}</RoleAreaLayout>;
}
