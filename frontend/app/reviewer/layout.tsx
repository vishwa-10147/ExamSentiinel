import Sidebar from "@/components/Sidebar";

export default function ReviewerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-50 dark:bg-slate-900 overflow-hidden">
      <Sidebar />
      <div className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
