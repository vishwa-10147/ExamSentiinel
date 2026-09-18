import re
from typing import Dict, Optional, Tuple

class RollNumberParser:
    def __init__(self, regex_pattern: str, group_mapping: Dict[str, int]):
        """
        regex_pattern: The regex pattern to match roll numbers, e.g., r"^(\d{4})([A-Z]{2,3})(\d{3})$"
        group_mapping: Dictionary mapping semantic fields to regex groups.
                       e.g., {"year": 1, "department": 2, "id": 3}
        """
        self.pattern = re.compile(regex_pattern)
        self.mapping = group_mapping

    def parse(self, roll_number: str) -> Optional[Dict[str, str]]:
        """
        Parse a roll number and extract fields.
        Returns None if it doesn't match the pattern.
        """
        match = self.pattern.match(roll_number)
        if not match:
            return None
            
        result = {}
        for field, group_idx in self.mapping.items():
            try:
                result[field] = match.group(group_idx)
            except IndexError:
                result[field] = None
                
        return result
        
    def generate_batch_name(self, parsed_data: Dict[str, str]) -> str:
        """
        Generates a standard batch name from parsed data, e.g., "CS-2024"
        """
        dept = parsed_data.get("department", "GEN")
        year = parsed_data.get("year", "0000")
        return f"{dept}-{year}"

# Default Singleton if needed
default_parser = RollNumberParser(r"^(\d{4})([A-Z]{2,3})(\d{3})$", {"year": 1, "department": 2, "id": 3})
