import argparse
import base64
import json
import shutil
import struct
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlsplit
from rich.markup import escape as rich_escape
from rich.text import Text


try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.screen import ModalScreen
    from textual.widgets import DataTable, Footer, Header, Static
    TEXTUAL_IMPORT_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local env
    App = object  # type: ignore[assignment]
    ComposeResult = object  # type: ignore[assignment]
    ModalScreen = object  # type: ignore[assignment]
    Binding = None  # type: ignore[assignment]
    Horizontal = Vertical = VerticalScroll = DataTable = Footer = Header = Static = None  # type: ignore[assignment]
    TEXTUAL_IMPORT_ERROR = exc


INITIAL_MAGIC = 0xFCFB6D1BA7725C30
SIMPLE_FINAL_MAGIC = 0xF4FA6F45970D41D8
SIMPLE_INDEX_MAGIC = 0x656E74657220796F
DEFAULT_CACHE_SIZE = 80 * 1024 * 1024
EVICTION_MARGIN_DIVISOR = 20
ESTIMATED_ENTRY_OVERHEAD = 512
CACHE_ACCOUNTING_SLOT_SIZE = 256
QUOTA_BAR_WIDTH = 64
SIDE_PANEL_WIDTH = 54
PICKLE_HEADER_SIZE = 8
WINDOWS_TO_UNIX_EPOCH_SECONDS = 11644473600
HINT_HIGH_PRIORITY = 1 << 1
PRIORITIZATION_FACTOR_DEFAULT = 10
PRIORITIZATION_PERIOD_SECONDS = 24 * 60 * 60
DEFAULT_QUOTA_RANGE_VISIBLE_SLOTS = 64
DEFAULT_QUOTA_RANGE_SLOTS_PER_ROW = 16
SIMPLE_FILE_HEADER_SIZE = 24
SIMPLE_FILE_EOF_SIZE = 24
SIMPLE_KEY_SHA256_SIZE = 32
SIMPLE_EOF_FLAG_HAS_KEY_SHA256 = 1 << 1
SORTS = [
    ("eviction_score", "score"),
    ("accounted", "rounded"),
    ("size", "raw"),
    ("slack", "slack"),
    ("key_length", "key"),
]
SIMPLE_INDEX_MAGIC = 0x656E74657220796F
PICKLE_HEADER_SIZE = 8
WINDOWS_TO_UNIX_EPOCH_SECONDS = 11644473600
HINT_HIGH_PRIORITY = 1 << 1
PRIORITIZATION_FACTOR_DEFAULT = 10
PRIORITIZATION_PERIOD_SECONDS = 24 * 60 * 60


@dataclass
class QuotaInfo:
    max_quota: int | None
    source: str
    detail: str
    high_watermark: int | None
    low_watermark: int | None
    free_disk: int | None


@dataclass
class MetricSummary:
    count: int
    raw_bytes: int
    chromium_bytes: int
    accounted_bytes: int
    eviction_weight_bytes: int
    total_key_bytes: int
    max_key_bytes: int
    unique_urls: int
    unique_paths: int
    unique_isolation_keys: int
    partitions: Counter[str]
    largest_entry: int
    avg_entry: float


@dataclass
class StatRow:
    key: str
    label: str
    value: str
    description: str


@dataclass
class Snapshot:
    input_spec: str
    resolved_from: str
    profile: Path
    cache_dir: Path
    all_entries: list[dict[str, object]]
    visible_entries: list[dict[str, object]]
    all_summary: MetricSummary
    visible_summary: MetricSummary
    cache_data_total_bytes: int
    cache_data_other_bytes: int
    quota: QuotaInfo
    filter_text: str | None
    collected_at: float


@dataclass
class EntryPayload:
    path: str
    size: int
    preview_bytes: bytes
    truncated: bool


@dataclass
class LogicalSlotSpan:
    ordinal: int
    start_slot: int
    end_slot: int
    entry: dict[str, object]


@dataclass
class ProfileTarget:
    input_spec: str
    host_profile: Path | None
    process_hint: str | None
    container: str | None = None


@dataclass
class DirectoryEntry:
    name: str
    path: str
    is_profile: bool
    mtime: float


@dataclass
class DirectoryState:
    current_path: str
    parent_path: str | None
    is_profile: bool
    entries: list[DirectoryEntry]


REMOTE_COLLECTOR = """
import json
import os
import struct
import sys
import time
from urllib.parse import parse_qs, urlsplit

INITIAL_MAGIC = 0xFCFB6D1BA7725C30
SIMPLE_FINAL_MAGIC = 0xF4FA6F45970D41D8
SIMPLE_INDEX_MAGIC = 0x656E74657220796F
DEFAULT_CACHE_SIZE = 80 * 1024 * 1024
EVICTION_MARGIN_DIVISOR = 20
ESTIMATED_ENTRY_OVERHEAD = 512
PICKLE_HEADER_SIZE = 8
WINDOWS_TO_UNIX_EPOCH_SECONDS = 11644473600
HINT_HIGH_PRIORITY = 1 << 1
PRIORITIZATION_FACTOR_DEFAULT = 10
PRIORITIZATION_PERIOD_SECONDS = 24 * 60 * 60
SIMPLE_FILE_HEADER_SIZE = 24
SIMPLE_FILE_EOF_SIZE = 24
SIMPLE_KEY_SHA256_SIZE = 32
SIMPLE_EOF_FLAG_HAS_KEY_SHA256 = 1 << 1


def round_256(n):
    return ((n + 255) // 256) * 256


def simple_file_size_from_data_size(key_length, data_size):
    return data_size + key_length + SIMPLE_FILE_HEADER_SIZE + SIMPLE_FILE_EOF_SIZE


def parse_header(data):
    if len(data) < SIMPLE_FILE_HEADER_SIZE:
        return None
    initial_magic, _version, key_length, _key_hash, _padding = struct.unpack("<QIIII", data[:SIMPLE_FILE_HEADER_SIZE])
    if initial_magic != INITIAL_MAGIC:
        return None
    return key_length, SIMPLE_FILE_HEADER_SIZE


def parse_eof(data):
    if len(data) < SIMPLE_FILE_EOF_SIZE:
        return None
    final_magic, flags, _crc32, stream_size, _padding = struct.unpack("<QIIII", data[:SIMPLE_FILE_EOF_SIZE])
    if final_magic != SIMPLE_FINAL_MAGIC:
        return None
    return flags, stream_size


def read_at(path, offset, size):
    with open(path, "rb") as fh:
        fh.seek(offset)
        return fh.read(size)


def extract_key(path):
    try:
        header_bytes = read_at(path, 0, SIMPLE_FILE_HEADER_SIZE)
    except OSError:
        return None, None
    header = parse_header(header_bytes)
    if not header:
        return None, None
    key_length, header_size = header
    try:
        key_bytes = read_at(path, header_size, key_length)
    except OSError:
        return None, None
    try:
        return key_bytes.decode(), key_length
    except UnicodeDecodeError:
        return None, key_length


def file0_stream_sizes(path, key_length, file0_size):
    minimum = SIMPLE_FILE_HEADER_SIZE + key_length + (2 * SIMPLE_FILE_EOF_SIZE)
    if file0_size < minimum:
        return None
    try:
        eof0_raw = read_at(path, file0_size - SIMPLE_FILE_EOF_SIZE, SIMPLE_FILE_EOF_SIZE)
    except OSError:
        return None
    eof0 = parse_eof(eof0_raw)
    if not eof0:
        return None
    flags, stream0_size = eof0
    extra = SIMPLE_KEY_SHA256_SIZE if (flags & SIMPLE_EOF_FLAG_HAS_KEY_SHA256) else 0
    stream1_size = file0_size - SIMPLE_FILE_HEADER_SIZE - key_length - (2 * SIMPLE_FILE_EOF_SIZE) - extra - stream0_size
    if stream1_size < 0:
        return None
    eof1_offset = SIMPLE_FILE_HEADER_SIZE + key_length + stream1_size
    if eof1_offset < 0 or eof1_offset + SIMPLE_FILE_EOF_SIZE > file0_size:
        return None
    try:
        eof1_raw = read_at(path, eof1_offset, SIMPLE_FILE_EOF_SIZE)
    except OSError:
        return None
    if not parse_eof(eof1_raw):
        return None
    return stream0_size, stream1_size


def file1_stream_size(path, key_length):
    if not os.path.isfile(path):
        return 0
    try:
        file1_size = os.path.getsize(path)
    except OSError:
        return None
    minimum = SIMPLE_FILE_HEADER_SIZE + key_length + SIMPLE_FILE_EOF_SIZE
    if file1_size < minimum:
        return None
    try:
        eof_raw = read_at(path, file1_size - SIMPLE_FILE_EOF_SIZE, SIMPLE_FILE_EOF_SIZE)
    except OSError:
        return None
    if not parse_eof(eof_raw):
        return None
    return file1_size - minimum


def chromium_disk_usage(path, key_length):
    try:
        file0_size = os.path.getsize(path)
    except OSError:
        return entry_family_size(path), "stored_fallback"
    stream01 = file0_stream_sizes(path, key_length, file0_size)
    if not stream01:
        return entry_family_size(path), "stored_fallback"
    stream0_size, stream1_size = stream01
    prefix = path[:-2]
    stream2_size = file1_stream_size(prefix + "_1", key_length)
    if stream2_size is None:
        return entry_family_size(path), "stored_fallback"
    sparse_size = 0
    source = "parsed"
    sparse_path = prefix + "_s"
    if os.path.isfile(sparse_path):
        try:
            sparse_size = os.path.getsize(sparse_path)
        except OSError:
            return entry_family_size(path), "stored_fallback"
        source = "parsed+physical_sparse"
    total = 0
    for stream_size in (stream0_size, stream1_size, stream2_size):
        total += simple_file_size_from_data_size(key_length, stream_size)
    total += sparse_size
    return total, source


def partition_of(key):
    if not key:
        return "unknown"
    if "_dk_cn_" in key:
        return "_dk_cn_"
    if "_dk_" in key:
        return "_dk_"
    return "unpartitioned"


def last_url_start(key):
    return max(key.rfind("http://"), key.rfind("https://"))


def isolation_key_of(key):
    if not key:
        return None
    marker = partition_of(key)
    if marker not in {"_dk_", "_dk_cn_"}:
        return None
    start = key.find(marker)
    end = last_url_start(key)
    if start == -1 or end == -1 or end <= start:
        return None
    return key[start + len(marker):end].strip()


def url_of(key):
    if not key:
        return None
    start = last_url_start(key)
    if start == -1:
        return None
    return key[start:].strip()


def parse_switch(args, name):
    prefix = f"{name}="
    for i, arg in enumerate(args):
        if arg.startswith(prefix):
            return arg[len(prefix):]
        if arg == name and i + 1 < len(args):
            return args[i + 1]
    return None


def split_feature_list(raw):
    items = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        items.append(part.split("<", 1)[0].split(":", 1)[0])
    return set(items)


def detect_prioritized_caching(profile):
    wanted = {profile, os.path.realpath(profile)}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            raw = open(f"/proc/{pid}/cmdline", "rb").read()
        except OSError:
            continue
        if not raw:
            continue
        args = [part.decode(errors="ignore") for part in raw.split(b"\\0") if part]
        user_data_dir = parse_switch(args, "--user-data-dir")
        if not user_data_dir:
            continue
        candidate = {user_data_dir, os.path.realpath(user_data_dir)}
        if wanted.isdisjoint(candidate):
            continue
        disabled = split_feature_list(parse_switch(args, "--disable-features"))
        enabled = split_feature_list(parse_switch(args, "--enable-features"))
        if "SimpleCachePrioritizedCaching" in disabled:
            return False
        if "SimpleCachePrioritizedCaching" in enabled:
            return True
        return True
    return True


def entry_hash_from_name(name):
    value = name
    if value.startswith("todelete_"):
        value = value[len("todelete_"):]
    prefix = value.split("_", 1)[0]
    if len(prefix) != 16:
        return None
    try:
        return int(prefix, 16)
    except ValueError:
        return None


def entry_family_paths(path):
    prefix = path[:-2]
    paths = []
    for suffix in ("_0", "_1", "_s"):
        candidate = prefix + suffix
        if os.path.isfile(candidate):
            paths.append(candidate)
    return paths


def entry_family_size(path):
    total = 0
    for candidate in entry_family_paths(path):
        try:
            total += os.path.getsize(candidate)
        except OSError:
            pass
    return total


def internal_time_to_unix_seconds(internal):
    if not internal:
        return None
    return max(0, internal // 1000000 - WINDOWS_TO_UNIX_EPOCH_SECONDS)


def parse_index_entries(cache_dir):
    entries = {}
    index_dir = os.path.join(cache_dir, "index-dir")
    for name in ("the-real-index", "temp-index"):
        path = os.path.join(index_dir, name)
        try:
            data = open(path, "rb").read()
        except OSError:
            continue
        if len(data) < PICKLE_HEADER_SIZE:
            continue
        payload_size, _crc = struct.unpack_from("<II", data, 0)
        header_size = len(data) - payload_size
        if header_size != PICKLE_HEADER_SIZE or payload_size < 36 or payload_size > len(data) - PICKLE_HEADER_SIZE:
            continue
        payload = memoryview(data)[header_size:header_size + payload_size]
        offset = 0
        magic, version = struct.unpack_from("<QI", payload, offset)
        offset += 12
        entry_count = struct.unpack_from("<Q", payload, offset)[0]
        offset += 8
        _cache_size = struct.unpack_from("<Q", payload, offset)[0]
        offset += 8
        _reason = struct.unpack_from("<I", payload, offset)[0]
        offset += 4
        if magic != SIMPLE_INDEX_MAGIC:
            continue
        for _ in range(entry_count):
            if offset + 24 > len(payload):
                entries.clear()
                break
            hash_key = struct.unpack_from("<Q", payload, offset)[0]
            offset += 8
            last_used_internal = struct.unpack_from("<q", payload, offset)[0]
            offset += 8
            packed_entry_info = struct.unpack_from("<Q", payload, offset)[0]
            offset += 8
            entries[hash_key] = {
                "last_used_epoch": internal_time_to_unix_seconds(last_used_internal),
                "in_memory_data": packed_entry_info & 0x03,
                "entry_size": ((packed_entry_info >> 8) << 8),
                "source": "index",
            }
        if entries:
            return entries
    return entries


def metadata_from_stat(path):
    try:
        st = os.stat(path)
    except OSError:
        return {}
    last_used = int(st.st_atime or st.st_mtime or 0)
    return {
        "last_used_epoch": last_used or None,
        "in_memory_data": 0,
        "source": "stat",
    }


def eviction_score_for(accounted, last_used_epoch, in_memory_data, prioritized_caching):
    if not last_used_epoch:
        return None, None
    now = int(time.time())
    age_seconds = max(0, now - int(last_used_epoch))
    score = age_seconds * (int(accounted) + ESTIMATED_ENTRY_OVERHEAD)
    if prioritized_caching and age_seconds < PRIORITIZATION_PERIOD_SECONDS and (in_memory_data & HINT_HIGH_PRIORITY) == HINT_HIGH_PRIORITY:
        score //= PRIORITIZATION_FACTOR_DEFAULT
    return score, age_seconds


def detect_process_quota(profile):
    wanted = {profile, os.path.realpath(profile)}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            raw = open(f"/proc/{pid}/cmdline", "rb").read()
        except OSError:
            continue
        if not raw:
            continue
        args = [part.decode(errors="ignore") for part in raw.split(b"\\0") if part]
        user_data_dir = parse_switch(args, "--user-data-dir")
        if not user_data_dir:
            continue
        candidate = {user_data_dir, os.path.realpath(user_data_dir)}
        if wanted.isdisjoint(candidate):
            continue
        cache_size = parse_switch(args, "--disk-cache-size")
        if cache_size and cache_size.isdigit() and int(cache_size) > 0:
            return int(cache_size), f"process {pid} --disk-cache-size"
    return None, ""


def detect_local_state_quota(profile):
    path = os.path.join(profile, "Local State")
    try:
        data = json.load(open(path))
    except (OSError, json.JSONDecodeError):
        return None, ""
    browser = data.get("browser", {})
    cache_size = browser.get("disk_cache_size")
    if isinstance(cache_size, int) and cache_size > 0:
        return cache_size, "Local State browser.disk_cache_size"
    return None, ""


def preferred_cache_size_internal(available):
    if available < DEFAULT_CACHE_SIZE * 10 // 8:
        return available * 8 // 10
    if available < DEFAULT_CACHE_SIZE * 10:
        return DEFAULT_CACHE_SIZE
    if available < DEFAULT_CACHE_SIZE * 25:
        return available // 10
    if available < DEFAULT_CACHE_SIZE * 250:
        return DEFAULT_CACHE_SIZE * 5 // 2
    return available // 100


def estimate_default_quota(profile):
    stat_path = profile
    while stat_path and not os.path.exists(stat_path):
        parent = os.path.dirname(stat_path)
        if parent == stat_path:
            break
        stat_path = parent
    if not stat_path:
        stat_path = "/"
    try:
        st = os.statvfs(stat_path)
    except OSError:
        return None, "could not stat filesystem", None
    free_disk = st.f_bavail * st.f_frsize
    percent_relative_size = 100 if sys.platform.startswith("win") else 400
    scaled_default = DEFAULT_CACHE_SIZE * percent_relative_size // 100
    preferred = preferred_cache_size_internal(free_disk)
    if preferred < free_disk // 5:
        preferred = min(preferred * percent_relative_size // 100, free_disk // 5)
    size_limit = scaled_default * 4
    return min(preferred, size_limit), "estimated PreferredCacheSize", free_disk


def detect_quota(profile, override):
    free_disk = None
    if override is not None:
        max_quota = override
        source = "manual override"
        detail = "--max-quota"
    else:
        max_quota, detail = detect_process_quota(profile)
        source = "explicit"
        if max_quota is None:
            max_quota, detail = detect_local_state_quota(profile)
        if max_quota is None:
            max_quota, detail, free_disk = estimate_default_quota(profile)
            source = "estimated"
    if free_disk is None:
        _unused, _detail, free_disk = estimate_default_quota(profile)
    high = low = None
    if max_quota:
        high = max_quota - max_quota // EVICTION_MARGIN_DIVISOR
        low = max_quota - 2 * (max_quota // EVICTION_MARGIN_DIVISOR)
    return {
        "max_quota": max_quota,
        "source": source,
        "detail": detail,
        "high_watermark": high,
        "low_watermark": low,
        "free_disk": free_disk,
    }


def collect_entries(cache_dir, profile):
    entries = []
    cache_data_total = 0
    if not os.path.isdir(cache_dir):
        return entries, cache_data_total
    indexed = parse_index_entries(cache_dir)
    prioritized_caching = detect_prioritized_caching(profile)
    for root, _dirs, files in os.walk(cache_dir):
        for name in files:
            path = os.path.join(root, name)
            try:
                cache_data_total += os.path.getsize(path)
            except OSError:
                pass
        for name in sorted(files):
            if not name.endswith("_0"):
                continue
            path = os.path.join(root, name)
            try:
                file0_size = os.path.getsize(path)
            except OSError:
                continue
            size = entry_family_size(path)
            key, key_length = extract_key(path)
            url = url_of(key)
            query = parse_qs(urlsplit(url).query) if url else {}
            hash_key = entry_hash_from_name(name)
            metadata = dict(indexed.get(hash_key) or metadata_from_stat(path))
            chromium_size, chromium_size_source = chromium_disk_usage(path, key_length or 0)
            accounted = int(metadata.get("entry_size") or 0) or round_256(chromium_size)
            score, age_seconds = eviction_score_for(
                accounted,
                metadata.get("last_used_epoch"),
                int(metadata.get("in_memory_data", 0)),
                prioritized_caching,
            )
            entries.append(
                {
                    "file": name,
                    "relative_path": os.path.relpath(path, cache_dir),
                    "size": size,
                    "file0_size": file0_size,
                    "chromium_size": chromium_size,
                    "chromium_size_source": chromium_size_source,
                    "accounted": accounted,
                    "accounted_source": metadata.get("source", "none") if metadata.get("entry_size") else f"rounded {chromium_size_source}",
                    "slack": accounted - chromium_size,
                    "logical_overhead": chromium_size - size,
                    "eviction_weight": accounted + ESTIMATED_ENTRY_OVERHEAD,
                    "eviction_score": score,
                    "age_seconds": age_seconds,
                    "last_used_epoch": metadata.get("last_used_epoch"),
                    "metadata_source": metadata.get("source", "none"),
                    "in_memory_data": int(metadata.get("in_memory_data", 0)),
                    "high_priority": bool(int(metadata.get("in_memory_data", 0)) & HINT_HIGH_PRIORITY),
                    "key_length": key_length or 0,
                    "partition": partition_of(key),
                    "isolation_key": isolation_key_of(key),
                    "key": key,
                    "url": url,
                    "path": urlsplit(url).path if url else None,
                    "query": query,
                }
            )
    entries.sort(key=lambda entry: entry["file"])
    return entries, cache_data_total


profile = os.path.realpath(sys.argv[1])
override = None if len(sys.argv) < 3 or not sys.argv[2] else int(sys.argv[2])
cache_dir = os.path.join(profile, "Default", "Cache", "Cache_Data")
entries, cache_data_total = collect_entries(cache_dir, profile)
print(
    json.dumps(
        {
            "profile": profile,
            "cache_dir": cache_dir,
            "entries": entries,
            "cache_data_total_bytes": cache_data_total,
            "quota": detect_quota(profile, override),
        }
    )
)
"""


