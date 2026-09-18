import sys

with open(r'frontend\app\admin\exam\[id]\manage\page.tsx', 'r') as f:
    text = f.read()

import_ai = 'import AIGenerateModal from "./AIGenerateModal";'
text = text.replace('import CreateQuestionModal from "./CreateQuestionModal";', 'import CreateQuestionModal from "./CreateQuestionModal";\n' + import_ai)
text = text.replace('const [showCreateModal, setShowCreateModal] = useState(false);', 'const [showCreateModal, setShowCreateModal] = useState(false);\n  const [showAIModal, setShowAIModal] = useState(false);')

old_buttons = '''                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 active:bg-blue-200 active:scale-95 px-3 py-1.5 rounded-lg transition cursor-pointer"
                  >
                    <Plus className="w-4 h-4" /> Add Question
                  </button>'''

new_buttons = '''                  <button
                    onClick={() => setShowAIModal(true)}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 active:bg-indigo-200 active:scale-95 px-3 py-1.5 rounded-lg transition cursor-pointer"
                  >
                    <Sparkles className="w-4 h-4" /> Generate AI
                  </button>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 active:bg-blue-200 active:scale-95 px-3 py-1.5 rounded-lg transition cursor-pointer"
                  >
                    <Plus className="w-4 h-4" /> Add Question
                  </button>'''

text = text.replace(old_buttons, new_buttons)

old_modals = '''      {showCreateModal && (
        <CreateQuestionModal'''

new_modals = '''      {showAIModal && (
        <AIGenerateModal
          examId={examId}
          onClose={() => setShowAIModal(false)}
          onSuccess={(count) => {
            setShowAIModal(false);
            showToast(`Successfully generated ${count} AI questions!`, "success");
            fetchExam();
          }}
        />
      )}
      
      {showCreateModal && (
        <CreateQuestionModal'''

text = text.replace(old_modals, new_modals)

if 'Sparkles' not in text:
    text = text.replace('CheckCircle2,', 'CheckCircle2,\n  Sparkles,')

with open(r'frontend\app\admin\exam\[id]\manage\page.tsx', 'w') as f:
    f.write(text)
