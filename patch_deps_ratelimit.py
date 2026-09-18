import re

with open(r'backend\app\api\deps.py', 'r') as f:
    text = f.read()

# Find the block from "async with redis_client.pipeline" to "detail="Too Many Requests"\n            )"
# and wrap it in a try...except.
match = re.search(r'(async with redis_client\.pipeline.*?raise HTTPException.*?\n            \))', text, re.DOTALL)
if match:
    block = match.group(1)
    
    # indented block
    indented = "\n".join(["    " + line if line.strip() else line for line in block.split("\n")])
    
    new_block = f'''try:
{indented}
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            logger.debug(f"Redis rate limiter failed, bypassing: {{e}}")'''

    text = text.replace(block, new_block)
    with open(r'backend\app\api\deps.py', 'w') as f:
        f.write(text)
    print("Patched!")
else:
    print("Match not found!")
