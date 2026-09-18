import asyncio
import os
import sys

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.plagiarism_service import plagiarism_service

async def test_plagiarism_engine():
    print("[RUN] Automatically testing the Plagiarism Engine...")

    # Simulated submissions fetched from the database
    submissions = [
        {
            "id": "sub_1",
            "student_name": "Alice Johnson",
            "code": """
def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
            """
        },
        {
            "id": "sub_2",
            "student_name": "Bob Smith",
            "code": """
# Bob's copied solution
def fib(num):
    # Base cases
    if num <= 0:
        return 0
    elif num == 1:
        return 1
    # Recursive step
    else:
        return fib(num-1) + fib(num-2)
            """
        },
        {
            "id": "sub_3",
            "student_name": "Charlie Davis",
            "code": """
def fib_iterative(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
            """
        }
    ]

    print("\n[COMPARE] Comparing Submissions:")
    print("1. Alice (Recursive)")
    print("2. Bob (Recursive, but renamed variables and added comments)")
    print("3. Charlie (Iterative)")

    print("\n[TEST] Running Code Similarity Engine...")
    results = plagiarism_service.run_batch_comparison(submissions, threshold=0.70)

    print("\n[FLAG] PLAGIARISM FLAGS DETECTED [FLAG]")
    if not results:
        print("No plagiarism detected.")
    
    for r in results:
        print(f"Match: {r.student_a_name} <-> {r.student_b_name} | Similarity: {r.similarity_score * 100:.2f}%")

if __name__ == "__main__":
    asyncio.run(test_plagiarism_engine())
