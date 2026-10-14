"""ExamSentinel practice problem bank. Import order is significant (shared RNG).

Every problem has a permanent ``number`` (its public ID) and ``slug``; never
renumber or rename an existing problem — append new ones instead.
"""

from practice_bank.common import EXTRA_TOPICS, PROBLEMS, TOPICS
from practice_bank import core  # noqa: F401
from practice_bank import algorithms  # noqa: F401
from practice_bank import sql  # noqa: F401
from practice_bank import dsa_basics  # noqa: F401
from practice_bank import dsa_search_lists  # noqa: F401
from practice_bank import dsa_structures  # noqa: F401
from practice_bank import dsa_advanced  # noqa: F401
from practice_bank.metadata import META

for _p in PROBLEMS:
    for _key, _value in META.get(_p["slug"], {}).items():
        _p.setdefault(_key, _value)

__all__ = ["PROBLEMS", "TOPICS", "EXTRA_TOPICS"]
