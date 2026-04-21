"""单元测试 - RAG 模块."""

import tempfile
import os
from unittest.mock import MagicMock, patch
import pytest

from src.rag.knowledge_store import KnowledgeStore, RetrievalResult
from src.rag.ranker import Ranker, RankedResult
from src.rag.graph_node import (
    GraphNode, GraphEdge,
    LEVEL_FRAMEWORK, LEVEL_DOMAIN, LEVEL_CATEGORY, LEVEL_CONTROL, LEVEL_DETAIL,
    REL_CONTAINS, REL_BELONGS_TO, REL_RELATED_TO, REL_IMPLEMENTS,
)
from src.rag.graph_store import GraphStore
from src.rag.graph_builder import GraphBuilder, _infer_domain, _infer_category, _infer_framework
from src.rag.graph_retriever import GraphRetriever, GraphRetrievalResult


# ---------------------------------------------------------------------------
# Fixtures shared across graph test classes
# ---------------------------------------------------------------------------

def _make_simple_graph() -> GraphStore:
    """CIS / Network / Firewall / ctrl_3.5.1"""
    gs = GraphStore()
    fw = GraphNode.make_framework("CIS")
    dom = GraphNode.make_domain("CIS", "Network")
    cat = GraphNode.make_category("CIS", "Network", "Firewall")
    ctrl = GraphNode.make_control("CIS", "Network", "Firewall", "3.5.1",
                                  "Ensure firewall is installed and active")
    for n in (fw, dom, cat, ctrl):
        gs.add_node(n)
    gs.add_hierarchy_edge(fw.node_id, dom.node_id)
    gs.add_hierarchy_edge(dom.node_id, cat.node_id)
    gs.add_hierarchy_edge(cat.node_id, ctrl.node_id)
    return gs


def _make_fake_retriever(gs: GraphStore) -> GraphRetriever:
    mock_chroma = MagicMock()
    mock_chroma.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    mock_embed = MagicMock()
    mock_embed.encode_single.return_value = [0.0] * 4
    return GraphRetriever(gs, mock_chroma, mock_embed)


# ===========================================================================
# TestGraphNode
# ===========================================================================

class TestGraphNode:
    """GraphNode 工厂方法与基本行为。"""

    def test_make_framework(self):
        n = GraphNode.make_framework("CIS")
        assert n.level == LEVEL_FRAMEWORK
        assert n.label == "FRAMEWORK"
        assert n.metadata["framework"] == "CIS"
        assert "fw/cis" in n.node_id

    def test_make_domain(self):
        n = GraphNode.make_domain("CIS", "Network")
        assert n.level == LEVEL_DOMAIN
        assert n.metadata["domain"] == "Network"

    def test_make_category(self):
        n = GraphNode.make_category("CIS", "Network", "Firewall")
        assert n.level == LEVEL_CATEGORY
        assert n.metadata["category"] == "Firewall"

    def test_make_control(self):
        n = GraphNode.make_control("CIS", "Network", "Firewall", "3.5.1", "content")
        assert n.level == LEVEL_CONTROL
        assert n.metadata["control_id"] == "3.5.1"
        assert n.content == "content"

    def test_make_detail(self):
        ctrl = GraphNode.make_control("CIS", "Net", "FW", "1.1", "c")
        d = GraphNode.make_detail(ctrl.node_id, 0, "detail text")
        assert d.level == LEVEL_DETAIL
        assert d.metadata["parent_control"] == ctrl.node_id
        assert "detail/0" in d.node_id

    def test_equality_and_hash(self):
        a = GraphNode.make_framework("CIS")
        b = GraphNode.make_framework("CIS")
        assert a == b
        assert hash(a) == hash(b)

    def test_short_id(self):
        n = GraphNode.make_control("CIS", "Net", "FW", "3.5.1", "c")
        assert n.short_id() == "3.5.1"

    def test_custom_content(self):
        n = GraphNode.make_framework("NIST", content="NIST SP 800-53")
        assert "NIST SP 800-53" in n.content


# ===========================================================================
# TestGraphEdge
# ===========================================================================

