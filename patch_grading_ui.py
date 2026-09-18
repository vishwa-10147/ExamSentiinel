import sys
import re

with open(r'frontend\app\admin\exam\[id]\grading\page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Add autoGrade function
auto_grade_func = '''  const autoGrade = async (responseId: string) => {
    try {
      const toastId = toast.loading("AI is analyzing the answer...");
      const res = await apiClient.post(`/api/reports/autograde/${responseId}`, {});
      toast.dismiss(toastId);
      
      const form = document.getElementById(`form-${responseId}`) as HTMLFormElement;
      if (form) {
        const marksInput = form.elements.namedItem("marks") as HTMLInputElement;
        if (marksInput) marksInput.value = res.suggested_marks;
        toast.success("AI suggested " + res.suggested_marks + " points!\\n" + res.feedback, { duration: 5000 });
      }
    } catch (err) {
      toast.error("AI Grading failed.");
    }
  };'''

text = text.replace('  if (loading)', auto_grade_func + '\n\n  if (loading)')

# Add button
btn = '''
                            <button 
                              type="button"
                              onClick={() => autoGrade(r.response_id)}
                              className="px-3 py-1 bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-400 hover:to-indigo-400 text-white text-xs font-bold rounded shadow-sm transition-all flex items-center gap-1"
                            >
                              ✨ Auto-Grade
                            </button>
'''

text = text.replace(
    '<div className="flex flex-col items-end gap-2 shrink-0">',
    '<div className="flex flex-col items-end gap-2 shrink-0">' + btn
)

# Add form ID
text = text.replace(
    '<form \n                            onSubmit=',
    '<form \n                            id={`form-${r.response_id}`}\n                            onSubmit='
)

with open(r'frontend\app\admin\exam\[id]\grading\page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
