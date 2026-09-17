"""
MOSS Winnowing Code Plagiarism Detector.

Uses the Winnowing algorithm (Schleimer, Wilkerson, Aiken) to generate 
document fingerprints and compute similarity scores between student code submissions.
"""

import hashlib
import re
from collections import defaultdict
from typing import List, Set, Tuple

K_GRAM_SIZE = 15
WINDOW_SIZE = 4

class CodeIntegrityEngine:
    def __init__(self):
        # In a real environment, this would connect to a vector DB 
        # or graph DB of all historical student submissions.
        self.corpus_fingerprints = defaultdict(set)

    def sanitize_code(self, code: str) -> str:
        """Removes whitespace and comments to normalize code structure."""
        # Remove single line comments
        code = re.sub(r'//.*|#.*', '', code)
        # Remove multi-line comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'\'\'\'.*?\'\'\'', '', code, flags=re.DOTALL)
        code = re.sub(r'\"\"\".*?\"\"\"', '', code, flags=re.DOTALL)
        # Remove all whitespace
        return re.sub(r'\s+', '', code.lower())

    def get_kgrams(self, text: str) -> List[str]:
        """Generates k-grams of size K_GRAM_SIZE from text."""
        return [text[i:i+K_GRAM_SIZE] for i in range(len(text) - K_GRAM_SIZE + 1)]

    def hash_kgram(self, kgram: str) -> int:
        """Hashes a k-gram into a deterministic integer."""
        return int(hashlib.md5(kgram.encode('utf-8')).hexdigest()[:8], 16)

    def generate_fingerprint(self, code: str) -> Set[int]:
        """Runs the Winnowing algorithm to generate a minimal fingerprint subset."""
        sanitized = self.sanitize_code(code)
        if len(sanitized) < K_GRAM_SIZE:
            return set()

        kgrams = self.get_kgrams(sanitized)
        hashes = [self.hash_kgram(kg) for kg in kgrams]
        
        fingerprint = set()
        
        # Slide window across hashes to select minimum hash per window
        for i in range(len(hashes) - WINDOW_SIZE + 1):
            window = hashes[i:i+WINDOW_SIZE]
            # Get the minimum hash in the window. 
            # If there's a tie, pick the rightmost to ensure selection sparsity.
            min_hash = min(window)
            fingerprint.add(min_hash)
            
        return fingerprint

    def compute_similarity(self, code_a: str, code_b: str) -> float:
        """Computes Jaccard similarity between two code fingerprints."""
        fp_a = self.generate_fingerprint(code_a)
        fp_b = self.generate_fingerprint(code_b)
        
        if not fp_a or not fp_b:
            return 0.0
            
        intersection = fp_a.intersection(fp_b)
        union = fp_a.union(fp_b)
        
        return len(intersection) / len(union)

    def analyze_submission(self, student_id: str, exam_id: str, code: str) -> dict:
        """
        Main entry point for analyzing a live code submission.
        """
        fingerprint = self.generate_fingerprint(code)
        
        # 1. Compare against known external solutions (StackOverflow, Chegg dataset)
        external_sim = self.compute_similarity(code, "KNOWN_CHEATS_CORPUS_MOCK")
        
        # 2. Add to historical corpus (mocked)
        self.corpus_fingerprints[f"{exam_id}:{student_id}"] = fingerprint
        
        flags = []
        similarity_score = external_sim * 100
        
        if similarity_score > 60.0:
            flags.append("CODE_SIMILARITY_HIGH")
        elif similarity_score > 30.0:
            flags.append("CODE_SIMILARITY_MEDIUM")

        return {
            "similarity_score": round(similarity_score, 2),
            "flags": flags,
            "kgrams_matched": len(fingerprint) // 3  # simulated metrics
        }
