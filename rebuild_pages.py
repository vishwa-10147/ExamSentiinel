import os
import re

# 9. Practice Page
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

# 10. Questions Page
with open("frontend/app/admin/questions/page.tsx", "r", encoding="utf-8") as f:
    ques = f.read()
ques = ques.replace('import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart } from "lucide-react";', 'import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart, Upload } from "lucide-react";\\nimport { useRef } from "react";\\nimport toast from "react-hot-toast";')
ques = ques.replace('const [isSubmitting, setIsSubmitting] = useState(false);', '''const [isSubmitting, setIsSubmitting] = useState(false);
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
buttons = '''
            <div className="flex items-center gap-3">
              <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
              <button onClick={() => fileInputRef.current?.click()} disabled={isUploadingCSV} className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
                <Upload className="h-4 w-4" /> {isUploadingCSV ? "Importing..." : "Import CSV"}
              </button>
              <button onClick={() => setIsModalOpen(true)}
'''
ques = ques.replace('<button\\n              onClick={() => setIsModalOpen(true)}', buttons)
with open("frontend/app/admin/questions/page.tsx", "w", encoding="utf-8") as f:
    f.write(ques)

print("Practice and Questions complete")