class TestGraphEdge:
    def test_equality(self):
        a = GraphEdge("src", "tgt", REL_CONTAINS)
        b = GraphEdge("src", "tgt", REL_CONTAINS)
        assert a == b
        assert hash(a) == hash(b)

    def test_different_relation_not_equal(self):
        a = GraphEdge("src", "tgt", REL_CONTAINS)
        b = GraphEdge("src", "tgt", REL_BELONGS_TO)
        assert a != b


# ===========================================================================
# TestGraphStore
# ===========================================================================

class TestGraphStore:
    """GraphStore 节点/边管理与遍历。"""

    def test_add_and_get_node(self):
        gs = GraphStore()
        fw = GraphNode.make_framework("CIS")
        gs.add_node(fw)
        assert gs.has_node(fw.node_id)
        assert gs.get_node(fw.node_id) is fw

    def test_add_node_idempotent_updates_content(self):
        gs = GraphStore()
        fw = GraphNode.make_framework("CIS")
        gs.add_node(fw)
        fw2 = GraphNode.make_framework("CIS")
        fw2.content = "updated"
        gs.add_node(fw2)
        assert gs.get_node(fw.node_id).content == "updated"
        assert len(gs) == 1

    def test_nodes_at_level(self):
        gs = _make_simple_graph()
        assert len(gs.nodes_at_level(LEVEL_FRAMEWORK)) == 1
        assert len(gs.nodes_at_level(LEVEL_DOMAIN)) == 1
        assert len(gs.nodes_at_level(LEVEL_CONTROL)) == 1

    def test_add_hierarchy_edge_creates_both_directions(self):
        gs = GraphStore()
        fw = GraphNode.make_framework("CIS")
        dom = GraphNode.make_domain("CIS", "Net")
        gs.add_node(fw); gs.add_node(dom)
        gs.add_hierarchy_edge(fw.node_id, dom.node_id)
        out_rels = {e.relation for e in gs.get_out_edges(fw.node_id)}
        assert REL_CONTAINS in out_rels
        in_rels = {e.relation for e in gs.get_out_edges(dom.node_id)}
        assert REL_BELONGS_TO in in_rels

    def test_get_parent(self):
        gs = _make_simple_graph()
        ctrl = gs.nodes_at_level(LEVEL_CONTROL)[0]
        parent = gs.get_parent(ctrl.node_id)
        assert parent is not None
        assert parent.level == LEVEL_CATEGORY

    def test_get_children(self):
        gs = _make_simple_graph()
        cat = gs.nodes_at_level(LEVEL_CATEGORY)[0]
        children = gs.get_children(cat.node_id)
        assert len(children) == 1
        assert children[0].level == LEVEL_CONTROL

    def test_get_ancestors(self):
        gs = _make_simple_graph()
        ctrl = gs.nodes_at_level(LEVEL_CONTROL)[0]
        ancestors = gs.get_ancestors(ctrl.node_id)
        labels = [a.label for a in ancestors]
        assert labels == ["CATEGORY", "DOMAIN", "FRAMEWORK"]

    def test_get_descendants(self):
        gs = _make_simple_graph()
        fw = gs.nodes_at_level(LEVEL_FRAMEWORK)[0]
        descs = gs.get_descendants(fw.node_id, max_depth=3)
        levels = {d.level for d in descs}
        assert LEVEL_DOMAIN in levels
        assert LEVEL_CATEGORY in levels
        assert LEVEL_CONTROL in levels

    def test_get_siblings_empty_for_only_child(self):
        gs = _make_simple_graph()
        ctrl = gs.nodes_at_level(LEVEL_CONTROL)[0]
        assert gs.get_siblings(ctrl.node_id) == []

    def test_get_siblings(self):
        gs = GraphStore()
        fw = GraphNode.make_framework("CIS")
        dom = GraphNode.make_domain("CIS", "Net")
        cat1 = GraphNode.make_category("CIS", "Net", "A")
        cat2 = GraphNode.make_category("CIS", "Net", "B")
        for n in (fw, dom, cat1, cat2):
            gs.add_node(n)
        gs.add_hierarchy_edge(fw.node_id, dom.node_id)
        gs.add_hierarchy_edge(dom.node_id, cat1.node_id)
        gs.add_hierarchy_edge(dom.node_id, cat2.node_id)
        sibs = gs.get_siblings(cat1.node_id)
        assert len(sibs) == 1
        assert sibs[0].node_id == cat2.node_id

    def test_edge_idempotent(self):
        gs = GraphStore()
        fw = GraphNode.make_framework("CIS")
        dom = GraphNode.make_domain("CIS", "Net")
        gs.add_node(fw); gs.add_node(dom)
        gs.add_edge(GraphEdge(fw.node_id, dom.node_id, REL_RELATED_TO))
        gs.add_edge(GraphEdge(fw.node_id, dom.node_id, REL_RELATED_TO))
        assert len(gs.get_out_edges(fw.node_id)) == 1

    def test_stats(self):
        gs = _make_simple_graph()
        s = gs.stats()
        assert s["total_nodes"] == 4
        assert s["CONTROL"] == 1
        assert s["FRAMEWORK"] == 1

    def test_save_load_roundtrip(self):
        gs = _make_simple_graph()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            gs.save(path)
            gs2 = GraphStore.load(path)
            assert gs2.stats()["total_nodes"] == gs.stats()["total_nodes"]
            assert gs2.stats()["total_edges"] == gs.stats()["total_edges"]
            ctrl2 = gs2.nodes_at_level(LEVEL_CONTROL)[0]
            ancestors = gs2.get_ancestors(ctrl2.node_id)
            assert [a.label for a in ancestors] == ["CATEGORY", "DOMAIN", "FRAMEWORK"]
        finally:
            os.unlink(path)

    def test_contains(self):
        gs = _make_simple_graph()
        fw = gs.nodes_at_level(LEVEL_FRAMEWORK)[0]
        assert fw.node_id in gs
        assert "nonexistent" not in gs


