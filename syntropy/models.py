from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class SourceTier(int, Enum):
    FORMAL_LOGICAL = 100
    PEER_REVIEWED_SCIENCE = 85  # Vědecké práce a studie (arXiv apod. - sem nepatří Wikipedie)
    EXACT_WORKS = 75            # Exaktní práce a deterministické kalkulace
    OFFICIAL_INSTITUTIONAL = 70
    WIKIPEDIA = 60              # Wikipedie a encyklopedie (samostatné místo)
    REPUTABLE_SYNTHESIS = 50
    EMPIRICAL_OBSERVATION = 35
    COMMON_SENSE_HEURISTIC = 20
    UNSUPPORTED = 0

class SourceType(str, Enum):
    PEER_REVIEWED_SCIENCE = "peer_reviewed_science"  # 1. Vědecké práce (arXiv, akademické studie). Sem NEPATŘÍ Wikipedie!
    EXACT_WORKS = "exact_works"                      # 2. Exaktní práce, matematické kalkulace a deterministické důkazy
    WIKIPEDIA = "wikipedia"                          # Samostatné vyhrazené místo pro Wikipedii (až sekundární zdroj po vědeckých pracích)
    FORMAL_LOGICAL = "formal_logic"                  # Formální logika a dedukce
    OFFICIAL_INSTITUTIONAL = "official_institutional"# Oficiální institucionální data
    COMMON_SENSE = "common_sense"                    # Obecné empirické pozorování
    UNSUPPORTED = "unsupported"                      # Nepodložené tvrzení

class DebateEvent(BaseModel):
    type: str
    node: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
