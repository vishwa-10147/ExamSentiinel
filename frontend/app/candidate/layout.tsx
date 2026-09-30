import Sidebar from "@/components/Sidebar";

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-50 dark:bg-slate-900 overflow-hidden">
      <Sidebar />
      <div className="flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