# ===========================================================================
# TestGraphBuilder
# ===========================================================================

class TestGraphBuilder:
    """GraphBuilder 构建与增量追加。"""

    @pytest.fixture
    def items(self):
        return [
            {"content": "Disable root SSH login via PermitRootLogin no in sshd_config",
             "metadata": {"id": "c1", "framework": "CIS", "domain": "Access Control",
                          "category": "SSH", "control_id": "5.2.8"}},
            {"content": "Ensure firewall is active, use iptables or firewalld.",
             "metadata": {"id": "c2", "framework": "CIS", "domain": "Network",
                          "category": "Firewall", "control_id": "3.5.1"}},
            {"content": "Set sysctl net.ipv4.ip_forward=0. Edit /etc/sysctl.conf and run sysctl -p.",
             "metadata": {"id": "c3", "framework": "CIS", "domain": "Kernel",
                          "category": "Kernel Parameters", "control_id": "3.2.1"}},
        ]

    def test_build_creates_hierarchy(self, items):
        gs = GraphBuilder().build(items)
        assert len(gs.nodes_at_level(LEVEL_FRAMEWORK)) == 1
        assert len(gs.nodes_at_level(LEVEL_DOMAIN)) == 3
        assert len(gs.nodes_at_level(LEVEL_CATEGORY)) == 3
        assert len(gs.nodes_at_level(LEVEL_CONTROL)) == 3

    def test_hierarchy_edges_connected(self, items):
        gs = GraphBuilder().build(items)
        for ctrl in gs.nodes_at_level(LEVEL_CONTROL):
            ancestors = gs.get_ancestors(ctrl.node_id)
            labels = [a.label for a in ancestors]
            assert "CATEGORY" in labels
            assert "DOMAIN" in labels
            assert "FRAMEWORK" in labels

    def test_incremental_add(self, items):
        builder = GraphBuilder()
        gs = builder.build(items[:1])
        assert len(gs.nodes_at_level(LEVEL_CONTROL)) == 1
        added = builder.add_items(gs, items[1:])
        assert added == 2
        assert len(gs.nodes_at_level(LEVEL_CONTROL)) == 3

    def test_duplicate_item_not_added_twice(self, items):
        builder = GraphBuilder()
        gs = builder.build(items[:1])
        added = builder.add_items(gs, items[:1])
        assert added == 0
        assert len(gs.nodes_at_level(LEVEL_CONTROL)) == 1

    def test_long_content_creates_detail_nodes(self):
        # Each paragraph must exceed DETAIL_THRESHOLD (400 chars) total
        para = "A" * 180
        long_text = f"{para} first paragraph.\n\n{para} second paragraph.\n\n{para} third paragraph."
        items = [{"content": long_text,
                  "metadata": {"id": "x1", "framework": "CIS", "domain": "Network",
                               "category": "Firewall", "control_id": "9.9.9"}}]
        gs = GraphBuilder().build(items)
        ctrl = gs.nodes_at_level(LEVEL_CONTROL)[0]
        details = gs.get_children(ctrl.node_id)
        assert len(details) >= 2

    def test_metadata_inference_from_source_path(self):
        item = {"content": "audit rules for login",
                "metadata": {"id": "x", "source": "/data/cis/benchmark.yaml"}}
        gs = GraphBuilder().build([item])
        fw_nodes = gs.nodes_at_level(LEVEL_FRAMEWORK)
        assert fw_nodes[0].metadata["framework"] == "CIS"

    def test_infer_domain_ssh(self):
        assert _infer_domain("sshd_config sets PermitRootLogin") == "SSH"

    def test_infer_domain_network(self):
        assert _infer_domain("configure iptables firewall rules") == "Network"

    def test_infer_category_firewall(self):
        assert _infer_category("use iptables or nftables to block traffic") == "Firewall"

    def test_infer_framework_from_source(self):
        assert _infer_framework({"source": "/policies/stig/v1.yaml"}) == "STIG"
        assert _infer_framework({"source": "/policies/nist/sp800.yaml"}) == "NIST"
        assert _infer_framework({"source": "/other.yaml"}) == "Generic"

    def test_skip_empty_content(self):
        items = [{"content": "", "metadata": {"id": "empty"}}]
        gs = GraphBuilder().build(items)
        assert len(gs.nodes_at_level(LEVEL_CONTROL)) == 0