REMOTE_ENTRY_VIEWER = """
import base64
import json
import os
import sys

MAX_PREVIEW = 32768
path = sys.argv[1]
data = open(path, "rb").read()
preview = data[:MAX_PREVIEW]
print(
    json.dumps(
        {
            "path": os.path.realpath(path),
            "size": len(data),
            "truncated": len(data) > MAX_PREVIEW,
            "preview_b64": base64.b64encode(preview).decode(),
        }
    )
)
"""


REMOTE_DIRECTORY_INSPECTOR = """
import json
import os
import sys


def is_profile_dir(path):
    return (
        os.path.isdir(os.path.join(path, "Default"))
        or os.path.exists(os.path.join(path, "Local State"))
        or os.path.isdir(os.path.join(path, "Default", "Cache", "Cache_Data"))
    )


def nearest_dir(path):
    current = os.path.realpath(path)
    while not os.path.isdir(current):
        parent = os.path.dirname(current)
        if parent == current:
            return "/"
        current = parent
    return current


root = nearest_dir(sys.argv[1])
entries = []
dirs = []
for name in os.listdir(root):
    child = os.path.join(root, name)
    if not os.path.isdir(child):
        continue
    try:
        mtime = os.path.getmtime(child)
    except OSError:
        mtime = 0
    dirs.append((mtime, name, child))
for _mtime, name, child in sorted(dirs, key=lambda item: (-item[0], item[1].lower())):
    entries.append(
        {
            "name": name,
            "path": os.path.realpath(child),
            "is_profile": is_profile_dir(child),
            "mtime": _mtime,
        }
    )
parent = os.path.dirname(root)
if parent == root:
    parent = None
print(
    json.dumps(
        {
            "current_path": root,
            "parent_path": parent,
            "is_profile": is_profile_dir(root),
            "entries": entries,
        }
    )
)
"""


