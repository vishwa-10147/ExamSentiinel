import re

filepath = 'frontend/app/admin/questions/page.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if 'const fileInputRef' not in content:
    # Add imports
    content = content.replace('import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart } from "lucide-react";', 'import { Plus, Library, Trash2, Edit, AlertCircle, Type, BarChart, Upload } from "lucide-react";\nimport { useRef } from "react";\nimport toast from "react-hot-toast";')
    
    # Add state and ref
    state_hook = '''
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
      const res = await fetch(${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/questions/bulk, {
        method: "POST",
        headers: { "Authorization": Bearer  },
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
      console.error(err);
      toast.error("Error uploading CSV.");
    } finally {
      setIsUploadingCSV(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };
'''
    content = content.replace('const [isSubmitting, setIsSubmitting] = useState(false);', 'const [isSubmitting, setIsSubmitting] = useState(false);' + state_hook)
    
    # Add button
    buttons = '''
            <div className="flex items-center gap-3">
              <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleFileUpload} />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingCSV}
                className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                {isUploadingCSV ? "Importing..." : "Import CSV"}
              </button>
              <button
                onClick={() => setIsModalOpen(true)}
'''
    content = content.replace('<button\n              onClick={() => setIsModalOpen(true)}', buttons)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated questions UI")
