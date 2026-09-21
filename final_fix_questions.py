with open('frontend/app/admin/questions/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('  return (\n    <div className="flex-1 flex flex-col overflow-y-auto">', '  return (\n    <div className="flex-1 w-full">\n    <main className="flex-1 flex flex-col overflow-y-auto">')
text = text.replace('      </main>\n\n      {/* Create Question Modal */}', '      </main>\n\n      {/* Create Question Modal */}')

# Now what? We need to make sure the end has two </div> tags!
# Wait! In the current file, we have:
#       </main>
#       {/* Modal */}
#       {isModalOpen && ( ... )}
#     </div>
#   );
# }

# Let's just fix it perfectly.
text = text.replace('  return (\n    <div className="flex-1 flex flex-col overflow-y-auto">', '  return (\n    <div className="flex-1 w-full">\n      <main className="flex-1 flex flex-col overflow-y-auto">')

with open('frontend/app/admin/questions/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
