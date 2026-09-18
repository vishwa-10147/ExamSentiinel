import sys

with open(r'backend\app\services\grading_service.py', 'r') as f:
    lines = f.readlines()

new_lines = []
in_essay_block = False

for line in lines:
    if 'elif question.type == QuestionType.ESSAY:' in line:
        in_essay_block = True
        new_lines.append('            elif question.type == QuestionType.ESSAY:\n')
    elif 'elif question.type == QuestionType.CODING:' in line:
        in_essay_block = False
        new_lines.append(line)
    elif in_essay_block:
        # dedent by 12 spaces if it has at least 24 spaces
        if line.startswith(' ' * 24):
            new_lines.append(line[12:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(r'backend\app\services\grading_service.py', 'w') as f:
    f.writelines(new_lines)