# ===========================================================================
# TestGraphRetriever
# ===========================================================================

class TestGraphRetriever:
    """GraphRetriever 上下文路径与图遍历检索。"""

    @pytest.fixture
    def gs(self):
        return _make_simple_graph()

    @pytest.fixture
    def retriever(self, gs):
        return _make_fake_retriever(gs)

    def test_context_path_format(self, retriever, gs):
        ctrl = gs.nodes_at_level(LEVEL_CONTROL)[0]
        path = retriever._build_context_path(ctrl)
        assert path == "CIS / Network / Firewall / 3.5.1"

    def test_context_path_framework_node(self, retriever, gs):
        fw = gs.nodes_at_level(LEVEL_FRAMEWORK)[0]
        path = retriever._build_context_path(fw)
        assert path == "CIS"

    def test_search_by_path_framework_filter(self):
        gs = GraphBuilder().build([
            {"content": "SSH root login", "metadata": {"id": "a", "framework": "CIS",
             "domain": "Access Control", "category": "SSH", "control_id": "5.2.8"}},
            {"content": "STIG control", "metadata": {"id": "b", "framework": "STIG",
             "domain": "Network", "category": "Firewall", "control_id": "V-001"}},
        ])
        gr = _make_fake_retriever(gs)
        results = gr.search_by_path(framework="CIS")
        frameworks = {r.metadata.get("framework") for r in results
                      if r.metadata.get("framework")}
        assert "STIG" not in frameworks

    def test_search_by_path_category_filter(self):
        gs = GraphBuilder().build([
            {"content": "SSH PermitRootLogin no", "metadata": {"id": "a", "framework": "CIS",
             "domain": "Access Control", "category": "SSH", "control_id": "5.2.8"}},
            {"content": "firewall block all", "metadata": {"id": "b", "framework": "CIS",
             "domain": "Network", "category": "Firewall", "control_id": "3.5.1"}},
        ])
        gr = _make_fake_retriever(gs)
        results = gr.search_by_path(framework="CIS", category="SSH")
        for r in results:
            if r.metadata.get("category"):
                assert r.metadata["category"] == "SSH"

    def test_search_returns_empty_when_chroma_empty(self, retriever):
        results = retriever.search("SSH config", n_results=5)
        assert isinstance(results, list)

    def test_get_context_window_structure(self, retriever, gs):
        ctrl = gs.nodes_at_level(LEVEL_CONTROL)[0]
        window = retriever.get_context_window(ctrl.node_id)
        assert "node" in window
        assert "ancestors" in window
        assert "siblings" in window
        assert "children" in window
        assert window["node"]["node_id"] == ctrl.node_id
        assert len(window["ancestors"]) == 3

    def test_get_context_window_missing_node(self, retriever):
        assert retriever.get_context_window("does/not/exist") == {}

    def test_search_by_path_returns_ranked(self):
        builder = GraphBuilder()
        items = [
            {"content": f"Control {i}", "metadata": {"id": f"c{i}", "framework": "CIS",
             "domain": "Network", "category": "Firewall", "control_id": f"3.5.{i}"}}
            for i in range(5)
        ]
        gs = builder.build(items)
        gr = _make_fake_retriever(gs)
        results = gr.search_by_path(framework="CIS")
        assert all(r.rank == i + 1 for i, r in enumerate(results))

    def test_graph_retrieval_result_properties(self, gs):
        ctrl = gs.nodes_at_level(LEVEL_CONTROL)[0]
        r = GraphRetrievalResult(node=ctrl, content=ctrl.content,
                                 metadata=ctrl.metadata, vector_score=0.9,
                                 final_score=0.85, rank=1)
        assert r.node_id == ctrl.node_id
        assert r.level == LEVEL_CONTROL


