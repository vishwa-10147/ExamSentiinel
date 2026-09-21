import re

def modify_file(filepath, search, replace):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    if search in text:
        text = text.replace(search, replace)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Modified {filepath}")
    else:
        print(f"Could not find search in {filepath}")

modify_file('frontend/app/layout.tsx', 'import { AuthProvider } from "@/contexts/AuthContext";', 'import { AuthProvider } from "@/contexts/AuthContext";\nimport { SidebarProvider } from "@/contexts/SidebarContext";')
modify_file('frontend/app/layout.tsx', '<AuthProvider>', '<AuthProvider>\n          <SidebarProvider>')
modify_file('frontend/app/layout.tsx', '</AuthProvider>', '</SidebarProvider>\n        </AuthProvider>')

modify_file('frontend/components/Navbar.tsx', 'import { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth }')
modify_file('frontend/components/Navbar.tsx', 'AlertTriangle } from "lucide-react";', 'AlertTriangle, Menu } from "lucide-react";')
modify_file('frontend/components/Navbar.tsx', 'const { user, isAuthenticated, logout } = useAuth();', 'const { user, isAuthenticated, logout } = useAuth();\n  const { isSidebarOpen, toggleSidebar } = useSidebar();')
modify_file('frontend/components/Navbar.tsx', '<Link href="/" className="flex items-center gap-2">', '''<div className="flex items-center gap-4">
          {isAuthenticated && (
            <button onClick={toggleSidebar} className="p-2 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800 transition-colors" aria-label="Toggle Sidebar">
              <Menu className="h-6 w-6" />
            </button>
          )}
          <Link href="/" className="flex items-center gap-2">''')
modify_file('frontend/components/Navbar.tsx', '</Link>\n          </div>', '</Link>\n        </div>\n          </div>')

modify_file('frontend/components/Sidebar.tsx', 'import { useAuth }', 'import { useSidebar } from "@/contexts/SidebarContext";\nimport { useAuth }')
modify_file('frontend/components/Sidebar.tsx', 'const { user } = useAuth();', 'const { user } = useAuth();\n  const { isSidebarOpen } = useSidebar();')
modify_file('frontend/components/Sidebar.tsx', '<aside className="w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col min-h-[calc(100vh-4rem)]">', '<aside className={g-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col min-h-[calc(100vh-4rem)] transition-all duration-300 ease-in-out }>')
modify_file('frontend/components/Sidebar.tsx', '<nav className="flex-1 overflow-y-auto py-4">', '<nav className="flex-1 overflow-y-auto py-4 min-w-[16rem]">')

modify_file('frontend/app/admin/questions/page.tsx', 'import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart } from "lucide-react";', 'import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart, Upload } from "lucide-react";\nimport { useRef } from "react";\nimport toast from "react-hot-toast";')
modify_file('frontend/app/admin/questions/page.tsx', 'const [isSubmitting, setIsSubmitting] = useState(false);', '''const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploadingCSV, setIsUploadingCSV] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploadingCSV(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(\\/api/questions/bulk, {
        method: "POST",
        headers: { "Authorization": Bearer \\ },
        body: formData,
      });
      if (res.ok) {
        toast.success("Questions imported successfully!");
        const data = await apiClient.get("/api/questions");
        setQuestions(data);
      } else {
        toast.error("Failed to import CSV.");
      }
    } catch (err) {
      toast.error("Error uploading CSV.");
    } finally {
      setIsUploadingCSV(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };''')
modify_file('frontend/app/admin/questions/page.tsx', '<button\n              onClick={() => setIsModalOpen(true)}', '''<div className="flex items-center gap-3">
              <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
              <button onClick={() => fileInputRef.current?.click()} disabled={isUploadingCSV} className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                <Upload className="h-4 w-4" /> {isUploadingCSV ? "Importing..." : "Import CSV"}
              </button>
              <button onClick={() => setIsModalOpen(true)}''')

with open("frontend/app/candidate/practice/page.tsx", "r", encoding="utf-8") as f:
    prac = f.read()
prac = re.sub(r'const runCode = async \(\) => \{.*?\n  \};', '''const runCode = async () => {
    setIsRunning(true);
    setOutput(["Dispatching to execution cluster..."]);
    setActiveTab("console");
    try {
      const res = await fetch(\\/api/sandbox/execute, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: language, source_code: code, stdin: "", time_limit_sec: 5.0, memory_limit_mb: 256 })
      });
      const data = await res.json();
      if (res.ok) {
        setOutput(data.stdout ? data.stdout.split("\\n") : []);
        if (data.stderr) setOutput(prev => [...prev, ...data.stderr.split("\\n")]);
      } else {
        setOutput(["Execution failed.", JSON.stringify(data)]);
      }
    } catch (err) {
      setOutput(["Connection error. Please try again."]);
    } finally {
      setIsRunning(false);
    }
  };''', prac, flags=re.DOTALL)
with open("frontend/app/candidate/practice/page.tsx", "w", encoding="utf-8") as f:
    f.write(prac)
print("Modified practice")

