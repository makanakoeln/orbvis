"""Monitoring state schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.board import AggregationNode

HostStateValue = Literal["UP", "DOWN", "UNREACHABLE", "PENDING"]
ServiceStateValue = Literal["OK", "WARNING", "CRITICAL", "UNKNOWN", "PENDING"]
# Synthetic states that may also appear on ObjectState.state:
#   NO_PERMISSION — caller lacks contact-group access for this object
#   NOT_FOUND     — host/service/group is absent from monitoring data entirely


class ServicesSummary(BaseModel):
    ok: int = 0
    warning: int = 0
    critical: int = 0
    unknown: int = 0
    pending: int = 0


class ObjectState(BaseModel):
    object_id: str
    type: str
    state: str
    output: str = ""
    perf_data: str = ""
    acknowledged: bool = False
    in_downtime: bool = False
    stale: bool = False
    notifications_enabled: bool = True
    active_checks_enabled: bool = True
    address: str = ""
    alias: str = ""
    last_check: float | None = None
    next_check: float | None = None
    state_type: str = ""  # "HARD" | "SOFT" | ""
    current_attempt: int = 0
    max_attempts: int = 0
    last_state_change: float | None = None
    # Set in distributed Checkmk setups to identify the originating site.
    site_id: str | None = None
    # Populated only for type=='aggregation' when the BoardObject has expand_depth > 0.
    tree: AggregationNode | None = None
    # Aggregated service-state counts; populated only for type=='host'.
    services_summary: ServicesSummary | None = None


class ObjectTiming(BaseModel):
    """Slim check-timing patch for the fields excluded from the state-delta
    hash. Without it they freeze on the client and "check overdue" grows with
    the board's open time."""

    object_id: str
    last_check: float | None = None
    next_check: float | None = None
    current_attempt: int = 0


class CommentInfo(BaseModel):
    id: int
    author: str
    comment: str
    entry_time: float
    expire_time: float | None = None


class DowntimeInfo(BaseModel):
    id: int
    author: str
    comment: str
    start_time: float
    end_time: float
    fixed: bool = True


class ObjectDetails(BaseModel):
    """Extended object info loaded on demand (Drawer, Properties modal).

    Kept separate from ``ObjectState`` so the WebSocket stream stays compact —
    long_output, comments, downtimes and topology can each be many KB and
    rarely change between checks.
    """

    type: Literal["host", "service"]
    host_name: str
    service_description: str | None = None
    long_output: str = ""
    check_command: str = ""
    latency: float | None = None
    execution_time: float | None = None
    is_flapping: bool = False
    in_notification_period: bool = True
    last_time_ok: float | None = None  # service only
    notification_period: str = ""
    check_interval: float | None = None
    parents: list[str] = []
    children: list[str] = []
    host_groups: list[str] = []
    service_groups: list[str] = []
    contact_groups: list[str] = []
    labels: dict[str, str] = {}
    # CMK graphing-plugin display titles for the perf_data metric IDs of this
    # service (e.g. {"mem_lnx_committed_as": "Committed memory"}). Drawer falls
    # back to title-cased metric IDs when an entry is missing.
    metric_titles: dict[str, str] = {}
    comments: list[CommentInfo] = []
    downtimes: list[DowntimeInfo] = []


class FolderTreeNode(BaseModel):
    """A node in a SETUP folder-tree board (concept v3).

    ``kind`` distinguishes folders from host/service leaves. Folders carry an
    aggregated worst-state across everything below them, or the synthetic
    ``"EMPTY"`` state when (recursively) hostless — ``EMPTY`` is ranked outside
    the normal severity scale and excluded from the parent's worst-state.
    """

    path: str  # folder path key, e.g. "datacenters/muc" ("" = root)
    title: str  # display title (real, or prettified slug)
    kind: Literal["folder", "host", "service"] = "folder"
    state: str  # aggregated/own state; "EMPTY" for hostless folders
    is_empty: bool = False
    # Whether the requesting user may see this folder (Checkmk folder permissions:
    # see-all, or member of the folder's contact groups). Empty + non-permitted
    # folders are pruned so a scoped user never sees SETUP folder names they have
    # no access to. Internal-only — drives pruning, not sent to the client.
    permitted: bool = Field(default=True, exclude=True)
    folder_id: str = ""  # stable WATO ``__id`` when known (v3 §7.1)
    host_count: int = 0  # hosts at/below this node
    problem_count: int = 0  # non-OK hosts at/below (for badges)
    # Hosts at/below this node grouped by their combined state, problem states
    # only (e.g. {"CRITICAL": 4, "WARNING": 46}). Powers severity-aware badges.
    severity_counts: dict[str, int] = Field(default_factory=dict)
    output: str = ""  # leaf plugin output
    acknowledged: bool = False
    in_downtime: bool = False
    is_flapping: bool = False
    last_state_change: float | None = None  # leaf age for triage ("since…")
    # Distributed monitoring: leaf hosts carry their originating site (v3 §5).
    site_id: str | None = None
    children: list[FolderTreeNode] = Field(default_factory=list)


class FolderHostService(BaseModel):
    """One service of a host, fetched lazily when a foldertree host is expanded.

    Kept minimal: the frontend already knows the host (path/site) it drilled
    into, so it composes the full FolderTreeNode from this. Ordered by the
    endpoint worst-state first (CRITICAL on top).
    """

    name: str
    state: str
    output: str = ""
    acknowledged: bool = False
    in_downtime: bool = False
    is_flapping: bool = False
    last_state_change: float | None = None


class MapStates(BaseModel):
    map_name: str
    states: list[ObjectState]
    generated_at: float  # unix timestamp
    connection_ok: bool = True  # False when the monitoring connection is unreachable
    # Populated only for foldertree boards: the resolved + aggregated tree.
    folder_tree: FolderTreeNode | None = None