# ===========================================================================
# TestRanker (existing, unchanged)
# ===========================================================================

class TestRanker:
    """Ranker 测试类。"""

    @pytest.fixture
    def ranker(self):
        """测试前准备。"""
        return Ranker()

    def test_rank(self, ranker):
        """测试排序。"""
        mock_results = [
            RetrievalResult(content="doc1", metadata={}, score=0.8, rank=1),
            RetrievalResult(content="doc2", metadata={}, score=0.9, rank=2)
        ]
        ranked = ranker.rank(mock_results, "test")
        assert ranked[0].score == 0.9
        assert ranked[0].rank == 1

    def test_filter_by_metadata(self, ranker):
        """测试元数据过滤。"""
        mock_results = [
            RetrievalResult(content="doc1", metadata={"type": "A"}, score=0.8, rank=1),
            RetrievalResult(content="doc2", metadata={"type": "B"}, score=0.9, rank=2)
        ]
        filtered = ranker.filter_by_metadata(mock_results, {"type": "A"})
        assert len(filtered) == 1

    def test_boost_by_relevance(self, ranker):
        """测试相关性提升。"""
        mock_results = [
            RetrievalResult(content="SSH configuration", metadata={}, score=0.8, rank=1)
        ]
        ranked = ranker.boost_by_relevance(mock_results, "SSH")
        assert len(ranked) >= 1


