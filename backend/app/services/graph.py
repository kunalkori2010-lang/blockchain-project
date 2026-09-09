"""Build investigator graph: nodes + edges for ReactFlow/Cytoscape."""
from collections import Counter


def build_graph(address: str, txs: list[dict], entity_map: dict, risk_score: int, limit: int = 40):
    addr = address.lower()
    # rank counterparties by interaction count
    cnt = Counter()
    for t in txs:
        f, to = t["from_address"], t["to_address"]
        if f.lower() == addr:
            cnt[to] += 1
        elif to.lower() == addr:
            cnt[f] += 1
    top = [a for a, _ in cnt.most_common(limit)]
    keep = set([address] + top)
    # include 2nd-hop forward from consolidation for story completeness
    extra_edges = []
    for t in txs:
        if t["from_address"] in top or t["to_address"] in top:
            keep.add(t["from_address"])
            keep.add(t["to_address"])

    nodes = []
    for a in keep:
        is_suspect = a.lower() == addr
        ent = entity_map.get(a.lower())
        nodes.append({
            "id": a,
            "label": "SUSPECT" if is_suspect else (ent["label"] if ent else a[:10] + "…"),
            "type": "suspect" if is_suspect else (ent["category"] if ent else "wallet"),
            "entity": ent["label"] if ent else None,
            "risk": risk_score if is_suspect else None,
        })
    edges = []
    for t in txs:
        if t["from_address"] in keep and t["to_address"] in keep:
            edges.append({
                "id": t["tx_hash"][:16],
                "source": t["from_address"],
                "target": t["to_address"],
                "label": f"{t['amount']} {t.get('token', 'ETH')}",
                "tx_hash": t["tx_hash"],
                "timestamp": t["timestamp"],
            })
    return {"nodes": nodes[:80], "edges": edges[:160]}


def trace_metrics(address: str, txs: list[dict], entity_map: dict) -> dict:
    """networkx fund-flow intelligence: shortest suspect→endpoint path,
    max hop depth reached, and most-connected hubs (excluding the suspect)."""
    try:
        import networkx as nx
    except ImportError:
        return {"engine": "unavailable"}
    addr = address.lower()
    G = nx.DiGraph()
    for t in txs:
        G.add_edge(t["from_address"].lower(), t["to_address"].lower(), tx_hash=t["tx_hash"])
    if addr not in G:
        return {"engine": "networkx", "nodes": 0, "edges": 0}
    targets = [a for a in entity_map if a in G and entity_map[a].get("category") in ("exchange", "flagged", "mixer")]
    best = None
    for tgt in targets:
        try:
            p = nx.shortest_path(G, addr, tgt)
            if best is None or len(p) < len(best["path"]):
                best = {"hops": len(p) - 1, "path": p,
                        "label": entity_map[tgt].get("label", tgt),
                        "category": entity_map[tgt].get("category", "")}
        except nx.NetworkXNoPath:
            continue
    lengths = nx.single_source_shortest_path_length(G, addr)
    hubs = sorted(((n, d) for n, d in G.degree() if n != addr), key=lambda x: -x[1])[:3]
    return {"engine": "networkx", "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
            "max_depth": max(lengths.values()) if lengths else 0,
            "nearest_endpoint": best,
            "hubs": [{"address": h, "degree": d,
                      "label": entity_map.get(h, {}).get("label")} for h, d in hubs]}
