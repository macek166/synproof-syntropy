from enum import Enum
from typing import Optional, Dict, Any, List, Union
import uuid
from pydantic import BaseModel, Field

class SourceTier(int, Enum):
    FORMAL_LOGICAL = 100
    CUSTOMER_SOT = 95           # Verified Customer Ground-Truth Connector (DB, API, Sub-Agent)
    PEER_REVIEWED_SCIENCE = 85  # Vědecké práce a studie (arXiv apod. - sem nepatří Wikipedie)
    EXACT_WORKS = 75            # Exaktní práce a deterministické kalkulace
    OFFICIAL_INSTITUTIONAL = 70
    WIKIPEDIA = 60              # Wikipedie a encyklopedie (samostatné místo)
    REPUTABLE_SYNTHESIS = 50
    EMPIRICAL_OBSERVATION = 35
    COMMON_SENSE_HEURISTIC = 20
    UNSUPPORTED = 0

class SourceType(str, Enum):
    CUSTOMER_SOT = "customer_sot"                    # Ověřený zákaznický zdroj pravdy (SQL tabulka, interní API, data-retrieval agent)
    PEER_REVIEWED_SCIENCE = "peer_reviewed_science"  # 1. Vědecké práce (arXiv, akademické studie). Sem NEPATŘÍ Wikipedie!
    EXACT_WORKS = "exact_works"                      # 2. Exaktní práce, matematické kalkulace a deterministické důkazy
    WIKIPEDIA = "wikipedia"                          # Samostatné vyhrazené místo pro Wikipedii (až sekundární zdroj po vědeckých pracích)
    FORMAL_LOGICAL = "formal_logic"                  # Formální logika a dedukce
    OFFICIAL_INSTITUTIONAL = "official_institutional"# Oficiální institucionální data
    COMMON_SENSE = "common_sense"                    # Obecné empirické pozorování
    UNSUPPORTED = "unsupported"                      # Nepodložené tvrzení

class CustomConnectorConfig(BaseModel):
    id: str = Field(default_factory=lambda: f"conn_{uuid.uuid4().hex[:10]}")
    name: str = Field(..., min_length=1, max_length=120, description="Human-readable connector name")
    connector_type: str = Field(
        default="rest_webhook",
        description="One of: 'rest_webhook', 'rest_api', 'sql_table_snapshot', 'sql_postgrest', 'agent_endpoint', 'agent_webhook', 'mcp_tool', 'graphql'"
    )
    endpoint_url: Optional[str] = Field(default=None, description="HTTPS/HTTP endpoint for live retrieval")
    method: str = Field(default="POST", description="HTTP method: 'POST' or 'GET'")
    headers: Dict[str, str] = Field(default_factory=dict, description="Optional auth/custom HTTP headers")
    description: Optional[str] = Field(default=None, max_length=500, description="What domain data this connector provides")
    timeout_ms: int = Field(default=4000, ge=250, le=4000, description="Hard timeout in ms (max 4000ms)")
    response_axioms_path: Optional[str] = Field(default=None, description="Optional dot-path to extract array/facts from JSON response")
    row_template: Optional[str] = Field(
        default=None,
        description="Optional Python format string to render dict rows into declarative axioms (e.g. 'Tier {tier} enforces max liability {max_liability_eur} EUR.')"
    )
    static_rows: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=None,
        description="Inline SQL/JSON table rows or static facts when connector_type=='sql_table_snapshot'"
    )
    enabled: bool = Field(default=True)

class DebateEvent(BaseModel):
    type: str
    node: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