class TestKnowledgeStore:
    """KnowledgeStore 测试类。"""

    @pytest.fixture
    def store(self):
        with patch('src.rag.knowledge_store.EmbeddingModel') as MockEmbedding, \
             patch('src.rag.knowledge_store.ChromaClient') as MockChroma, \
             patch('src.rag.knowledge_store.VectorStorePersistence'), \
             patch('src.rag.knowledge_store.GraphStore') as MockGraphStore:
            mock_embed = MagicMock()
            mock_embed.encode_single.return_value = [0.1, 0.2, 0.3]
            MockEmbedding.return_value = mock_embed

            mock_chroma = MagicMock()
            mock_chroma.query.return_value = {
                "documents": [["doc1"]], "metadatas": [[{}]], "distances": [[0.2]]
            }
            mock_chroma.collection.get.return_value = {
                "documents": [], "metadatas": [], "ids": []
            }
            MockChroma.return_value = mock_chroma

            mock_gs = MagicMock()
            mock_gs.__len__ = MagicMock(return_value=0)
            mock_gs.stats.return_value = {"total_nodes": 0}
            MockGraphStore.return_value = mock_gs

            yield KnowledgeStore("./test_db", "test_collection")

    def test_init_with_mock(self, store):
        assert store is not None
        assert store.collection_name == "test_collection"

    def test_search_returns_retrieval_results(self, store):
        store.ranker.rank = MagicMock(return_value=[
            MagicMock(content="doc1", metadata={}, score=0.8, rank=1)
        ])
        results = store.search("test query")
        assert len(results) == 1
        assert isinstance(results[0], RetrievalResult)

    def test_search_with_filter(self, store):
        store.ranker.rank = MagicMock(return_value=[])
        results = store.search("query", filter_dict={"framework": "CIS"})
        assert isinstance(results, list)

    def test_graph_search_falls_back_to_vector_when_graph_empty(self, store):
        store.graph_store.__len__ = MagicMock(return_value=0)
        store.ranker.rank = MagicMock(return_value=[
            MagicMock(content="doc1", metadata={}, score=0.8, rank=1)
        ])
        results = store.graph_search("SSH config", n_results=5)
        assert isinstance(results, list)
        for r in results:
            assert hasattr(r, "node")
            assert hasattr(r, "final_score")

    def test_graph_search_uses_graph_retriever_when_populated(self, store):
        store.graph_store.__len__ = MagicMock(return_value=10)
        fake_result = MagicMock(spec=GraphRetrievalResult)
        store.graph_retriever.search = MagicMock(return_value=[fake_result])
        results = store.graph_search("firewall rules")
        store.graph_retriever.search.assert_called_once()
        assert results == [fake_result]

    def test_get_graph_stats(self, store):
        store.graph_store.stats.return_value = {"total_nodes": 5, "CONTROL": 2}
        stats = store.get_graph_stats()
        assert "total_nodes" in stats

    def test_add_updates_graph(self, store):
        store._graph_builder.add_items = MagicMock(return_value=1)
        store._save_graph = MagicMock()
        store.chroma_client.add = MagicMock()
        store.chroma_client.get_collection_info = MagicMock(
            return_value={"name": "test", "count": 1}
        )
        items = [{"content": "test content",
                  "metadata": {"id": "t1", "framework": "CIS",
                               "domain": "Network", "category": "Firewall",
                               "control_id": "1.1"}}]
        store.add(items)
        store._graph_builder.add_items.assert_called_once()

    def test_rebuild_graph(self, store):
        store.chroma_client.collection.get.return_value = {
            "documents": ["doc"], "metadatas": [{"id": "x"}], "ids": ["x"]
        }
        store._save_graph = MagicMock()
        count = store.rebuild_graph()
        assert isinstance(count, int)

    def test_consolidate_calls_add_with_consolidated_metadata(self, store):
        """consolidate() must store only verified-success remediations with required tags."""
        store._graph_builder.add_items = MagicMock(return_value=1)
        store._save_graph = MagicMock()
        store.chroma_client.add = MagicMock()
        store.chroma_client.get_collection_info = MagicMock(
            return_value={"name": "test", "count": 1}
        )
        store.consolidate(
            rule_id="5.2.1",
            playbook="---\n- name: fix",
            os_version="RHEL 9.2",
            error_signature="permission denied",
            version="2",
        )
        store.chroma_client.add.assert_called_once()
        call_kwargs = store.chroma_client.add.call_args
        # metadata is the second positional arg or keyword arg
        added_meta = call_kwargs[0][1][0] if call_kwargs[0] else call_kwargs[1]["metadatas"][0]
        assert added_meta["rule_id"] == "5.2.1"
        assert added_meta["os_version"] == "RHEL 9.2"
        assert added_meta["error_signature"] == "permission denied"
        assert added_meta["type"] == "consolidated_remediation"
        assert added_meta["source"] == "verified_success"