def round_256(n: int) -> int:
    return ((n + 255) // 256) * 256


def fmt_bytes(value: int | float | None, exact: bool = False) -> str:
    if value is None:
        return "?"
    if exact:
        if isinstance(value, float) and not value.is_integer():
            return f"{value:.2f} B"
        return f"{int(value)} B"
    negative = value < 0
    n = float(abs(value))
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if n < 1024 or unit == units[-1]:
            if unit == "B":
                text = f"{int(n)} {unit}"
            else:
                text = f"{n:.2f} {unit}"
            return f"-{text}" if negative else text
        n /= 1024
    return "?"


def fmt_ratio(used: int, total: int | None, exact: bool = False) -> str:
    if not total:
        return f"{fmt_bytes(used, exact)} / ?"
    percent = 100.0 * used / total
    return f"{fmt_bytes(used, exact)} / {fmt_bytes(total, exact)} ({percent:.1f}%)"


def quota_slots(value: int | None) -> int | None:
    if value is None:
        return None
    return max(0, (int(value) + CACHE_ACCOUNTING_SLOT_SIZE - 1) // CACHE_ACCOUNTING_SLOT_SIZE)


def render_quota_bar(
    used_bytes: int,
    quota: QuotaInfo,
    width: int = QUOTA_BAR_WIDTH,
) -> tuple[str, str] | None:
    total_slots = quota_slots(quota.max_quota)
    if not total_slots:
        return None

    used_slots = min(total_slots, quota_slots(used_bytes) or 0)
    low_slots = min(total_slots, quota_slots(quota.low_watermark) or 0)
    high_slots = min(total_slots, quota_slots(quota.high_watermark) or 0)

    def slot_to_col(slot: int) -> int:
        if slot <= 0:
            return 0
        return min(width - 1, (slot * width) // total_slots)

    chars = ["#" if index < (used_slots * width) / total_slots else "." for index in range(width)]

    low_col = slot_to_col(low_slots)
    high_col = slot_to_col(high_slots)
    chars[low_col] = "L"
    chars[high_col] = "H"

    if used_slots >= total_slots:
        chars[-1] = "@"

    bar = "".join(chars)
    scale = (
        f"slot=256 B, used={used_slots}, low={low_slots}, "
        f"high={high_slots}, max={total_slots}"
    )
    return bar, scale


def slot_fill_width(slots: int, total_slots: int, width: int) -> int:
    if slots <= 0 or total_slots <= 0 or width <= 0:
        return 0
    return max(1, min(width, (slots * width + total_slots - 1) // total_slots))


def slot_to_col(slot: int, total_slots: int, width: int) -> int:
    if width <= 0 or total_slots <= 0:
        return 0
    if slot <= 0:
        return 0
    return min(width - 1, (slot * (width - 1)) // total_slots)


def build_quota_visual(snapshot: Snapshot, exact_bytes: bool = False, width: int = QUOTA_BAR_WIDTH) -> str:
    quota = snapshot.quota
    total_slots = quota_slots(quota.max_quota)
    if not total_slots:
        return "\n".join(
            [
                accent("Quota Visualizer"),
                subtle("Quota unavailable for this profile."),
            ]
        )

    used_slots = min(total_slots, quota_slots(snapshot.all_summary.accounted_bytes) or 0)
    low_slots = min(total_slots, quota_slots(quota.low_watermark) or 0)
    high_slots = min(total_slots, quota_slots(quota.high_watermark) or 0)

    bar_width = max(24, width)
    used_fill = slot_fill_width(used_slots, total_slots, bar_width)
    full_bar = ["#" if index < used_fill else "." for index in range(bar_width)]
    full_bar = "".join(full_bar)

    marker_line = [" " for _ in range(bar_width)]

    def place_marker(slot: int, char: str) -> None:
        col = slot_to_col(slot, total_slots, bar_width)
        marker_line[col] = char if marker_line[col] == " " else "*"

    if used_slots > 0:
        place_marker(used_slots, "U")
    place_marker(low_slots, "L")
    place_marker(high_slots, "H")
    place_marker(total_slots, "M")

    scale_line = [" " for _ in range(bar_width)]

    def place_scale(col: int, text: str) -> None:
        if not text:
            return
        start = max(0, min(bar_width - len(text), col - len(text) // 2))
        for index, char in enumerate(text):
            scale_line[start + index] = char

    place_scale(0, "0")
    place_scale(slot_to_col(low_slots, total_slots, bar_width), "low")
    place_scale(slot_to_col(high_slots, total_slots, bar_width), "high")
    place_scale(slot_to_col(total_slots, total_slots, bar_width), "max")

    return "\n".join(
        [
            accent("Quota Visualizer"),
            f"{accent('Bytes')} : used={escape_markup(fmt_bytes(snapshot.all_summary.accounted_bytes, exact_bytes))}  low={escape_markup(fmt_bytes(quota.low_watermark, exact_bytes))}  high={escape_markup(fmt_bytes(quota.high_watermark, exact_bytes))}  max={escape_markup(fmt_bytes(quota.max_quota, exact_bytes))}",
            f"{accent('Slots')} : used={escape_markup(str(used_slots))}  low={escape_markup(str(low_slots))}  high={escape_markup(str(high_slots))}  max={escape_markup(str(total_slots))}",
            f"{accent('Scale')} : {escape_markup(''.join(scale_line))}",
            f"{accent('Usage')} : {escape_markup(full_bar)}",
            f"{accent('Marks')} : {escape_markup(''.join(marker_line))}",
            f"{accent('Legend')}: {escape_markup('# used, U usage edge, L low watermark, H high watermark, M max')}",
        ]
    )


def fmt_mtime(value: float | int | None) -> str:
    if not value:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(value)))


def fmt_age(value: int | None) -> str:
    if value is None:
        return "-"
    if value < 60:
        return f"{value}s"
    minutes, seconds = divmod(value, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def escape_markup(text: object) -> str:
    return rich_escape(str(text))


def accent(label: object) -> str:
    return f"[bold bright_cyan]{escape_markup(label)}[/]"


def subtle(text: object) -> str:
    return f"[dim]{escape_markup(text)}[/]"


def parse_header(data: bytes) -> tuple[int, int, int] | None:
    if len(data) < SIMPLE_FILE_HEADER_SIZE:
        return None
    initial_magic, _version, key_length, key_hash, _padding = struct.unpack("<QIIII", data[:SIMPLE_FILE_HEADER_SIZE])
    if initial_magic != INITIAL_MAGIC:
        return None
    return key_length, key_hash, SIMPLE_FILE_HEADER_SIZE


def parse_eof(data: bytes) -> tuple[int, int] | None:
    if len(data) < SIMPLE_FILE_EOF_SIZE:
        return None
    final_magic, flags, _crc32, stream_size, _padding = struct.unpack("<QIIII", data[:SIMPLE_FILE_EOF_SIZE])
    if final_magic != SIMPLE_FINAL_MAGIC:
        return None
    return flags, stream_size


def simple_file_size_from_data_size(key_length: int, data_size: int) -> int:
    return data_size + key_length + SIMPLE_FILE_HEADER_SIZE + SIMPLE_FILE_EOF_SIZE


def read_at(path: Path, offset: int, size: int) -> bytes:
    with path.open("rb") as fh:
        fh.seek(offset)
        return fh.read(size)


def extract_key(path: Path) -> tuple[str | None, int | None]:
    try:
        header_bytes = read_at(path, 0, SIMPLE_FILE_HEADER_SIZE)
    except OSError:
        return None, None
    header = parse_header(header_bytes)
    if not header:
        return None, None
    key_length, _key_hash, header_size = header
    try:
        key_bytes = read_at(path, header_size, key_length)
    except OSError:
        return None, None
    try:
        return key_bytes.decode(), key_length
    except UnicodeDecodeError:
        return None, key_length


def partition_of(key: str | None) -> str:
    if not key:
        return "unknown"
    if "_dk_cn_" in key:
        return "_dk_cn_"
    if "_dk_" in key:
        return "_dk_"
    return "unpartitioned"


def last_url_start(key: str) -> int:
    return max(key.rfind("http://"), key.rfind("https://"))


def isolation_key_of(key: str | None) -> str | None:
    if not key:
        return None
    marker = partition_of(key)
    if marker not in {"_dk_", "_dk_cn_"}:
        return None
    start = key.find(marker)
    end = last_url_start(key)
    if start == -1 or end == -1 or end <= start:
        return None
    return key[start + len(marker):end].strip()


def url_of(key: str | None) -> str | None:
    if not key:
        return None
    start = last_url_start(key)
    if start == -1:
        return None
    return key[start:].strip()


def entry_hash_from_name(name: str) -> int | None:
    value = name
    if value.startswith("todelete_"):
        value = value[len("todelete_"):]
    prefix = value.split("_", 1)[0]
    if len(prefix) != 16:
        return None
    try:
        return int(prefix, 16)
    except ValueError:
        return None


def entry_family_paths(path: Path) -> list[Path]:
    prefix = path.name[:-2]
    paths = []
    for suffix in ("_0", "_1", "_s"):
        candidate = path.with_name(prefix + suffix)
        if candidate.is_file():
            paths.append(candidate)
    return paths


def entry_family_size(path: Path) -> int:
    total = 0
    for candidate in entry_family_paths(path):
        try:
            total += candidate.stat().st_size
        except OSError:
            pass
    return total


def file0_stream_sizes(path: Path, key_length: int, file0_size: int) -> tuple[int, int] | None:
    minimum = SIMPLE_FILE_HEADER_SIZE + key_length + (2 * SIMPLE_FILE_EOF_SIZE)
    if file0_size < minimum:
        return None
    try:
        eof0_raw = read_at(path, file0_size - SIMPLE_FILE_EOF_SIZE, SIMPLE_FILE_EOF_SIZE)
    except OSError:
        return None
    eof0 = parse_eof(eof0_raw)
    if not eof0:
        return None
    flags, stream0_size = eof0
    extra = SIMPLE_KEY_SHA256_SIZE if (flags & SIMPLE_EOF_FLAG_HAS_KEY_SHA256) else 0
    stream1_size = file0_size - SIMPLE_FILE_HEADER_SIZE - key_length - (2 * SIMPLE_FILE_EOF_SIZE) - extra - stream0_size
    if stream1_size < 0:
        return None
    eof1_offset = SIMPLE_FILE_HEADER_SIZE + key_length + stream1_size
    if eof1_offset < 0 or eof1_offset + SIMPLE_FILE_EOF_SIZE > file0_size:
        return None
    try:
        eof1_raw = read_at(path, eof1_offset, SIMPLE_FILE_EOF_SIZE)
    except OSError:
        return None
    if not parse_eof(eof1_raw):
        return None
    return stream0_size, stream1_size


def file1_stream_size(path: Path, key_length: int) -> int | None:
    if not path.is_file():
        return 0
    try:
        file1_size = path.stat().st_size
    except OSError:
        return None
    minimum = SIMPLE_FILE_HEADER_SIZE + key_length + SIMPLE_FILE_EOF_SIZE
    if file1_size < minimum:
        return None
    try:
        eof_raw = read_at(path, file1_size - SIMPLE_FILE_EOF_SIZE, SIMPLE_FILE_EOF_SIZE)
    except OSError:
        return None
    if not parse_eof(eof_raw):
        return None
    return file1_size - minimum


def chromium_disk_usage(path: Path, key_length: int) -> tuple[int, str]:
    try:
        file0_size = path.stat().st_size
    except OSError:
        return entry_family_size(path), "stored_fallback"
    stream01 = file0_stream_sizes(path, key_length, file0_size)
    if not stream01:
        return entry_family_size(path), "stored_fallback"
    stream0_size, stream1_size = stream01
    prefix = path.with_name(path.name[:-2])
    stream2_size = file1_stream_size(prefix.with_name(prefix.name + "_1"), key_length)
    if stream2_size is None:
        return entry_family_size(path), "stored_fallback"
    sparse_size = 0
    source = "parsed"
    sparse_path = prefix.with_name(prefix.name + "_s")
    if sparse_path.is_file():
        try:
            sparse_size = sparse_path.stat().st_size
        except OSError:
            return entry_family_size(path), "stored_fallback"
        source = "parsed+physical_sparse"
    total = sum(
        simple_file_size_from_data_size(key_length, stream_size)
        for stream_size in (stream0_size, stream1_size, stream2_size)
    )
    total += sparse_size
    return total, source


def internal_time_to_unix_seconds(internal: int) -> int | None:
    if not internal:
        return None
    return max(0, internal // 1_000_000 - WINDOWS_TO_UNIX_EPOCH_SECONDS)


def split_feature_list(raw: str | None) -> set[str]:
    items = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        items.add(part.split("<", 1)[0].split(":", 1)[0])
    return items


def detect_prioritized_caching(profile: Path, process_hint: str | None) -> bool:
    proc_root = Path("/proc")
    if not proc_root.exists():
        return True

    wanted = {str(profile), str(profile.resolve(strict=False))}
    if process_hint:
        wanted.add(process_hint)

    for proc in proc_root.iterdir():
        if not proc.name.isdigit():
            continue
        try:
            raw = (proc / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        args = [part.decode(errors="ignore") for part in raw.split(b"\0") if part]
        user_data_dir = parse_switch(args, "--user-data-dir")
        if not user_data_dir:
            continue
        candidate = Path(user_data_dir)
        candidate_paths = {str(candidate), str(candidate.resolve(strict=False))}
        if wanted.isdisjoint(candidate_paths):
            continue
        disabled = split_feature_list(parse_switch(args, "--disable-features"))
        enabled = split_feature_list(parse_switch(args, "--enable-features"))
        if "SimpleCachePrioritizedCaching" in disabled:
            return False
        if "SimpleCachePrioritizedCaching" in enabled:
            return True
        return True
    return True


def index_file_candidates(profile: Path) -> list[Path]:
    index_dir = cache_dir(profile) / "index-dir"
    return [index_dir / "the-real-index", index_dir / "temp-index"]


def parse_index_entries(profile: Path) -> dict[int, dict[str, object]]:
    for index_path in index_file_candidates(profile):
        try:
            data = index_path.read_bytes()
        except OSError:
            continue
        if len(data) < PICKLE_HEADER_SIZE:
            continue
        payload_size, _crc = struct.unpack_from("<II", data, 0)
        header_size = len(data) - payload_size
        if header_size != PICKLE_HEADER_SIZE or payload_size < 36 or payload_size > len(data) - PICKLE_HEADER_SIZE:
            continue
        payload = memoryview(data)[header_size:header_size + payload_size]
        offset = 0
        magic, version = struct.unpack_from("<QI", payload, offset)
        offset += 12
        entry_count = struct.unpack_from("<Q", payload, offset)[0]
        offset += 8
        _cache_size = struct.unpack_from("<Q", payload, offset)[0]
        offset += 8
        _reason = struct.unpack_from("<I", payload, offset)[0]
        offset += 4
        if magic != SIMPLE_INDEX_MAGIC:
            continue
        entries: dict[int, dict[str, object]] = {}
        for _ in range(entry_count):
            if offset + 24 > len(payload):
                entries.clear()
                break
            hash_key = struct.unpack_from("<Q", payload, offset)[0]
            offset += 8
            last_used_internal = struct.unpack_from("<q", payload, offset)[0]
            offset += 8
            packed_entry_info = struct.unpack_from("<Q", payload, offset)[0]
            offset += 8
            entries[hash_key] = {
                "last_used_epoch": internal_time_to_unix_seconds(last_used_internal),
                "in_memory_data": packed_entry_info & 0x03,
                "entry_size": ((packed_entry_info >> 8) << 8),
                "source": "index",
            }
        if entries:
            return entries
    return {}


def metadata_from_stat(path: Path) -> dict[str, object]:
    try:
        stat = path.stat()
    except OSError:
        return {}
    last_used = int(stat.st_atime or stat.st_mtime or 0)
    return {
        "last_used_epoch": last_used or None,
        "in_memory_data": 0,
        "source": "stat",
    }


def eviction_score_for(
    accounted: int,
    last_used_epoch: int | None,
    in_memory_data: int,
    prioritized_caching: bool,
) -> tuple[int | None, int | None]:
    if not last_used_epoch:
        return None, None
    age_seconds = max(0, int(time.time()) - int(last_used_epoch))
    score = age_seconds * (accounted + ESTIMATED_ENTRY_OVERHEAD)
    if prioritized_caching and age_seconds < PRIORITIZATION_PERIOD_SECONDS and (in_memory_data & HINT_HIGH_PRIORITY) == HINT_HIGH_PRIORITY:
        score //= PRIORITIZATION_FACTOR_DEFAULT
    return score, age_seconds


def entry_record(
    path: Path,
    indexed: dict[int, dict[str, object]],
    prioritized_caching: bool,
) -> dict[str, object] | None:
    try:
        file0_size = path.stat().st_size
    except OSError:
        return None
    size = entry_family_size(path)
    key, key_length = extract_key(path)
    url = url_of(key)
    query = parse_qs(urlsplit(url).query) if url else {}
    metadata = dict(indexed.get(entry_hash_from_name(path.name)) or metadata_from_stat(path))
    chromium_size, chromium_size_source = chromium_disk_usage(path, key_length or 0)
    accounted = int(metadata.get("entry_size") or 0) or round_256(chromium_size)
    score, age_seconds = eviction_score_for(
        accounted,
        metadata.get("last_used_epoch"),  # type: ignore[arg-type]
        int(metadata.get("in_memory_data", 0)),
        prioritized_caching,
    )
    return {
        "file": path.name,
        "relative_path": path.name,
        "size": size,
        "file0_size": file0_size,
        "chromium_size": chromium_size,
        "chromium_size_source": chromium_size_source,
        "accounted": accounted,
        "accounted_source": metadata.get("source", "none") if metadata.get("entry_size") else f"rounded {chromium_size_source}",
        "slack": accounted - chromium_size,
        "logical_overhead": chromium_size - size,
        "eviction_weight": accounted + ESTIMATED_ENTRY_OVERHEAD,
        "eviction_score": score,
        "age_seconds": age_seconds,
        "last_used_epoch": metadata.get("last_used_epoch"),
        "metadata_source": metadata.get("source", "none"),
        "in_memory_data": int(metadata.get("in_memory_data", 0)),
        "high_priority": bool(int(metadata.get("in_memory_data", 0)) & HINT_HIGH_PRIORITY),
        "key_length": key_length or 0,
        "partition": partition_of(key),
        "isolation_key": isolation_key_of(key),
        "key": key,
        "url": url,
        "path": urlsplit(url).path if url else None,
        "query": query,
    }


def cache_dir(profile: Path) -> Path:
    return profile / "Default" / "Cache" / "Cache_Data"


def looks_like_container_spec(spec: str) -> bool:
    if spec.startswith("/"):
        return False
    container, sep, path = spec.partition(":")
    return bool(container and sep and path.startswith("/"))


def run_command(
    args: list[str], cwd: Path | None = None, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, input=input_text)


def checked_output(
    args: list[str], cwd: Path | None = None, input_text: str | None = None
) -> str:
    result = run_command(args, cwd=cwd, input_text=input_text)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise RuntimeError(f"{' '.join(args)}: {detail}")
    return result.stdout.strip()


def parse_container_spec(spec: str) -> tuple[str, str]:
    container, _, raw_path = spec.partition(":")
    container_path = str(PurePosixPath(raw_path))
    if not container_path.startswith("/"):
        raise RuntimeError("container path must be absolute")
    return container, container_path


def inspect_container(container: str) -> dict:
    data = json.loads(checked_output(["docker", "inspect", container]))
    if not data:
        raise RuntimeError(f"container not found: {container}")
    return data[0]


def resolve_profile_target(spec: str) -> ProfileTarget:
    if looks_like_container_spec(spec):
        container, container_path = parse_container_spec(spec)
        inspect_container(container)
        return ProfileTarget(spec, None, container_path, container)
    host = Path(spec)
    return ProfileTarget(spec, host, str(host))


def all_cache_files(profile: Path) -> list[Path]:
    root = cache_dir(profile)
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def is_profile_dir(path: Path) -> bool:
    return (
        path.is_dir()
        and (
            (path / "Default").is_dir()
            or (path / "Local State").exists()
            or cache_dir(path).is_dir()
        )
    )


def nearest_existing_dir(path: Path) -> Path:
    current = path.resolve(strict=False)
    while not current.exists():
        parent = current.parent
        if parent == current:
            return Path("/")
        current = parent
    return current if current.is_dir() else current.parent


def inspect_host_directory(path: Path) -> DirectoryState:
    root = nearest_existing_dir(path)
    entries = []
    try:
        children = []
        for child in root.iterdir():
            if not child.is_dir():
                continue
            children.append((child.stat().st_mtime, child))
        children.sort(key=lambda item: (-item[0], item[1].name.lower()))
    except OSError as exc:
        raise RuntimeError(f"cannot list {root}: {exc}") from exc
    for mtime, child in children:
        entries.append(
            DirectoryEntry(
                child.name,
                str(child.resolve(strict=False)),
                is_profile_dir(child),
                mtime,
            )
        )
    parent = None if root.parent == root else str(root.parent)
    return DirectoryState(str(root.resolve(strict=False)), parent, is_profile_dir(root), entries)


def inspect_container_directory(container: str, path: str) -> DirectoryState:
    raw = checked_output(
        ["docker", "exec", "-i", container, "python3", "-", path],
        input_text=REMOTE_DIRECTORY_INSPECTOR,
    )
    payload = json.loads(raw)
    return DirectoryState(
        current_path=str(payload["current_path"]),
        parent_path=payload.get("parent_path"),
        is_profile=bool(payload.get("is_profile")),
        entries=[
            DirectoryEntry(
                str(entry["name"]),
                str(entry["path"]),
                bool(entry.get("is_profile")),
                float(entry.get("mtime", 0)),
            )
            for entry in payload.get("entries", [])
        ],
    )


def inspect_directory(target: ProfileTarget, path: str | Path | None = None) -> DirectoryState:
    if target.container is not None:
        current = str(path or target.process_hint or "/")
        return inspect_container_directory(target.container, current)
    if target.host_profile is None:
        raise RuntimeError("host profile path is missing")
    current_path = Path(path) if path is not None else target.host_profile
    return inspect_host_directory(current_path)


def target_is_profile_dir(target: ProfileTarget) -> bool:
    if target.container is not None:
        return inspect_directory(target).is_profile
    if target.host_profile is None:
        return False
    return is_profile_dir(target.host_profile.resolve(strict=False))


def load_entries(profile: Path, process_hint: str | None = None) -> list[dict[str, object]]:
    entries = []
    indexed = parse_index_entries(profile)
    prioritized_caching = detect_prioritized_caching(profile, process_hint)
    for path in sorted(cache_dir(profile).glob("*_0")):
        if not path.is_file():
            continue
        record = entry_record(path, indexed, prioritized_caching)
        if record:
            entries.append(record)
    return entries


def matches_filter(entry: dict[str, object], needle: str | None) -> bool:
    if not needle:
        return True
    haystack = " ".join(
        str(entry.get(field, ""))
        for field in ("file", "partition", "isolation_key", "key", "url", "path", "query")
    )
    return needle in haystack


def summarize(entries: list[dict[str, object]]) -> MetricSummary:
    urls = {str(entry["url"]) for entry in entries if entry["url"]}
    paths = {str(entry["path"]) for entry in entries if entry["path"]}
    isolation_keys = {str(entry["isolation_key"]) for entry in entries if entry["isolation_key"]}
    partitions = Counter(str(entry["partition"]) for entry in entries)
    raw_bytes = sum(int(entry["size"]) for entry in entries)
    chromium_bytes = sum(int(entry["chromium_size"]) for entry in entries)
    accounted_bytes = sum(int(entry["accounted"]) for entry in entries)
    eviction_weight_bytes = sum(int(entry["eviction_weight"]) for entry in entries)
    total_key_bytes = sum(int(entry["key_length"]) for entry in entries)
    max_key_bytes = max((int(entry["key_length"]) for entry in entries), default=0)
    largest_entry = max((int(entry["accounted"]) for entry in entries), default=0)
    avg_entry = accounted_bytes / len(entries) if entries else 0.0
    return MetricSummary(
        count=len(entries),
        raw_bytes=raw_bytes,
        chromium_bytes=chromium_bytes,
        accounted_bytes=accounted_bytes,
        eviction_weight_bytes=eviction_weight_bytes,
        total_key_bytes=total_key_bytes,
        max_key_bytes=max_key_bytes,
        unique_urls=len(urls),
        unique_paths=len(paths),
        unique_isolation_keys=len(isolation_keys),
        partitions=partitions,
        largest_entry=largest_entry,
        avg_entry=avg_entry,
    )


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def parse_switch(args: list[str], name: str) -> str | None:
    prefix = f"{name}="
    for i, arg in enumerate(args):
        if arg.startswith(prefix):
            return arg[len(prefix):]
        if arg == name and i + 1 < len(args):
            return args[i + 1]
    return None


def detect_process_quota(profile: Path, process_hint: str | None) -> tuple[int | None, str]:
    proc_root = Path("/proc")
    if not proc_root.exists():
        return None, ""

    wanted = {str(profile), str(profile.resolve(strict=False))}
    if process_hint:
        wanted.add(process_hint)

    for proc in proc_root.iterdir():
        if not proc.name.isdigit():
            continue
        try:
            raw = (proc / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        args = [part.decode(errors="ignore") for part in raw.split(b"\0") if part]
        user_data_dir = parse_switch(args, "--user-data-dir")
        if not user_data_dir:
            continue
        candidate = Path(user_data_dir)
        candidate_paths = {str(candidate), str(candidate.resolve(strict=False))}
        if wanted.isdisjoint(candidate_paths):
            continue
        cache_size = parse_switch(args, "--disk-cache-size")
        if cache_size and cache_size.isdigit() and int(cache_size) > 0:
            return int(cache_size), f"process {proc.name} --disk-cache-size"
    return None, ""


def detect_local_state_quota(profile: Path) -> tuple[int | None, str]:
    data = read_json(profile / "Local State")
    if not data:
        return None, ""
    browser = data.get("browser", {})
    cache_size = browser.get("disk_cache_size")
    if isinstance(cache_size, int) and cache_size > 0:
        return cache_size, "Local State browser.disk_cache_size"
    return None, ""


def preferred_cache_size_internal(available: int) -> int:
    if available < DEFAULT_CACHE_SIZE * 10 // 8:
        return available * 8 // 10
    if available < DEFAULT_CACHE_SIZE * 10:
        return DEFAULT_CACHE_SIZE
    if available < DEFAULT_CACHE_SIZE * 25:
        return available // 10
    if available < DEFAULT_CACHE_SIZE * 250:
        return DEFAULT_CACHE_SIZE * 5 // 2
    return available // 100


def estimate_default_quota(profile: Path) -> tuple[int | None, str, int | None]:
    try:
        free_disk = shutil.disk_usage(profile).free
    except OSError:
        return None, "could not stat filesystem", None

    percent_relative_size = 100 if sys.platform.startswith("win") else 400
    scaled_default = DEFAULT_CACHE_SIZE * percent_relative_size // 100
    preferred = scaled_default
    preferred = preferred_cache_size_internal(free_disk)
    if preferred < free_disk // 5:
        preferred = min(preferred * percent_relative_size // 100, free_disk // 5)
    size_limit = scaled_default * 4
    return min(preferred, size_limit), "estimated PreferredCacheSize", free_disk


def detect_quota(target: ProfileTarget, profile: Path, override: int | None) -> QuotaInfo:
    free_disk = None
    if override:
        max_quota = override
        source = "manual override"
        detail = "--max-quota"
    else:
        max_quota, detail = detect_process_quota(profile, target.process_hint)
        source = "explicit"
        if max_quota is None:
            max_quota, detail = detect_local_state_quota(profile)
        if max_quota is None:
            max_quota, detail, free_disk = estimate_default_quota(profile)
            source = "estimated"

    if free_disk is None:
        try:
            free_disk = shutil.disk_usage(profile).free
        except OSError:
            free_disk = None

    high = low = None
    if max_quota:
        high = max_quota - max_quota // EVICTION_MARGIN_DIVISOR
        low = max_quota - 2 * (max_quota // EVICTION_MARGIN_DIVISOR)
    return QuotaInfo(max_quota, source, detail, high, low, free_disk)


def quota_from_payload(payload: dict[str, object]) -> QuotaInfo:
    return QuotaInfo(
        payload.get("max_quota"),  # type: ignore[arg-type]
        str(payload.get("source", "")),
        str(payload.get("detail", "")),
        payload.get("high_watermark"),  # type: ignore[arg-type]
        payload.get("low_watermark"),  # type: ignore[arg-type]
        payload.get("free_disk"),  # type: ignore[arg-type]
    )


def collect_container_snapshot(
    target: ProfileTarget, needle: str | None, quota_override: int | None
) -> Snapshot:
    if target.container is None or target.process_hint is None:
        raise RuntimeError("container target is incomplete")
    override = "" if quota_override is None else str(quota_override)
    raw = checked_output(
        ["docker", "exec", "-i", target.container, "python3", "-", target.process_hint, override],
        input_text=REMOTE_COLLECTOR,
    )
    payload = json.loads(raw)
    entries = payload.get("entries", [])
    visible_entries = [entry for entry in entries if matches_filter(entry, needle)]
    all_summary = summarize(entries)
    visible_summary = summarize(visible_entries)
    cache_data_total = int(payload.get("cache_data_total_bytes", 0))
    return Snapshot(
        input_spec=target.input_spec,
        resolved_from=f"{target.container}:{payload['profile']}",
        profile=Path(payload["profile"]),
        cache_dir=Path(payload["cache_dir"]),
        all_entries=entries,
        visible_entries=visible_entries,
        all_summary=all_summary,
        visible_summary=visible_summary,
        cache_data_total_bytes=cache_data_total,
        cache_data_other_bytes=max(0, cache_data_total - all_summary.raw_bytes),
        quota=quota_from_payload(payload["quota"]),
        filter_text=needle,
        collected_at=time.time(),
    )


def collect_snapshot(target: ProfileTarget, needle: str | None, quota_override: int | None) -> Snapshot:
    if target.container is not None:
        return collect_container_snapshot(target, needle, quota_override)

    if target.host_profile is None:
        raise RuntimeError("host profile path is missing")
    profile = target.host_profile.resolve(strict=False)
    entries = load_entries(profile, target.process_hint)
    visible_entries = [entry for entry in entries if matches_filter(entry, needle)]
    cache_data_total = sum(path.stat().st_size for path in all_cache_files(profile) if path.exists())
    all_summary = summarize(entries)
    visible_summary = summarize(visible_entries)
    return Snapshot(
        input_spec=target.input_spec,
        resolved_from=str(profile),
        profile=profile,
        cache_dir=cache_dir(profile),
        all_entries=entries,
        visible_entries=visible_entries,
        all_summary=all_summary,
        visible_summary=visible_summary,
        cache_data_total_bytes=cache_data_total,
        cache_data_other_bytes=max(0, cache_data_total - all_summary.raw_bytes),
        quota=detect_quota(target, profile, quota_override),
        filter_text=needle,
        collected_at=time.time(),
    )


def decode_preview(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    return text


def hex_preview(data: bytes, width: int = 16) -> str:
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        hex_bytes = " ".join(f"{byte:02x}" for byte in chunk)
        padded_hex = f"{hex_bytes:<{width * 3 - 1}}"
        ascii_text = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        lines.append(f"{offset:08x}  {padded_hex}  {ascii_text}")
    return "\n".join(lines)


def load_entry_payload(target: ProfileTarget, snapshot: Snapshot, entry: dict[str, object]) -> EntryPayload:
    relative_path = str(entry.get("relative_path") or entry["file"])
    if target.container is not None:
        entry_path = snapshot.cache_dir / relative_path
        raw = checked_output(
            ["docker", "exec", "-i", target.container, "python3", "-", str(entry_path)],
            input_text=REMOTE_ENTRY_VIEWER,
        )
        payload = json.loads(raw)
        preview = base64.b64decode(payload["preview_b64"])
        return EntryPayload(
            path=str(payload["path"]),
            size=int(payload["size"]),
            preview_bytes=preview,
            truncated=bool(payload["truncated"]),
        )

    entry_path = snapshot.cache_dir / relative_path
    data = entry_path.read_bytes()
    preview = data[:32768]
    return EntryPayload(
        path=str(entry_path.resolve(strict=False)),
        size=len(data),
        preview_bytes=preview,
        truncated=len(data) > 32768,
    )


def stat_rows(snapshot: Snapshot, exact_bytes: bool = False) -> list[StatRow]:
    all_summary = snapshot.all_summary
    visible = snapshot.visible_summary
    quota = snapshot.quota
    partitions = ", ".join(f"{name}:{count}" for name, count in sorted(all_summary.partitions.items())) or "none"
    used_slots = quota_slots(all_summary.accounted_bytes) or 0
    low_slots = quota_slots(quota.low_watermark)
    high_slots = quota_slots(quota.high_watermark)
    max_slots = quota_slots(quota.max_quota)
    return [
        StatRow("quota", "Quota", fmt_ratio(all_summary.accounted_bytes, quota.max_quota, exact_bytes), "Sum of Chromium-accounted entry sizes against the detected max quota. Uses indexed entry_size when available."),
        StatRow("quota_source", "Quota source", f"{quota.source} [{quota.detail}]", "Where max quota came from: live process switch, Local State pref, or Chromium default-size estimate."),
        StatRow("high", "High watermark", fmt_bytes(quota.high_watermark, exact_bytes), "Eviction starts after usage grows beyond this threshold. Chromium sets it to 95% of max_size."),
        StatRow("low", "Low watermark", fmt_bytes(quota.low_watermark, exact_bytes), "Eviction removes entries until usage falls to this threshold. Chromium sets it to 90% of max_size."),
        StatRow("slot_size", "Slot size", f"{CACHE_ACCOUNTING_SLOT_SIZE} B", "Simple Cache accounting is tracked in 256-byte slots. Indexed entry_size values are multiples of this unit."),
        StatRow("used_slots", "Used slots", str(used_slots), "Current Chromium-accounted cache occupancy expressed in 256-byte slots."),
        StatRow("low_slots", "Low slots", str(low_slots) if low_slots is not None else "?", "Low watermark expressed in 256-byte slots."),
        StatRow("high_slots", "High slots", str(high_slots) if high_slots is not None else "?", "High watermark expressed in 256-byte slots."),
        StatRow("max_slots", "Max slots", str(max_slots) if max_slots is not None else "?", "Configured or estimated max quota expressed in 256-byte slots."),
        StatRow("headroom_high", "Headroom to high", fmt_bytes((quota.high_watermark - all_summary.accounted_bytes) if quota.high_watermark is not None else None, exact_bytes), "Remaining Chromium-accounted bytes before the cache crosses the high watermark."),
        StatRow("headroom_max", "Headroom to max", fmt_bytes((quota.max_quota - all_summary.accounted_bytes) if quota.max_quota is not None else None, exact_bytes), "Remaining Chromium-accounted bytes before the configured or estimated max size."),
        StatRow("fs_free", "Filesystem free", fmt_bytes(quota.free_disk, exact_bytes), "Free bytes on the filesystem backing this profile. Chromium default sizing uses this."),
        StatRow("entries", "Entries", str(all_summary.count), "Number of cache entries, keyed by their stream-0 file (*_0)."),
        StatRow("shown", "Entries shown", str(visible.count), "Number of entries visible after applying the current text filter."),
        StatRow("raw", "Entry raw bytes", fmt_bytes(all_summary.raw_bytes, exact_bytes), "Literal on-disk bytes across all files belonging to the tracked entries (_0, _1, and _s where present)."),
        StatRow("chromium", "Entry Chromium bytes", fmt_bytes(all_summary.chromium_bytes, exact_bytes), "Logical Simple Cache GetDiskUsage-equivalent bytes before 256-byte slot rounding. This can exceed literal entry-file bytes because Chromium accounts each stream separately."),
        StatRow("accounted", "Entry indexed bytes", fmt_bytes(all_summary.accounted_bytes, exact_bytes), "Chromium quota bytes after 256-byte rounding. Uses indexed entry_size when available, otherwise rounds the watcher’s Chromium-byte reconstruction."),
        StatRow("eviction_weight", "Eviction weight", fmt_bytes(all_summary.eviction_weight_bytes, exact_bytes), "Rounded entry bytes plus Chromium's synthetic 512-byte per-entry eviction overhead."),
        StatRow("cache_data_total", "Cache_Data bytes", fmt_bytes(snapshot.cache_data_total_bytes, exact_bytes), "All bytes currently under Cache_Data, including index files and other metadata."),
        StatRow("cache_data_other", "Auxiliary bytes", fmt_bytes(snapshot.cache_data_other_bytes, exact_bytes), "Bytes in Cache_Data that are not part of the tracked entry-file totals, such as index and auxiliary metadata files."),
        StatRow("key_total", "Key bytes total", fmt_bytes(all_summary.total_key_bytes, exact_bytes), "Total serialized cache-key bytes stored in entry headers. Padding attacks change this value directly."),
        StatRow("key_avg", "Key bytes avg", fmt_bytes(int(all_summary.total_key_bytes / all_summary.count) if all_summary.count else 0, exact_bytes), "Average serialized cache-key length across entries."),
        StatRow("key_max", "Key bytes max", fmt_bytes(all_summary.max_key_bytes, exact_bytes), "Largest serialized cache-key length among current entries."),
        StatRow("unique_urls", "Unique URLs", str(all_summary.unique_urls), "Count of distinct final request URLs extracted from Chromium's combined cache keys."),
        StatRow("unique_paths", "Unique paths", str(all_summary.unique_paths), "Count of distinct URL paths currently cached."),
        StatRow("isolation_keys", "Isolation keys", str(all_summary.unique_isolation_keys), "Count of distinct NetworkIsolationKey prefixes, which approximates the number of cache partitions represented."),
        StatRow("partitions", "Partitions", partitions, "_dk_ means partitioned keys. _dk_cn_ is the cross-site main-frame navigation form seen for victim popup navigations."),
        StatRow("largest", "Largest entry", fmt_bytes(all_summary.largest_entry, exact_bytes), "Largest single entry by Chromium-accounted size."),
        StatRow("average", "Average entry", fmt_bytes(all_summary.avg_entry, exact_bytes), "Average Chromium-accounted entry size across all tracked entries."),
        StatRow("visible_bytes", "Shown indexed bytes", fmt_bytes(visible.accounted_bytes, exact_bytes), "Chromium-accounted bytes represented by the currently visible rows."),
    ]


def sort_entries(entries: list[dict[str, object]], sort_key: str) -> list[dict[str, object]]:
    def metric(entry: dict[str, object], key: str) -> int:
        value = entry.get(key)
        if value is None:
            return -1
        return int(value)

    return sorted(
        entries,
        key=lambda entry: (metric(entry, sort_key), metric(entry, "accounted"), str(entry["file"])),
        reverse=True,
    )


def build_summary(
    snapshot: Snapshot,
    sort_label: str,
    show_legend: bool,
    exact_bytes: bool,
    frozen: bool = False,
) -> str:
    return "\n".join(
        [
        f"{accent('Input')}: {escape_markup(snapshot.input_spec)}",
        f"{accent('Resolved path')}: {escape_markup(snapshot.resolved_from)}",
        f"{accent('Filter')}: {escape_markup(snapshot.filter_text or '(none)')}",
        f"{accent('Sort')}: {escape_markup(sort_label)}",
            f"{accent('Bytes')}: {escape_markup('exact' if exact_bytes else 'human')} {subtle('(b to toggle)')}",
            f"{accent('Refresh')}: {escape_markup('frozen' if frozen else 'live')} {subtle('(f to toggle)')}",
            f"{accent('Updated')}: {escape_markup(time.strftime('%H:%M:%S', time.localtime(snapshot.collected_at)))}",
            f"{accent('Legend')}: {escape_markup('shown' if show_legend else 'hidden')} {subtle('(? to toggle)')}",
        ]
    )


def slot_char(index: int, used_slots: int, low_slots: int, high_slots: int) -> str:
    used = index < used_slots
    if index < low_slots:
        return "[green]█[/]" if used else "[green]░[/]"
    if index < high_slots:
        return "[yellow]█[/]" if used else "[yellow]░[/]"
    return "[red]█[/]" if used else "[bright_black]░[/]"


def marker_row_for_range(start: int, end: int, used_slots: int, low_slots: int, high_slots: int, total_slots: int) -> str:
    markers = [" " for _ in range(max(0, end - start))]

    def place(slot: int, char: str) -> None:
        if start <= slot < end:
            pos = slot - start
            markers[pos] = char if markers[pos] == " " else "*"

    if used_slots > 0:
        place(min(total_slots - 1, used_slots - 1), "U")
    if low_slots < total_slots:
        place(low_slots, "L")
    if high_slots < total_slots:
        place(high_slots, "H")
    place(total_slots - 1, "M")
    return "".join(markers)


def merge_slot_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted((max(0, s), max(0, e)) for s, e in windows if e > s):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def quota_detail_windows(total_slots: int, used_slots: int, low_slots: int, high_slots: int, row_slots: int) -> list[tuple[int, int, str]]:
    span = row_slots * 6
    half = span // 2
    windows = [
        (0, min(total_slots, span), "Start"),
        (max(0, used_slots - half), min(total_slots, used_slots + half), "Around usage edge"),
        (max(0, low_slots - half), min(total_slots, low_slots + half), "Around low watermark"),
        (max(0, high_slots - half), min(total_slots, high_slots + half), "Around high watermark"),
        (max(0, total_slots - span), total_slots, "End"),
    ]
    merged = merge_slot_windows([(start, end) for start, end, _label in windows])
    label_map: dict[tuple[int, int], list[str]] = {}
    for start, end, label in windows:
        norm = None
        for merged_start, merged_end in merged:
            if merged_start <= start and end <= merged_end:
                norm = (merged_start, merged_end)
                break
        if norm is None:
            continue
        label_map.setdefault(norm, []).append(label)
    return [(start, end, " + ".join(label_map.get((start, end), ["Window"]))) for start, end in merged]


def build_quota_detail_popup(snapshot: Snapshot, exact_bytes: bool = False, row_slots: int = 96) -> str:
    quota = snapshot.quota
    total_slots = quota_slots(quota.max_quota)
    if not total_slots:
        return "\n".join(
            [
                accent("Detailed Quota View"),
                subtle("Quota unavailable for this profile."),
            ]
        )

    used_slots = min(total_slots, quota_slots(snapshot.all_summary.accounted_bytes) or 0)
    low_slots = min(total_slots, quota_slots(quota.low_watermark) or 0)
    high_slots = min(total_slots, quota_slots(quota.high_watermark) or 0)
    windows = quota_detail_windows(total_slots, used_slots, low_slots, high_slots, row_slots)

    lines = [
        accent("Detailed Quota View"),
        f"{accent('Bytes')} : used={escape_markup(fmt_bytes(snapshot.all_summary.accounted_bytes, exact_bytes))}  low={escape_markup(fmt_bytes(quota.low_watermark, exact_bytes))}  high={escape_markup(fmt_bytes(quota.high_watermark, exact_bytes))}  max={escape_markup(fmt_bytes(quota.max_quota, exact_bytes))}",
        f"{accent('Slots')} : used={escape_markup(str(used_slots))}  low={escape_markup(str(low_slots))}  high={escape_markup(str(high_slots))}  max={escape_markup(str(total_slots))}",
        f"{accent('Keys')} : {escape_markup('i range inspector, q close')}",
        f"{accent('Legend')}: [green]█[/] used below low  [green]░[/] free below low  [yellow]█[/]/[yellow]░[/] low..high band  [red]█[/]/[bright_black]░[/] above high  {accent('U')} usage edge  {accent('L')} low  {accent('H')} high  {accent('M')} max",
        "",
    ]

    for start, end, label in windows:
        lines.append(f"{accent(label)}: slots {start}..{max(start, end - 1)}")
        for row_start in range(start, end, row_slots):
            row_end = min(end, row_start + row_slots)
            slot_line = "".join(
                slot_char(index, used_slots, low_slots, high_slots)
                for index in range(row_start, row_end)
            )
            marker_line = marker_row_for_range(row_start, row_end, used_slots, low_slots, high_slots, total_slots)
            lines.append(
                f"{accent(str(row_start).rjust(9))} {slot_line} {accent(str(row_end - 1).rjust(9))}"
            )
            if marker_line.strip():
                lines.append(f"{subtle(' ' * 10)}{escape_markup(marker_line)}")
        lines.append("")

    return "\n".join(lines).rstrip()


def clamp_slot_start(start_slot: int, total_slots: int, page_slots: int) -> int:
    if total_slots <= 0:
        return 0
    max_start = max(0, total_slots - max(1, page_slots))
    return max(0, min(start_slot, max_start))


def slot_window_bytes(start_slot: int, end_slot: int) -> tuple[int, int]:
    return start_slot * CACHE_ACCOUNTING_SLOT_SIZE, end_slot * CACHE_ACCOUNTING_SLOT_SIZE


def logical_slot_layout(snapshot: Snapshot) -> list[LogicalSlotSpan]:
    def sort_key(entry: dict[str, object]) -> tuple[int, int, int, str]:
        score = int(entry["eviction_score"]) if entry.get("eviction_score") is not None else -1
        age = int(entry["age_seconds"]) if entry.get("age_seconds") is not None else -1
        return (score, age, int(entry["accounted"]), str(entry["file"]))

    cursor = 0
    spans: list[LogicalSlotSpan] = []
    for ordinal, entry in enumerate(sorted(snapshot.all_entries, key=sort_key, reverse=True), start=1):
        span_slots = max(1, quota_slots(int(entry["accounted"])) or 0)
        spans.append(
            LogicalSlotSpan(
                ordinal=ordinal,
                start_slot=cursor,
                end_slot=cursor + span_slots,
                entry=entry,
            )
        )
        cursor += span_slots
    return spans


def slot_owner(spans: list[LogicalSlotSpan], slot: int) -> LogicalSlotSpan | None:
    if slot < 0:
        return None
    for span in spans:
        if span.start_slot <= slot < span.end_slot:
            return span
    return None


def slot_boundary_sets(spans: list[LogicalSlotSpan]) -> tuple[set[int], set[int]]:
    starts = {span.start_slot for span in spans}
    ends = {span.end_slot - 1 for span in spans if span.end_slot > span.start_slot}
    return starts, ends


def usage_next_event_summary(used_slots: int, low_slots: int, high_slots: int, total_slots: int, exact_bytes: bool = False) -> str:
    def event_text(label: str, distance_slots: int) -> str:
        return f"{label} in {distance_slots} slots ({fmt_bytes(distance_slots * CACHE_ACCOUNTING_SLOT_SIZE, exact_bytes)})"

    if used_slots < low_slots:
        return event_text("low", low_slots - used_slots)
    if used_slots < high_slots:
        return event_text("high", high_slots - used_slots)
    if used_slots < total_slots:
        return event_text("max", total_slots - used_slots)
    return "at max quota"


def slot_marker_codes(
    slot: int,
    used_slots: int,
    low_slots: int,
    high_slots: int,
    total_slots: int,
    entry_starts: set[int],
    entry_ends: set[int],
    selected_slot: int | None = None,
) -> list[str]:
    codes: list[str] = []
    if selected_slot is not None and slot == selected_slot:
        codes.append("@")
    if used_slots > 0 and slot == min(total_slots - 1, used_slots - 1):
        codes.append("U")
    if slot == low_slots and low_slots < total_slots:
        codes.append("L")
    if slot == high_slots and high_slots < total_slots:
        codes.append("H")
    if total_slots > 0 and slot == total_slots - 1:
        codes.append("M")
    if slot in entry_starts:
        codes.append("S")
    if slot in entry_ends:
        codes.append("E")
    return codes


def quota_grid_slots_per_row(visible_slots: int, available_height: int | None = None) -> int:
    del available_height
    return max(1, min(DEFAULT_QUOTA_RANGE_SLOTS_PER_ROW, visible_slots))


def build_quota_range_info(
    snapshot: Snapshot,
    start_slot: int,
    visible_slots: int = 64,
    exact_bytes: bool = False,
    slots_per_row: int | None = None,
    selected_slot: int | None = None,
) -> str:
    quota = snapshot.quota
    total_slots = quota_slots(quota.max_quota)
    if not total_slots:
        return "\n".join(
            [
                accent("Slot Range Inspector"),
                subtle("Quota unavailable for this profile."),
            ]
        )

    visible_slots = max(8, visible_slots)
    start_slot = clamp_slot_start(start_slot, total_slots, visible_slots)
    end_slot = min(total_slots, start_slot + visible_slots)
    slots_per_row = max(1, min(slots_per_row or quota_grid_slots_per_row(visible_slots), visible_slots))
    row_count = (visible_slots + slots_per_row - 1) // slots_per_row

    used_slots = min(total_slots, quota_slots(snapshot.all_summary.accounted_bytes) or 0)
    low_slots = min(total_slots, quota_slots(quota.low_watermark) or 0)
    high_slots = min(total_slots, quota_slots(quota.high_watermark) or 0)
    window_start_bytes, window_end_bytes = slot_window_bytes(start_slot, end_slot)
    next_event = usage_next_event_summary(used_slots, low_slots, high_slots, total_slots, exact_bytes)

    info_lines = [
        accent("Slot Range Inspector"),
        f"{accent('Visible slots')}: {escape_markup(str(start_slot))}..{escape_markup(str(max(start_slot, end_slot - 1)))} {subtle(f'({end_slot - start_slot} slots)')}",
        f"{accent('Visible bytes')}: {escape_markup(fmt_bytes(window_start_bytes, exact_bytes))}..{escape_markup(fmt_bytes(window_end_bytes, exact_bytes))}",
        f"{accent('Layout')}: {escape_markup(f'{row_count} rows x {slots_per_row} slots/row')} {subtle('(boxed slot grid with lateral padding)')}",
        f"{accent('Selection')}: {escape_markup(str(selected_slot if selected_slot is not None else start_slot))} {subtle('(a/d move, w/s row jump)')}",
        f"{accent('Controls')}: {escape_markup('left/right shift window, up/down shift page, a/d select, w/s row jump, [ zoom in, ] zoom out, 0 start, u usage, l low, h high, m end, ? help, q close')}",
        f"{accent('Next event')}: {escape_markup(next_event)}",
        f"{accent('Box semantics')}: {escape_markup('border = quota band, fill = used/free, top codes = @ U L H M S E, inner tick = guide, cyan border = selected')}",
        f"{accent('Layout note')}: {escape_markup('entry markers use logical packing by eviction score, not physical disk offsets')}",
        f"{accent('Legend')}: [green]█[/] used<low  [green]░[/] free<low  [yellow]█[/]/[yellow]░[/] low..high  [red]█[/]/[bright_black]░[/] >high  {accent('@')} selected  {accent('U/L/H/M')} thresholds  {accent('S/E')} logical entry start/end",
    ]
    return "\n".join(info_lines)


def slot_marker_text(markers: list[str]) -> str:
    return " ".join(markers[:4]).center(11)


def slot_border_markup(slot: int, used_slots: int, low_slots: int, high_slots: int, selected: bool = False) -> str:
    if selected:
        return "bold bright_cyan"
    if slot < low_slots:
        return "green"
    if slot < high_slots:
        return "yellow"
    return "red" if slot < used_slots else "grey35"


def slot_fill_markup(slot: int, used_slots: int, low_slots: int, high_slots: int) -> str:
    used = slot < used_slots
    if slot < low_slots:
        return "black on green" if used else "green on rgb(12,26,26)"
    if slot < high_slots:
        return "black on yellow" if used else "yellow on rgb(20,20,10)"
    return "white on red" if used else "grey50 on rgb(18,18,18)"


def slot_guide_markup(
    slot: int,
    used_slots: int,
    low_slots: int,
    high_slots: int,
    total_slots: int,
    entry_starts: set[int],
    entry_ends: set[int],
    selected_slot: int | None = None,
) -> tuple[str | None, str | None]:
    if selected_slot is not None and slot == selected_slot:
        return "bold bright_cyan", "┃"
    if used_slots > 0 and slot == min(total_slots - 1, used_slots - 1):
        return "bold bright_cyan", "│"
    if slot == low_slots and low_slots < total_slots:
        return "bold green", "│"
    if slot == high_slots and high_slots < total_slots:
        return "bold yellow", "│"
    if total_slots > 0 and slot == total_slots - 1:
        return "bold red", "│"
    if slot in entry_starts or slot in entry_ends:
        return "grey70", "┆"
    return None, None


def slot_label_text(slot: int) -> str:
    text = str(slot)
    if len(text) > 7:
        text = text[-7:]
    return text.center(9)


def slot_inner_text(
    fill: str,
    guide_style: str | None,
    guide_char: str | None,
    width: int = 9,
) -> str:
    if not guide_style or not guide_char:
        return f"[{fill}]{' ' * width}[/]"
    left = width // 2
    right = width - left - 1
    return f"[{fill}]{' ' * left}[/][{guide_style}]{guide_char}[/][{fill}]{' ' * right}[/]"


def slot_band_name(slot: int, used_slots: int, low_slots: int, high_slots: int) -> str:
    if slot >= used_slots:
        if slot < low_slots:
            return "free below low"
        if slot < high_slots:
            return "free in low..high band"
        return "free above high"
    if slot < low_slots:
        return "used below low"
    if slot < high_slots:
        return "used in low..high band"
    return "used above high"


def build_quota_range_grid(
    snapshot: Snapshot,
    start_slot: int,
    visible_slots: int = 16,
    exact_bytes: bool = False,
    slots_per_row: int | None = None,
    selected_slot: int | None = None,
) -> str:
    quota = snapshot.quota
    total_slots = quota_slots(quota.max_quota)
    if not total_slots:
        return subtle("Quota unavailable.")

    visible_slots = max(1, visible_slots)
    start_slot = clamp_slot_start(start_slot, total_slots, visible_slots)
    end_slot = min(total_slots, start_slot + visible_slots)
    used_slots = min(total_slots, quota_slots(snapshot.all_summary.accounted_bytes) or 0)
    low_slots = min(total_slots, quota_slots(quota.low_watermark) or 0)
    high_slots = min(total_slots, quota_slots(quota.high_watermark) or 0)
    slots_per_row = max(1, min(slots_per_row or quota_grid_slots_per_row(visible_slots), visible_slots))
    left_pad = "    "
    spans = logical_slot_layout(snapshot)
    entry_starts, entry_ends = slot_boundary_sets(spans)

    lines: list[str] = []
    for row_index, row_start in enumerate(range(start_slot, end_slot, slots_per_row), start=1):
        row_end = min(end_slot, row_start + slots_per_row)
        row_start_bytes, row_end_bytes = slot_window_bytes(row_start, row_end)
        marker_cells = []
        top_cells = []
        upper_cells = []
        label_cells = []
        lower_cells = []
        bottom_cells = []
        lines.append(
            left_pad
            + f"{accent(f'Row {row_index:02d}')}  "
            + f"{accent('Slots')}: {escape_markup(str(row_start))}..{escape_markup(str(row_end - 1))}  "
            + f"{accent('Bytes')}: {escape_markup(fmt_bytes(row_start_bytes, exact_bytes))}..{escape_markup(fmt_bytes(row_end_bytes, exact_bytes))}"
        )
        for slot in range(row_start, row_end):
            selected = selected_slot is not None and slot == selected_slot
            border = slot_border_markup(slot, used_slots, low_slots, high_slots, selected=selected)
            fill = slot_fill_markup(slot, used_slots, low_slots, high_slots)
            marker = slot_marker_text(
                slot_marker_codes(
                    slot,
                    used_slots,
                    low_slots,
                    high_slots,
                    total_slots,
                    entry_starts,
                    entry_ends,
                    selected_slot,
                )
            )
            guide_style, guide_char = slot_guide_markup(
                slot,
                used_slots,
                low_slots,
                high_slots,
                total_slots,
                entry_starts,
                entry_ends,
                selected_slot,
            )
            label = slot_label_text(slot)
            marker_cells.append(f"[bold bright_cyan]{escape_markup(marker)}[/]")
            top_cells.append(f"[{border}]╭─────────╮[/]")
            upper_cells.append(f"[{border}]│[/]{slot_inner_text(fill, guide_style, guide_char)}[{border}]│[/]")
            label_cells.append(f"[{border}]│[/][{fill}]{escape_markup(label)}[/][{border}]│[/]")
            lower_cells.append(f"[{border}]│[/]{slot_inner_text(fill, guide_style, guide_char)}[{border}]│[/]")
            bottom_cells.append(f"[{border}]╰─────────╯[/]")
        lines.append(left_pad + "  ".join(marker_cells))
        lines.append(left_pad + "  ".join(top_cells))
        lines.append(left_pad + "  ".join(upper_cells))
        lines.append(left_pad + "  ".join(label_cells))
        lines.append(left_pad + "  ".join(lower_cells))
        lines.append(left_pad + "  ".join(bottom_cells))
        lines.append("")

    window_start_bytes, window_end_bytes = slot_window_bytes(start_slot, end_slot)
    footer = [
        f"{accent('Range bytes')}: {escape_markup(fmt_bytes(window_start_bytes, exact_bytes))}..{escape_markup(fmt_bytes(window_end_bytes, exact_bytes))}",
        f"{accent('Rows')}: {escape_markup(str((visible_slots + slots_per_row - 1) // slots_per_row))} {subtle(f'({slots_per_row} slots/row)')}",
        f"{accent('Next event')}: {escape_markup(usage_next_event_summary(used_slots, low_slots, high_slots, total_slots, exact_bytes))}",
    ]
    return "\n".join(lines + footer).rstrip()


def build_quota_range_slot_details(
    snapshot: Snapshot,
    selected_slot: int,
    exact_bytes: bool = False,
) -> str:
    quota = snapshot.quota
    total_slots = quota_slots(quota.max_quota)
    if not total_slots:
        return "\n".join([accent("Selected Slot"), subtle("Quota unavailable.")])

    selected_slot = max(0, min(selected_slot, total_slots - 1))
    used_slots = min(total_slots, quota_slots(snapshot.all_summary.accounted_bytes) or 0)
    low_slots = min(total_slots, quota_slots(quota.low_watermark) or 0)
    high_slots = min(total_slots, quota_slots(quota.high_watermark) or 0)
    spans = logical_slot_layout(snapshot)
    entry_starts, entry_ends = slot_boundary_sets(spans)
    owner = slot_owner(spans, selected_slot)
    slot_start_bytes, slot_end_bytes = slot_window_bytes(selected_slot, selected_slot + 1)
    marker_codes = slot_marker_codes(
        selected_slot,
        used_slots,
        low_slots,
        high_slots,
        total_slots,
        entry_starts,
        entry_ends,
        selected_slot,
    )
    lines = [
        accent("Selected Slot Details"),
        f"{accent('Slot')}: {escape_markup(str(selected_slot))}  {accent('Bytes')}: {escape_markup(fmt_bytes(slot_start_bytes, exact_bytes))}..{escape_markup(fmt_bytes(slot_end_bytes, exact_bytes))}",
        f"{accent('State')}: {escape_markup(slot_band_name(selected_slot, used_slots, low_slots, high_slots))}",
        f"{accent('Markers here')}: {escape_markup(' '.join(marker_codes) if marker_codes else '(none)')}",
        f"{accent('Next quota event')}: {escape_markup(usage_next_event_summary(used_slots, low_slots, high_slots, total_slots, exact_bytes))}",
    ]

    if owner is None or selected_slot >= used_slots:
        lines.extend(
            [
                f"{accent('Logical owner')}: {escape_markup('none (free headroom slot)')}",
                f"{accent('Semantics')}: {escape_markup('entry markers use logical packing by eviction score, not physical disk offsets')}",
            ]
        )
        return "\n".join(lines)

    entry = owner.entry
    span_slots = owner.end_slot - owner.start_slot
    slots_to_end = owner.end_slot - selected_slot - 1
    lines.extend(
        [
            f"{accent('Logical owner')}: #{owner.ordinal} {escape_markup(str(entry['file']))}",
            f"{accent('Entry span')}: {escape_markup(str(owner.start_slot))}..{escape_markup(str(owner.end_slot - 1))} {subtle(f'({span_slots} slots, {fmt_bytes(span_slots * CACHE_ACCOUNTING_SLOT_SIZE, exact_bytes)})')}",
            f"{accent('Entry edge distance')}: {escape_markup(f'end in {slots_to_end} slots')}",
            f"{accent('Partition')}: {escape_markup(str(entry['partition']))}  {accent('Indexed bytes')}: {escape_markup(fmt_bytes(int(entry['accounted']), exact_bytes))}",
            f"{accent('URL')}: {escape_markup(str(entry['url'] or '-'))}",
            f"{accent('Semantics')}: {escape_markup('border = quota band, fill = used/free, @ = selected, U/L/H/M = thresholds, S/E = logical entry start/end, center tick = vertical guide')}",
        ]
    )
    return "\n".join(lines)


def build_quota_range_help_popup() -> str:
    sections = [
        (
            "What This View Shows",
            [
                "The inspector is a logical slot map of Chromium HTTP cache accounting, where each slot is 256 bytes.",
                "It is not a physical disk-sector or on-disk file offset viewer. It is a quota-oriented visualization.",
                "Slots are packed from the current cache entries using each entry's accounted size, so the view is useful for reasoning about quota pressure, thresholds, and entry spans.",
            ],
        ),
        (
            "Rows And Captions",
            [
                "Each grid row shows its own slot range and byte range.",
                "The row caption tells you exactly which logical slots are visible on that row and what byte interval they represent.",
                "The footer shows the full visible byte span, row count, and the next quota event.",
            ],
        ),
        (
            "Box Semantics",
            [
                "Border color tells you which quota band the slot belongs to.",
                "Fill color tells you whether the slot is currently considered used or free.",
                "Cyan border marks the currently selected slot.",
                "The inner vertical tick is a guide marker. It appears for thresholds, selection, and logical entry boundaries.",
            ],
        ),
        (
            "Color Meaning",
            [
                "Green: below the low watermark.",
                "Yellow: between low and high watermarks.",
                "Red border or fill: above the high watermark, or used space beyond it.",
                "Grey or dim styling: free space in the above-high region.",
            ],
        ),
        (
            "Top Marker Codes",
            [
                "@ means the currently selected slot.",
                "U marks the current used edge.",
                "L marks the low watermark.",
                "H marks the high watermark.",
                "M marks the max quota edge.",
                "S marks a logical entry start.",
                "E marks a logical entry end.",
                "Multiple codes can appear on the same slot if boundaries coincide.",
            ],
        ),
        (
            "Selected Slot Details",
            [
                "The bottom pane explains the currently selected slot in detail.",
                "If the slot belongs to logical used space, the pane shows the logical owner entry, its span, partition, indexed bytes, and URL.",
                "If the slot is free headroom, the pane tells you there is no logical owner.",
            ],
        ),
        (
            "Logical Entry Boundaries",
            [
                "S and E markers are derived from a logical packing of entries, not from physical disk offsets.",
                "Entries are packed by the same ordering the watcher uses for logical inspection, so the grid can show where large entries begin and end.",
                "This makes fragmentation and entry spans easier to reason about, even though it is not a byte-for-byte physical disk map.",
            ],
        ),
        (
            "Next Event",
            [
                "The next-event line tells you how much headroom remains until the next important quota threshold.",
                "Below low, it reports distance to low.",
                "Between low and high, it reports distance to high.",
                "Above high, it reports distance to max.",
            ],
        ),
        (
            "Controls",
            [
                "left/right: shift the visible window by one slot.",
                "up/down: shift the visible window by one full page.",
                "a/d: move the selected slot left or right.",
                "w/s: move the selected slot by one row.",
                "[ and ]: zoom in or out by changing the visible slot count.",
                "0: jump to the start of the quota.",
                "u/l/h/m: jump near used, low, high, or max.",
                "?: open or close this help popup.",
            ],
        ),
    ]

    lines = [accent("Inspector Help"), subtle("Scroll this popup if the content does not fit."), ""]
    for title, bullets in sections:
        lines.append(accent(title))
        for bullet in bullets:
            lines.append(f"- {escape_markup(bullet)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_stats_text(rows: list[StatRow]) -> str:
    width = max((len(row.label) for row in rows), default=0)
    return "\n".join(
        f"{accent(row.label.ljust(width))} : {escape_markup(row.value)}" for row in rows
    )


def stats_panel_width(rows: list[StatRow]) -> int:
    label_width = max((len(row.label) for row in rows), default=0)
    line_width = max(
        (len(f"{row.label.ljust(label_width)} : {row.value}") for row in rows),
        default=0,
    )
    return max(54, min(96, line_width + 4))


def build_legend(rows: list[StatRow]) -> str:
    blocks = []
    for row in rows:
        blocks.append(
            "\n".join(
                [
                    accent(row.label),
                    f"{accent('Current value')}: {escape_markup(row.value)}",
                    escape_markup(row.description),
                ]
            )
        )
    return "\n\n".join(blocks)


def build_details(
    snapshot: Snapshot,
    entries: list[dict[str, object]],
    sort_label: str,
    row: int | None,
    exact_bytes: bool = False,
) -> str:
    lines = [
        f"{accent('Cache dir')}: {escape_markup(snapshot.cache_dir)}",
        f"{accent('Rows visible')}: {escape_markup(len(entries))}",
        f"{accent('Sort')}: {escape_markup(sort_label)}",
        f"{accent('Keys')}: {escape_markup('q quit, r refresh, s cycle sort, b bytes, f freeze, v quota view')}",
        "",
    ]
    if not entries:
        lines.append(subtle("No entries matched the current filter."))
        return "\n".join(lines)

    index = 0 if row is None else max(0, min(row, len(entries) - 1))
    entry = entries[index]
    lines.extend(
        [
            f"{accent('Selected row')}: {escape_markup(f'{index + 1}/{len(entries)}')}",
            f"{accent('File')}: {escape_markup(entry['file'])}",
            f"{accent('Partition')}: {escape_markup(entry['partition'])}",
            f"{accent('Isolation key')}: {escape_markup(entry['isolation_key'] or '-')}",
            f"{accent('Indexed / Chromium / files / _0')}: {escape_markup(fmt_bytes(int(entry['accounted']), exact_bytes))} / {escape_markup(fmt_bytes(int(entry['chromium_size']), exact_bytes))} / {escape_markup(fmt_bytes(int(entry['size']), exact_bytes))} / {escape_markup(fmt_bytes(int(entry['file0_size']), exact_bytes))}",
            f"{accent('Quota slack / logical overhead')}: {escape_markup(fmt_bytes(int(entry['slack']), exact_bytes))} / {escape_markup(fmt_bytes(int(entry['logical_overhead']), exact_bytes))}",
            f"{accent('Accounted source / Chromium source')}: {escape_markup(str(entry['accounted_source']))} / {escape_markup(str(entry['chromium_size_source']))}",
            f"{accent('Eviction weight')}: {escape_markup(fmt_bytes(int(entry['eviction_weight']), exact_bytes))}",
            f"{accent('Eviction score')}: {escape_markup(str(entry['eviction_score']) if entry['eviction_score'] is not None else '-')}",
            f"{accent('Last used')}: {escape_markup(fmt_mtime(entry['last_used_epoch']))}",
            f"{accent('Age')}: {escape_markup(fmt_age(entry['age_seconds']))}",
            f"{accent('Hint bits')}: {escape_markup(hex(int(entry['in_memory_data'])))}",
            f"{accent('High priority')}: {escape_markup('yes' if entry['high_priority'] else 'no')}",
            f"{accent('Metadata source')}: {escape_markup(entry['metadata_source'])}",
            f"{accent('Key bytes')}: {escape_markup(fmt_bytes(int(entry['key_length']), exact_bytes))}",
            f"{accent('URL')}: {escape_markup(entry['url'] or '-')}",
            f"{accent('Cache key')}: {escape_markup(entry['key'] or '-')}",
        ]
    )
    return "\n".join(lines)


def build_entry_popup(
    entry: dict[str, object],
    payload: EntryPayload,
    exact_bytes: bool = False,
) -> str:
    preview = decode_preview(payload.preview_bytes)
    lines = [
        f"{accent('File')}: {escape_markup(entry['file'])}",
        f"{accent('Path')}: {escape_markup(payload.path)}",
        f"{accent('Partition')}: {escape_markup(entry['partition'])}",
        f"{accent('Isolation key')}: {escape_markup(entry['isolation_key'] or '-')}",
        f"{accent('URL')}: {escape_markup(entry['url'] or '-')}",
        f"{accent('Cache key')}: {escape_markup(entry['key'] or '-')}",
        f"{accent('Raw bytes')}: {escape_markup(fmt_bytes(payload.size, exact_bytes))}",
        f"{accent('Eviction score')}: {escape_markup(str(entry['eviction_score']) if entry['eviction_score'] is not None else '-')}",
        f"{accent('Last used')}: {escape_markup(fmt_mtime(entry['last_used_epoch']))} {subtle('(' + fmt_age(entry['age_seconds']) + ')')}",
        f"{accent('View')}: {escape_markup('text only')} {subtle('(x to toggle split hex view)')}",
        "",
        accent("Content preview"),
        escape_markup(preview),
    ]
    if payload.truncated:
        lines.extend(["", subtle("[truncated to first 32768 bytes]")])
    return "\n".join(lines)


def build_entry_hex_popup(payload: EntryPayload) -> str:
    lines = [
        f"{accent('Hex dump')}: {subtle('(x to hide)')}",
        "",
        escape_markup(hex_preview(payload.preview_bytes)),
    ]
    if payload.truncated:
        lines.extend(["", subtle("[truncated to first 32768 bytes]")])
    return "\n".join(lines)


def rich_markup(text: str) -> Text:
    return Text.from_markup(text)


def print_once(
    snapshot: Snapshot,
    rows: list[StatRow],
    entries: list[dict[str, object]],
    limit: int,
    sort_label: str,
    exact_bytes: bool = False,
) -> None:
    print(f"input: {snapshot.input_spec}")
    print(f"resolved_path: {snapshot.resolved_from}")
    print(f"cache_dir: {snapshot.cache_dir}")
    print(f"sort: {sort_label}")
    print(f"bytes: {'exact' if exact_bytes else 'human'}")
    quota_map = render_quota_bar(snapshot.all_summary.accounted_bytes, snapshot.quota)
    if quota_map is not None:
        bar, scale = quota_map
        print(f"quota_map: {bar}")
        print(f"quota_slots: {scale}")
    for row in rows:
        print(f"{row.label}: {row.value}")
    print()
    for entry in entries[:limit]:
        print(json.dumps(entry, sort_keys=True))


if TEXTUAL_IMPORT_ERROR is None:  # pragma: no branch
    class ProfilePicker(ModalScreen[str | None]):
        CSS = """
        ProfilePicker {
            align: center middle;
        }
        #picker_popup {
            width: 82%;
            height: 82%;
            border: round $accent;
            background: $surface;
        }
        #picker_title {
            height: 5;
            padding: 0 1;
            border-bottom: solid $accent;
        }
        #picker_table {
            height: 1fr;
        }
        """

        BINDINGS = [
            Binding("enter", "open", "Open"),
            Binding("backspace", "up", "Up"),
            Binding("left", "up", "Up"),
            Binding("escape", "cancel", "Cancel"),
            Binding("q", "cancel", "Cancel"),
        ]

        def __init__(self, target: ProfileTarget) -> None:
            super().__init__()
            self.target = target
            self.current_path = str(target.process_hint or "/") if target.container else str(target.host_profile or Path.cwd())
            self.row_actions: list[dict[str, str]] = []
            self.refresh_timer = None

        def compose(self) -> ComposeResult:
            with Vertical(id="picker_popup"):
                yield Static("", id="picker_title")
                yield DataTable(id="picker_table")

        def on_mount(self) -> None:
            table = self.query_one("#picker_table", DataTable)
            table.cursor_type = "row"
            table.zebra_stripes = True
            self.load_current()
            table.focus()
            self.refresh_timer = self.set_interval(1.0, self.load_current)

        def selected_action_key(self) -> tuple[str, str] | None:
            table = self.query_one("#picker_table", DataTable)
            row = getattr(table, "cursor_row", None)
            if row is None or not (0 <= row < len(self.row_actions)):
                return None
            action = self.row_actions[row]
            return action["kind"], action["path"]

        def refresh_title(self, state: DirectoryState) -> None:
            target_kind = "container" if self.target.container else "host"
            lines = [
                accent("Profile Picker"),
                f"{accent('Target')}: {escape_markup(target_kind)}",
                f"{accent('Path')}: {escape_markup(state.current_path)}",
                f"{accent('Keys')}: {escape_markup('enter open/select, backspace up, q cancel, auto-refresh 1s')}",
            ]
            if state.is_profile:
                lines.append(subtle("This directory is a valid Chrome user-data-dir root."))
            self.query_one("#picker_title", Static).update(rich_markup("\n".join(lines)))

        def load_current(self) -> None:
            selected_key = self.selected_action_key()
            state = inspect_directory(self.target, self.current_path)
            self.current_path = state.current_path
            self.refresh_title(state)
            table = self.query_one("#picker_table", DataTable)
            table.clear(columns=True)
            table.add_columns("Type", "Name", "Profile", "Modified")
            self.row_actions = []
            if state.is_profile:
                self.row_actions.append({"kind": "select", "path": state.current_path})
                table.add_row("profile", ".", "yes", "-")
            if state.parent_path:
                self.row_actions.append({"kind": "up", "path": state.parent_path})
                table.add_row("dir", "..", "", "-")
            for entry in state.entries:
                self.row_actions.append(
                    {
                        "kind": "select" if entry.is_profile else "dir",
                        "path": entry.path,
                    }
                )
                table.add_row(
                    "profile" if entry.is_profile else "dir",
                    entry.name,
                    "yes" if entry.is_profile else "",
                    fmt_mtime(entry.mtime),
                )
            if self.row_actions:
                selected_row = 0
                if selected_key is not None:
                    for row_index, action in enumerate(self.row_actions):
                        if (action["kind"], action["path"]) == selected_key:
                            selected_row = row_index
                            break
                table.move_cursor(row=selected_row, animate=False)

        def current_action(self) -> dict[str, str] | None:
            table = self.query_one("#picker_table", DataTable)
            row = getattr(table, "cursor_row", None)
            if row is None or not (0 <= row < len(self.row_actions)):
                return None
            return self.row_actions[row]

        def action_open(self) -> None:
            action = self.current_action()
            if not action:
                return
            if action["kind"] == "select":
                self.dismiss(action["path"])
                return
            self.current_path = action["path"]
            self.load_current()

        def action_up(self) -> None:
            state = inspect_directory(self.target, self.current_path)
            if state.parent_path:
                self.current_path = state.parent_path
                self.load_current()

        def action_cancel(self) -> None:
            self.dismiss(None)

        def on_data_table_row_selected(self, event) -> None:  # pragma: no cover - UI callback
            if getattr(event.data_table, "id", None) != "picker_table":
                return
            self.action_open()

    class EntryViewer(ModalScreen[None]):
        CSS = """
        EntryViewer {
            align: center middle;
        }
        #entry_popup {
            width: 88%;
            height: 88%;
            border: round $accent;
            background: $surface;
        }
        #entry_popup_title {
            height: 3;
            padding: 0 1;
            border-bottom: solid $accent;
        }
        #entry_popup_body {
            height: 1fr;
        }
        #entry_text_pane {
            width: 3fr;
            border-right: solid $accent;
            padding: 0 1;
        }
        #entry_hex_pane {
            width: 2fr;
            padding: 0 1;
            display: none;
        }
        """

        BINDINGS = [
            Binding("x", "toggle_hex", "Hex"),
            Binding("escape", "close", "Close"),
            Binding("enter", "close", "Close"),
            Binding("q", "close", "Close"),
        ]

        def __init__(self, entry: dict[str, object], payload: EntryPayload, exact_bytes: bool) -> None:
            super().__init__()
            self.entry = entry
            self.payload = payload
            self.exact_bytes = exact_bytes
            self.hex_mode = False

        def compose(self) -> ComposeResult:
            with Vertical(id="entry_popup"):
                yield Static("", id="entry_popup_title")
                with Horizontal(id="entry_popup_body"):
                    with VerticalScroll(id="entry_text_pane"):
                        yield Static("", id="entry_popup_text")
                    with VerticalScroll(id="entry_hex_pane"):
                        yield Static("", id="entry_popup_hex")

        def on_mount(self) -> None:
            self.refresh_body()

        def action_close(self) -> None:
            self.dismiss(None)

        def action_toggle_hex(self) -> None:
            self.hex_mode = not self.hex_mode
            self.refresh_body()

        def refresh_body(self) -> None:
            title = f"Entry Viewer: {self.entry['file']} [{ 'split text+hex' if self.hex_mode else 'text' }]"
            body = build_entry_popup(self.entry, self.payload, self.exact_bytes)
            hex_body = build_entry_hex_popup(self.payload)
            self.query_one("#entry_popup_title", Static).update(rich_markup(accent(title)))
            self.query_one("#entry_popup_text", Static).update(rich_markup(body))
            hex_pane = self.query_one("#entry_hex_pane", VerticalScroll)
            hex_pane.styles.display = "block" if self.hex_mode else "none"
            self.query_one("#entry_popup_hex", Static).update(rich_markup(hex_body) if self.hex_mode else "")
            self.query_one("#entry_text_pane", VerticalScroll).scroll_home(animate=False)
            hex_pane.scroll_home(animate=False)

    class QuotaViewer(ModalScreen[None]):
        CSS = """
        QuotaViewer {
            align: center middle;
        }
        #quota_popup {
            width: 92%;
            height: 90%;
            border: round $accent;
            background: $surface;
        }
        #quota_popup_title {
            height: 3;
            padding: 0 1;
            border-bottom: solid $accent;
        }
        #quota_popup_body {
            height: 1fr;
            padding: 0 1;
            overflow-y: auto;
        }
        """

        BINDINGS = [
            Binding("i", "open_range_view", "Range View"),
            Binding("escape", "close", "Close"),
            Binding("enter", "close", "Close"),
            Binding("q", "close", "Close"),
        ]

        def __init__(self, snapshot: Snapshot, exact_bytes: bool) -> None:
            super().__init__()
            self.snapshot = snapshot
            self.exact_bytes = exact_bytes

        def compose(self) -> ComposeResult:
            with Vertical(id="quota_popup"):
                yield Static("", id="quota_popup_title")
                with VerticalScroll(id="quota_popup_body"):
                    yield Static("", id="quota_popup_text")

        def on_mount(self) -> None:
            self.query_one("#quota_popup_title", Static).update(
                rich_markup(accent("Quota Inspector"))
            )
            self.query_one("#quota_popup_text", Static).update(
                rich_markup(build_quota_detail_popup(self.snapshot, self.exact_bytes))
            )
            self.query_one("#quota_popup_body", VerticalScroll).scroll_home(animate=False)

        def action_close(self) -> None:
            self.dismiss(None)

        def action_open_range_view(self) -> None:
            self.app.push_screen(QuotaRangeViewer(self.snapshot, self.exact_bytes))

    class QuotaRangeHelpViewer(ModalScreen[None]):
        CSS = """
        QuotaRangeHelpViewer {
            align: center middle;
        }
        #quota_range_help_popup {
            width: 90%;
            height: 88%;
            border: round $accent;
            background: $surface;
        }
        #quota_range_help_title {
            height: 3;
            padding: 0 1;
            border-bottom: solid $accent;
        }
        #quota_range_help_body {
            height: 1fr;
            padding: 0 1;
            overflow-y: auto;
        }
        """

        BINDINGS = [
            Binding("question_mark", "close", "Close"),
            Binding("escape", "close", "Close"),
            Binding("enter", "close", "Close"),
            Binding("q", "close", "Close"),
        ]

        def compose(self) -> ComposeResult:
            with Vertical(id="quota_range_help_popup"):
                yield Static("", id="quota_range_help_title")
                with VerticalScroll(id="quota_range_help_body"):
                    yield Static("", id="quota_range_help_text")

        def on_mount(self) -> None:
            self.query_one("#quota_range_help_title", Static).update(
                rich_markup(accent("Inspector Semantics"))
            )
            self.query_one("#quota_range_help_text", Static).update(
                rich_markup(build_quota_range_help_popup())
            )
            self.query_one("#quota_range_help_body", VerticalScroll).scroll_home(animate=False)

        def action_close(self) -> None:
            self.dismiss(None)

    class QuotaRangeViewer(ModalScreen[None]):
        CSS = """
        QuotaRangeViewer {
            align: center middle;
        }
        #quota_range_popup {
            width: 96%;
            height: 94%;
            border: round $accent;
            background: $surface;
        }
        #quota_range_title {
            height: 3;
            padding: 0 1;
            border-bottom: solid $accent;
        }
        #quota_range_info {
            height: 10;
            padding: 0 1;
            border-bottom: solid $accent;
        }
        #quota_range_grid {
            height: 1fr;
            padding: 1 4;
            border-top: solid $accent;
            overflow-y: auto;
        }
        #quota_range_details {
            height: 11;
            padding: 0 1;
            border-top: solid $accent;
        }
        """

        BINDINGS = [
            Binding("left", "slot_left", "Slot Left"),
            Binding("right", "slot_right", "Slot Right"),
            Binding("up", "range_left", "Range Left"),
            Binding("down", "range_right", "Range Right"),
            Binding("a", "select_left", "Select Left"),
            Binding("d", "select_right", "Select Right"),
            Binding("w", "select_up", "Select Up"),
            Binding("s", "select_down", "Select Down"),
            Binding("[", "zoom_in", "Zoom In"),
            Binding("]", "zoom_out", "Zoom Out"),
            Binding("0", "jump_start", "Jump Start"),
            Binding("u", "jump_usage", "Jump Usage"),
            Binding("l", "jump_low", "Jump Low"),
            Binding("h", "jump_high", "Jump High"),
            Binding("m", "jump_max", "Jump Max"),
            Binding("question_mark", "open_help", "Help"),
            Binding("escape", "close", "Close"),
            Binding("enter", "close", "Close"),
            Binding("q", "close", "Close"),
        ]

        def __init__(self, snapshot: Snapshot, exact_bytes: bool) -> None:
            super().__init__()
            self.snapshot = snapshot
            self.exact_bytes = exact_bytes
            self.visible_slots = DEFAULT_QUOTA_RANGE_VISIBLE_SLOTS
            quota = snapshot.quota
            total_slots = quota_slots(quota.max_quota) or 0
            used_slots = quota_slots(snapshot.all_summary.accounted_bytes) or 0
            self.start_slot = clamp_slot_start(max(0, used_slots - self.visible_slots // 2), total_slots, self.visible_slots)
            self.selected_slot = max(0, min(total_slots - 1, used_slots - 1 if used_slots > 0 else self.start_slot)) if total_slots > 0 else 0
            self.slots_per_row = DEFAULT_QUOTA_RANGE_SLOTS_PER_ROW

        def compose(self) -> ComposeResult:
            with Vertical(id="quota_range_popup"):
                yield Static("", id="quota_range_title")
                yield Static("", id="quota_range_info")
                with VerticalScroll(id="quota_range_grid"):
                    yield Static("", id="quota_range_text")
                yield Static("", id="quota_range_details")

        def total_slots(self) -> int:
            return quota_slots(self.snapshot.quota.max_quota) or 0

        def page_slots(self) -> int:
            return self.visible_slots

        def used_slots(self) -> int:
            return min(self.total_slots(), quota_slots(self.snapshot.all_summary.accounted_bytes) or 0)

        def low_slots(self) -> int:
            return min(self.total_slots(), quota_slots(self.snapshot.quota.low_watermark) or 0)

        def high_slots(self) -> int:
            return min(self.total_slots(), quota_slots(self.snapshot.quota.high_watermark) or 0)

        def keep_selected_visible(self) -> None:
            total = self.total_slots()
            if total <= 0:
                self.selected_slot = 0
                self.start_slot = 0
                return
            self.selected_slot = max(0, min(self.selected_slot, total - 1))
            if self.selected_slot < self.start_slot:
                self.start_slot = self.selected_slot
            elif self.selected_slot >= self.start_slot + self.page_slots():
                self.start_slot = self.selected_slot - self.page_slots() + 1
            self.start_slot = clamp_slot_start(self.start_slot, total, self.page_slots())

        def refresh_body(self) -> None:
            self.keep_selected_visible()
            grid_height = self.query_one("#quota_range_grid", VerticalScroll).size.height
            slots_per_row = quota_grid_slots_per_row(self.visible_slots, grid_height)
            self.slots_per_row = slots_per_row
            title = (
                f"Slot Range Inspector: start={self.start_slot}  "
                f"visible_slots={self.visible_slots}  "
                f"selected={self.selected_slot}"
            )
            self.query_one("#quota_range_title", Static).update(rich_markup(accent(title)))
            info_text = build_quota_range_info(
                self.snapshot,
                self.start_slot,
                self.visible_slots,
                self.exact_bytes,
                slots_per_row=slots_per_row,
                selected_slot=self.selected_slot,
            )
            self.query_one("#quota_range_info", Static).update(rich_markup(info_text))
            grid_text = build_quota_range_grid(
                self.snapshot,
                self.start_slot,
                self.visible_slots,
                self.exact_bytes,
                slots_per_row=slots_per_row,
                selected_slot=self.selected_slot,
            )
            self.query_one("#quota_range_text", Static).update(rich_markup(grid_text))
            details_text = build_quota_range_slot_details(
                self.snapshot,
                self.selected_slot,
                self.exact_bytes,
            )
            self.query_one("#quota_range_details", Static).update(rich_markup(details_text))
            self.query_one("#quota_range_grid", VerticalScroll).scroll_home(animate=False)

        def on_mount(self) -> None:
            self.refresh_body()

        def move_range_by(self, delta_slots: int) -> None:
            self.start_slot += delta_slots
            self.refresh_body()

        def move_selection_by(self, delta_slots: int) -> None:
            self.selected_slot += delta_slots
            self.refresh_body()

        def action_slot_left(self) -> None:
            self.move_range_by(-1)

        def action_slot_right(self) -> None:
            self.move_range_by(1)

        def action_select_left(self) -> None:
            self.move_selection_by(-1)

        def action_select_right(self) -> None:
            self.move_selection_by(1)

        def action_select_up(self) -> None:
            self.move_selection_by(-self.slots_per_row)

        def action_select_down(self) -> None:
            self.move_selection_by(self.slots_per_row)

        def action_range_left(self) -> None:
            self.move_range_by(-self.page_slots())

        def action_range_right(self) -> None:
            self.move_range_by(self.page_slots())

        def action_zoom_in(self) -> None:
            self.visible_slots = max(8, self.visible_slots // 2)
            self.refresh_body()

        def action_zoom_out(self) -> None:
            self.visible_slots = min(512, self.visible_slots * 2)
            self.refresh_body()

        def action_jump_start(self) -> None:
            self.start_slot = 0
            self.selected_slot = 0
            self.refresh_body()

        def action_jump_usage(self) -> None:
            self.start_slot = self.used_slots() - self.page_slots() // 2
            self.selected_slot = max(0, self.used_slots() - 1)
            self.refresh_body()

        def action_jump_low(self) -> None:
            self.start_slot = self.low_slots() - self.page_slots() // 2
            self.selected_slot = max(0, self.low_slots())
            self.refresh_body()

        def action_jump_high(self) -> None:
            self.start_slot = self.high_slots() - self.page_slots() // 2
            self.selected_slot = max(0, self.high_slots())
            self.refresh_body()

        def action_jump_max(self) -> None:
            self.start_slot = self.total_slots() - self.page_slots()
            self.selected_slot = max(0, self.total_slots() - 1)
            self.refresh_body()

        def action_open_help(self) -> None:
            self.app.push_screen(QuotaRangeHelpViewer())

        def action_close(self) -> None:
            self.dismiss(None)

    class ChromeCacheCucker(App[None]):
        CSS = """
        Screen {
            layout: vertical;
        }
        #top {
            height: 13;
        }
        #summary {
            width: 54;
            min-width: 54;
            height: 1fr;
            border: round $accent;
            padding: 0 1;
        }
        #quota_visual {
            width: 1fr;
            height: 1fr;
            border: round $accent;
            padding: 0 1;
        }
        #body {
            height: 1fr;
        }
        #left {
            width: 54;
            min-width: 54;
        }
        #stats {
            height: 1fr;
            border: round $accent;
            padding: 0 1;
            overflow-y: auto;
        }
        #legend {
            height: 20;
            min-height: 10;
            border: round $accent;
            padding: 0 1;
            overflow-y: auto;
            display: none;
        }
        #right {
            width: 1fr;
        }
        #entries {
            height: 1fr;
            border: round $accent;
        }
        #details {
            height: 13;
            border: round $accent;
            padding: 0 1;
            overflow-y: auto;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("r", "refresh_now", "Refresh"),
            Binding("s", "cycle_sort", "Sort"),
            Binding("b", "toggle_bytes", "Bytes"),
            Binding("f", "toggle_freeze", "Freeze"),
            Binding("v", "open_quota_view", "Quota View"),
            Binding("p", "pick_profile", "Profile"),
            Binding("h", "toggle_legend", "Legend"),
            Binding("question_mark", "toggle_legend", "Legend"),
        ]

        def __init__(self, target: ProfileTarget, needle: str | None, refresh_seconds: float, quota_override: int | None) -> None:
            super().__init__()
            self.target = target
            self.needle = needle
            self.refresh_seconds = refresh_seconds
            self.quota_override = quota_override
            self.sort_index = 0
            self.show_legend = False
            self.exact_bytes = False
            self.frozen = False
            self.refresh_timer = None
            self.monitor_started = False
            self.snapshot: Snapshot | None = None
            self.stat_data: list[StatRow] = []
            self.entry_data: list[dict[str, object]] = []

        def quota_visual_width(self) -> int:
            widget = self.query_one("#quota_visual", Static)
            width = int(getattr(widget.size, "width", 0) or 0)
            return max(32, width - 12)

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="top"):
                yield Static(id="summary")
                yield Static(id="quota_visual")
            with Horizontal(id="body"):
                with Vertical(id="left"):
                    yield Static(id="stats")
                    with VerticalScroll(id="legend"):
                        yield Static(id="legend_text")
                with Vertical(id="right"):
                    yield DataTable(id="entries")
                    yield Static(id="details")
            yield Footer()

        def on_mount(self) -> None:
            table = self.query_one("#entries", DataTable)
            table.cursor_type = "row"
            table.zebra_stripes = True
            self.query_one("#legend", VerticalScroll).can_focus = True
            if target_is_profile_dir(self.target):
                self.start_monitor()
            else:
                self.open_profile_picker(required=True)

        def start_monitor(self) -> None:
            if self.monitor_started:
                return
            self.monitor_started = True
            self.refresh_view()
            self.query_one("#entries", DataTable).focus()
            self.refresh_timer = self.set_interval(self.refresh_seconds, self.refresh_view)

        def open_profile_picker(self, required: bool = False) -> None:
            self.push_screen(ProfilePicker(self.target), lambda selected_path: self.on_profile_picked(selected_path, required))

        def on_profile_picked(self, selected_path: str | None, required: bool = False) -> None:
            if not selected_path:
                if required and not self.monitor_started:
                    self.exit()
                elif self.monitor_started:
                    self.query_one("#entries", DataTable).focus()
                return
            if self.target.container is not None:
                self.target.process_hint = selected_path
            else:
                self.target.host_profile = Path(selected_path)
                self.target.process_hint = selected_path
            if self.monitor_started:
                self.refresh_view()
                self.query_one("#entries", DataTable).focus()
            else:
                self.start_monitor()

        def action_refresh_now(self) -> None:
            self.refresh_view()

        def action_cycle_sort(self) -> None:
            self.sort_index = (self.sort_index + 1) % len(SORTS)
            self.refresh_view()

        def action_toggle_bytes(self) -> None:
            self.exact_bytes = not self.exact_bytes
            self.refresh_view()

        def action_toggle_freeze(self) -> None:
            self.frozen = not self.frozen
            if self.refresh_timer is not None:
                self.refresh_timer.pause() if self.frozen else self.refresh_timer.resume()
            if self.snapshot:
                self.query_one("#summary", Static).update(
                    rich_markup(
                        build_summary(
                            self.snapshot,
                            SORTS[self.sort_index][1],
                            self.show_legend,
                            self.exact_bytes,
                            self.frozen,
                        )
                    )
                )

        def action_pick_profile(self) -> None:
            self.open_profile_picker(required=False)

        def action_open_quota_view(self) -> None:
            if self.snapshot is None:
                return
            self.push_screen(QuotaViewer(self.snapshot, self.exact_bytes))

        def action_toggle_legend(self) -> None:
            self.show_legend = not self.show_legend
            if self.snapshot:
                self.query_one("#summary", Static).update(
                    rich_markup(
                        build_summary(
                            self.snapshot,
                            SORTS[self.sort_index][1],
                            self.show_legend,
                            self.exact_bytes,
                            self.frozen,
                        )
                    )
                )
            legend = self.query_one("#legend", VerticalScroll)
            legend.styles.display = "block" if self.show_legend else "none"
            self.query_one("#legend_text", Static).update(
                rich_markup(build_legend(self.stat_data)) if self.show_legend else ""
            )
            if self.show_legend:
                legend.scroll_home(animate=False)
                legend.focus()
            else:
                self.query_one("#entries", DataTable).focus()
            self.update_details(self.query_one("#entries", DataTable).cursor_row)

        def on_data_table_row_selected(self, event) -> None:  # pragma: no cover - UI callback
            if getattr(event.data_table, "id", None) != "entries":
                return
            self.open_entry_viewer(getattr(event, "cursor_row", None))

        def on_click(self, event) -> None:  # pragma: no cover - UI callback
            if getattr(event, "chain", 1) != 2:
                return
            control = getattr(event, "control", None) or getattr(event, "widget", None) or getattr(event, "node", None)
            if control is not self.query_one("#entries", DataTable):
                return
            self.open_entry_viewer(self.query_one("#entries", DataTable).cursor_row)

        def on_data_table_row_highlighted(self, event) -> None:  # pragma: no cover - UI callback
            if getattr(event.data_table, "id", None) != "entries":
                return
            row = getattr(event, "cursor_row", None)
            if row is None:
                coordinate = getattr(event, "cursor_coordinate", None)
                row = getattr(coordinate, "row", None)
            self.update_details(row)

        def selected_row_state(self) -> tuple[str | None, int]:
            table = self.query_one("#entries", DataTable)
            row = getattr(table, "cursor_row", 0) or 0
            if 0 <= row < len(self.entry_data):
                return str(self.entry_data[row]["file"]), row
            return None, 0

        def refresh_view(self) -> None:
            try:
                focused = self.screen.focused
                focused_id = getattr(focused, "id", None)
                selected_file, selected_row = self.selected_row_state()
                snapshot = collect_snapshot(self.target, self.needle, self.quota_override)
                self.snapshot = snapshot
                self.stat_data = stat_rows(snapshot, self.exact_bytes)
                self.entry_data = sort_entries(snapshot.visible_entries, SORTS[self.sort_index][0])
                self.query_one("#summary", Static).update(
                    rich_markup(
                        build_summary(
                            snapshot,
                            SORTS[self.sort_index][1],
                            self.show_legend,
                            self.exact_bytes,
                            self.frozen,
                        )
                    )
                )
                self.query_one("#quota_visual", Static).update(
                    rich_markup(
                        build_quota_visual(
                            snapshot,
                            self.exact_bytes,
                            self.quota_visual_width(),
                        )
                    )
                )
                left = self.query_one("#left", Vertical)
                stats = self.query_one("#stats", Static)
                left.styles.width = stats_panel_width(self.stat_data)
                stats.update(rich_markup(build_stats_text(self.stat_data)))
                legend = self.query_one("#legend", VerticalScroll)
                legend.styles.display = "block" if self.show_legend else "none"
                self.query_one("#legend_text", Static).update(
                    rich_markup(build_legend(self.stat_data)) if self.show_legend else ""
                )
                selected_row = self.populate_entries(selected_file, selected_row)
                if focused_id == "legend" and self.show_legend:
                    legend.focus()
                elif focused_id == "entries":
                    self.query_one("#entries", DataTable).focus()
                self.update_details(selected_row)
            except Exception as exc:
                self.query_one("#summary", Static).update(f"Error: {exc}")
                self.query_one("#quota_visual", Static).update("")
                left = self.query_one("#left", Vertical)
                left.styles.width = 54
                stats = self.query_one("#stats", Static)
                stats.update("")
                legend = self.query_one("#legend", VerticalScroll)
                legend.styles.display = "none"
                self.query_one("#legend_text", Static).update("")
                self.query_one("#details", Static).update("Refresh failed.")
                table = self.query_one("#entries", DataTable)
                table.clear(columns=True)
                table.add_columns("#", "P", "Score", "Indexed", "Chromium", "Files", "_0", "Key", "URL")

        def populate_entries(self, selected_file: str | None, fallback_row: int) -> int | None:
            table = self.query_one("#entries", DataTable)
            table.clear(columns=True)
            table.add_columns("#", "P", "Score", "Indexed", "Chromium", "Files", "_0", "Key", "URL")
            selected_row = None
            for row_index, entry in enumerate(self.entry_data):
                table.add_row(
                    str(row_index + 1),
                    str(entry["partition"]),
                    str(entry["eviction_score"]) if entry["eviction_score"] is not None else "-",
                    fmt_bytes(int(entry["accounted"]), self.exact_bytes),
                    fmt_bytes(int(entry["chromium_size"]), self.exact_bytes),
                    fmt_bytes(int(entry["size"]), self.exact_bytes),
                    fmt_bytes(int(entry["file0_size"]), self.exact_bytes),
                    str(entry["key_length"]),
                    str(entry["url"] or entry["file"]),
                )
                if selected_file is not None and str(entry["file"]) == selected_file:
                    selected_row = row_index

            if selected_row is None and self.entry_data:
                selected_row = max(0, min(fallback_row, len(self.entry_data) - 1))

            if selected_row is not None:
                table.move_cursor(row=selected_row, animate=False)

            return selected_row

        def update_details(self, row: int | None) -> None:
            if not self.snapshot:
                return
            self.query_one("#details", Static).update(
                rich_markup(
                    build_details(
                        self.snapshot,
                        self.entry_data,
                        SORTS[self.sort_index][1],
                        row,
                        self.exact_bytes,
                    )
                )
            )

        def open_entry_viewer(self, row: int | None) -> None:
            if self.snapshot is None or row is None or not (0 <= row < len(self.entry_data)):
                return
            entry = self.entry_data[row]
            payload = load_entry_payload(self.target, self.snapshot, entry)
            self.push_screen(EntryViewer(entry, payload, self.exact_bytes))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile")
    parser.add_argument("--contains")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--refresh", type=float, default=1.0)
    parser.add_argument("--max-quota", type=int)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    try:
        target = resolve_profile_target(args.profile)
    except RuntimeError as exc:
        raise SystemExit(str(exc))

    if args.once or not sys.stdout.isatty():
        if not target_is_profile_dir(target):
            raise SystemExit("profile path is not a direct Chrome user-data-dir root; run interactively to choose one")
        try:
            snapshot = collect_snapshot(target, args.contains, args.max_quota)
        except RuntimeError as exc:
            raise SystemExit(str(exc))
        rows = stat_rows(snapshot)
        entries = sort_entries(snapshot.visible_entries, SORTS[0][0])
        print_once(snapshot, rows, entries, args.limit, SORTS[0][1])
        return

    if TEXTUAL_IMPORT_ERROR is not None:
        raise SystemExit("textual is not installed. Install it or use --once.")

    ChromeCacheCucker(target, args.contains, args.refresh, args.max_quota).run()


if __name__ == "__main__":
    main()
