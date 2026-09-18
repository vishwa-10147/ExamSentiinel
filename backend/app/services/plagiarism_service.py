import difflib
import re
from typing import Dict, List, Tuple
from pydantic import BaseModel

class SimilarityResult(BaseModel):
    submission_id_a: str
    submission_id_b: str
    student_a_name: str
    student_b_name: str
    similarity_score: float  # 0.0 to 1.0

class PlagiarismService:
    def __init__(self):
        pass

    def _normalize_code(self, code: str) -> str:
        """
        Normalizes code for similarity comparison by stripping comments and standardizing whitespace.
        This makes the comparison robust against basic cheating techniques like adding spaces or comments.
        """
        if not code:
            return ""
            
        # Remove single-line comments (Python/Ruby/Shell)
        code = re.sub(r'#.*', '', code)
        # Remove single-line comments (C/C++/Java/JS/Go/Rust)
        code = re.sub(r'//.*', '', code)
        # Remove multi-line comments (C-style)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # Remove multi-line strings/comments (Python)
        code = re.sub(r'\"\"\"(.*?)\"\"\"', '', code, flags=re.DOTALL)
        code = re.sub(r"\'\'\'(.*?)\'\'\'", '', code, flags=re.DOTALL)
        
        # Normalize whitespace (convert all whitespace sequences to a single space)
        code = re.sub(r'\s+', ' ', code)
        return code.strip()

    def calculate_similarity(self, code1: str, code2: str) -> float:
        """
        Calculates similarity ratio between two normalized code snippets using Ratcliff-Obershelp algorithm.
        """
        norm1 = self._normalize_code(code1)
        norm2 = self._normalize_code(code2)
        
        if not norm1 or not norm2:
            return 0.0
            
        # Using SequenceMatcher which provides a robust ratio of matching sequences
        matcher = difflib.SequenceMatcher(None, norm1, norm2)
        return matcher.ratio()

    def run_batch_comparison(
        self, 
        submissions: List[Dict[str, str]], 
        threshold: float = 0.75
    ) -> List[SimilarityResult]:
        """
        Compares a list of submissions against each other.
        submissions format: [{"id": "uuid", "student_name": "John Doe", "code": "print('hello')"}]
        Returns pairs that exceed the similarity threshold.
        """
        results = []
        n = len(submissions)
        
        for i in range(n):
            for j in range(i + 1, n):
                sub_a = submissions[i]
                sub_b = submissions[j]
                
                score = self.calculate_similarity(sub_a.get("code", ""), sub_b.get("code", ""))
                
                if score >= threshold:
                    results.append(SimilarityResult(
                        submission_id_a=sub_a["id"],
                        submission_id_b=sub_b["id"],
                        student_a_name=sub_a["student_name"],
                        student_b_name=sub_b["student_name"],
                        similarity_score=score
                    ))
                    
        # Sort by highest similarity first
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results

plagiarism_service = PlagiarismService()
