"""Knowledge Graph Builder.

将平铺的知识条目（来自 ChromaDB / YAML 解析器）构建成层次知识图谱。

每个知识条目的 metadata 预期字段（均为可选，缺失时自动推断）：
  framework  : str   CIS / NIST / STIG / generic
  domain     : str   安全域（Access Control / Network ...）
  category   : str   类别（SSH / Firewall / Users ...）
  control_id : str   控制项编号（1.1.1 / V-123456 …）
  source     : str   来源文件路径（用于推断 framework）

构建流程：
  1. 规范化元数据（填充缺失字段）
  2. 为每层（FRAMEWORK / DOMAIN / CATEGORY）获取或创建聚合节点
  3. 为每个知识条目创建 CONTROL 节点（及可选 DETAIL 子节点）
  4. 连接层次边 (CONTAINS / BELONGS_TO)
  5. 推断语义关联边 (RELATED_TO) —— 基于关键词共现

支持增量追加（对已存在节点只更新不重复添加）。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .graph_node import (
    LEVEL_CONTROL,
    GraphEdge,
    GraphNode,
    REL_IMPLEMENTS,
    REL_RELATED_TO,
)
from .graph_store import GraphStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain / category keyword mapping
# (用于从自由文本正文推断 domain 和 category)
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: List[Tuple[str, str]] = [
    ("Access Control", ["user", "account", "password", "pam", "privilege", "sudo",
                        "permission", "chmod", "chown", "umask", "login"]),
    ("Network", ["firewall", "iptables", "nftables", "ufw", "firewalld", "tcp",
                 "udp", "port", "interface", "route", "network"]),
    ("Kernel", ["kernel", "sysctl", "proc", "module", "parameter", "net.ipv4",
                "fs.", "vm.", "kernel.randomize"]),
    ("Audit & Logging", ["audit", "auditd", "log", "rsyslog", "syslog", "journald",
                         "auditctl", "ausearch"]),
    ("System Services", ["service", "systemd", "cron", "at", "daemon", "socket",
                         "unit", "timer"]),
    ("File System", ["mount", "partition", "fstab", "noexec", "nosuid", "nodev",
                     "tmpfs", "sticky"]),
    ("SSH", ["ssh", "sshd", "sshd_config", "authorized_keys", "known_hosts",
             "banner", "hostbased"]),
    ("SELinux / AppArmor", ["selinux", "apparmor", "enforcing", "permissive",
                             "policy", "context", "label"]),
    ("Cryptography", ["tls", "ssl", "cipher", "certificate", "key", "gpg",
                      "openssl", "algorithm", "entropy"]),
]

_CATEGORY_KEYWORDS: List[Tuple[str, str]] = [
    ("SSH", ["ssh", "sshd", "root login", "ssh banner"]),
    ("Firewall", ["iptables", "nftables", "ufw", "firewalld", "firewall-cmd"]),
    ("User Accounts", ["useradd", "passwd", "shadow", "lock", "expiry", "user account"]),
    ("Password Policy", ["pwquality", "minlen", "maxrepeat", "pam_pwquality",
                         "password quality", "cracklib"]),
    ("Audit Rules", ["auditd", "auditctl", "-w", "-a always", "audit rule"]),
    ("Kernel Parameters", ["sysctl", "kernel parameter", "sysctl.conf"]),
    ("File Permissions", ["chmod", "chown", "mode", "owner", "permission", "sticky"]),
    ("Cron", ["cron", "crontab", "at command", "anacron"]),
    ("Logging", ["rsyslog", "syslog", "journald", "log file"]),
    ("SELinux", ["selinux", "enforcing", "permissive", "getenforce"]),
    ("Mount Options", ["mount", "noexec", "nosuid", "nodev", "fstab"]),
    ("System Services", ["systemctl", "disable", "enable", "service unit"]),
]


def _infer_domain(text: str) -> str:
    lower = text.lower()
    best_domain, best_count = "General", 0
    for domain, keywords in _DOMAIN_KEYWORDS:
        count = sum(1 for kw in keywords if kw in lower)
        if count > best_count:
            best_domain, best_count = domain, count
    return best_domain


def _infer_category(text: str) -> str:
    lower = text.lower()
    best_cat, best_count = "General", 0
    for cat, keywords in _CATEGORY_KEYWORDS:
        count = sum(1 for kw in keywords if kw in lower)
        if count > best_count:
            best_cat, best_count = cat, count
    return best_cat


def _infer_framework(metadata: Dict[str, Any]) -> str:
    """从 metadata 或 source 路径推断 framework。"""
    fw = metadata.get("framework", "")
    if fw:
        return fw
    source: str = metadata.get("source", "") or metadata.get("file_path", "")
    source_lower = source.lower()
    if "cis" in source_lower:
        return "CIS"
    if "stig" in source_lower:
        return "STIG"
    if "nist" in source_lower:
        return "NIST"
    return "Generic"


def _normalize_meta(item: Dict[str, Any]) -> Dict[str, Any]:
    """返回填充了缺失字段的规范化元数据副本。"""
    meta = dict(item.get("metadata", {}))
    content = item.get("content", "")

    meta.setdefault("framework", _infer_framework(meta))
    meta.setdefault("domain", _infer_domain(content))
    meta.setdefault("category", _infer_category(content))
    meta.setdefault("control_id", meta.get("id", "unknown"))

    return meta


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

class GraphBuilder:
    """从知识条目构建层次知识图谱。

    Examples:
        >>> builder = GraphBuilder()
        >>> gs = builder.build(knowledge_items)
        >>> builder.add_items(gs, more_items)  # 增量追加
    """

    # 每个控制项最多切分出多少 DETAIL 子节点
    MAX_DETAIL_SPLITS = 4
    # 正文超过此长度才cut成 DETAIL 细节节点
    DETAIL_THRESHOLD = 400

    def build(
        self,
        items: List[Dict[str, Any]],
        embedding_model=None,
    ) -> GraphStore:
        """从知识条目列表构建新图谱。

        Args:
            items:           知识条目列表（各项含 content 和 metadata）
            embedding_model: 可选 EmbeddingModel，用于预填 embedding

        Returns:
            构建好的 GraphStore
        """
        gs = GraphStore()
        self.add_items(gs, items, embedding_model=embedding_model)
        return gs

    def add_items(
        self,
        gs: GraphStore,
        items: List[Dict[str, Any]],
        embedding_model=None,
    ) -> int:
        """向已有图谱增量追加知识条目。

        Returns:
            新增的 CONTROL 节点数量
        """
        added = 0
        for item in items:
            meta = _normalize_meta(item)
            content: str = item.get("content", "")
            if not content:
                continue

            framework = meta["framework"]
            domain = meta["domain"]
            category = meta["category"]
            control_id = meta["control_id"]

            # ---- 层级聚合节点 ----
            fw_node = GraphNode.make_framework(framework)
            dom_node = GraphNode.make_domain(framework, domain)
            cat_node = GraphNode.make_category(framework, domain, category)

            gs.add_node(fw_node)
            gs.add_node(dom_node)
            gs.add_node(cat_node)

            # 层次边（幂等）
            gs.add_hierarchy_edge(fw_node.node_id, dom_node.node_id)
            gs.add_hierarchy_edge(dom_node.node_id, cat_node.node_id)

            # ---- CONTROL 节点 ----
            ctrl_node = GraphNode.make_control(
                framework=framework,
                domain=domain,
                category=category,
                control_id=control_id,
                content=content,
                metadata=meta,
            )

            was_new = ctrl_node.node_id not in gs
            gs.add_node(ctrl_node)
            gs.add_hierarchy_edge(cat_node.node_id, ctrl_node.node_id)

            # ---- 可选：拆分长文本为 DETAIL 子节点 ----
            if len(content) > self.DETAIL_THRESHOLD:
                self._add_detail_nodes(gs, ctrl_node, content, meta)

            # ---- 填充 embedding ----
            if embedding_model and ctrl_node.embedding is None:
                ctrl_node.embedding = embedding_model.encode_single(ctrl_node.content)

            if was_new:
                added += 1

        # ---- 构建语义关联边 ----
        self._build_related_edges(gs)

        logger.info("GraphBuilder.add_items: +%d CONTROL nodes, total=%s", added, gs.stats())
        return added

    # ------------------------------------------------------------------
    # Detail node splitting
    # ------------------------------------------------------------------

    def _add_detail_nodes(
        self,
        gs: GraphStore,
        ctrl_node: GraphNode,
        content: str,
        meta: Dict[str, Any],
    ) -> None:
        """将长文本按语义段落拆分为 DETAIL 子节点。"""
        segments = self._split_into_segments(content)
        for idx, seg in enumerate(segments[: self.MAX_DETAIL_SPLITS]):
            detail = GraphNode.make_detail(
                control_node_id=ctrl_node.node_id,
                detail_index=idx,
                content=seg,
                metadata={k: v for k, v in meta.items()
                           if k in ("framework", "domain", "category", "control_id")},
            )
            gs.add_node(detail)
            gs.add_hierarchy_edge(ctrl_node.node_id, detail.node_id)
            gs.add_edge(GraphEdge(detail.node_id, ctrl_node.node_id, REL_IMPLEMENTS))

    @staticmethod
    def _split_into_segments(text: str) -> List[str]:
        """按双换行或句子边界将文本分段。"""
        # 优先按双换行（段落）分割
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        if len(paragraphs) >= 2:
            return paragraphs
        # 其次按单换行分割
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if len(lines) >= 2:
            return lines
        # 最后按句子分割（。.!?）
        sentences = re.split(r"(?<=[.!?。])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    # ------------------------------------------------------------------
    # Semantic relation edges
    # ------------------------------------------------------------------

    _DOMAIN_RELATIONS: List[Tuple[str, str]] = [
        ("SSH", "Access Control"),
        ("Firewall", "Network"),
        ("Kernel Parameters", "Network"),
        ("Audit Rules", "Audit & Logging"),
        ("Logging", "Audit & Logging"),
    ]

    def _build_related_edges(self, gs: GraphStore) -> None:
        """在具有语义关联的 CATEGORY 节点之间建立 RELATED_TO 边。"""
        cat_map: Dict[str, GraphNode] = {
            n.metadata.get("category", ""): n
            for n in gs.nodes_at_level(2)  # LEVEL_CATEGORY = 2
        }
        for cat_a, cat_b in self._DOMAIN_RELATIONS:
            node_a = cat_map.get(cat_a)
            node_b = cat_map.get(cat_b)
            if node_a and node_b:
                gs.add_edge(GraphEdge(node_a.node_id, node_b.node_id, REL_RELATED_TO, weight=0.6))
                gs.add_edge(GraphEdge(node_b.node_id, node_a.node_id, REL_RELATED_TO, weight=0.6))
