import os
import uuid
from collections import defaultdict
from importlib.resources import files

from AnyQt.QtWidgets import QFileDialog

from Orange.widgets import widget, gui
from Orange.widgets.settings import Setting
from Orange.data import Table, Domain, StringVariable

from lxml import etree

class OWPathwayKG(widget.OWWidget):
    name = "Pathway to Knowledge Graph"
    id = "orange.widgets.pathwaykg"
    description = "Convert KEGG KGML into a Knowledge Graph"
    icon = str(files("orange3biosci") / "icons/PathwayKG.svg")
    priority = 10

    class Outputs:
        nodes = widget.Output("Nodes", Table)
        edges = widget.Output("Edges", Table)

    want_main_area = False

    filename = Setting("")

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------

    def __init__(self):
        super().__init__()

        box = gui.widgetBox(self.controlArea, "KGML File")

        gui.button(box, self, "Load KGML",
                   callback=self.load_file)

        self.file_label = gui.label(box, self, "No file loaded")

    def load_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open KGML", "", "KGML files (*.xml *.kgml)"
        )
        if fname:
            self.filename = fname
            self.file_label.setText(os.path.basename(fname))
            self.setStatusMessage(os.path.basename(fname))
            self.process()

    # ------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------

    def process(self):
        if not self.filename:
            return

        tree = etree.parse(self.filename)
        root = tree.getroot()

        nodes, edges = self.build_graph(root)

        self.Outputs.nodes.send(self.to_table(nodes))
        self.Outputs.edges.send(self.to_table(edges))

    # ------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------

    def build_graph(self, root):
        entries = {}
        groups = {}
        relations = []

        pathway_id = root.attrib.get("name", "pathway")

        # -------------------------
        # Parse entries
        # -------------------------
        for entry in root.findall("entry"):
            eid = entry.attrib["id"]
            etype = entry.attrib.get("type")
            name = entry.attrib.get("name", "")
            reaction_ids = entry.attrib.get("reaction", "").split()

            entries[eid] = {
                "id": eid,
                "type": etype,
                "name": name,
                "genes": name.split(),
                "reactions": reaction_ids,
                "pathway_positions": reaction_ids or [eid]
            }

        # -------------------------
        # Parse groups (complexes)
        # -------------------------
        for entry in root.findall("entry"):
            if entry.attrib.get("type") == "group":
                gid = entry.attrib["id"]
                comps = [c.attrib["id"] for c in entry.findall("component")]
                groups[gid] = comps

        # -------------------------
        # Parse relations
        # -------------------------
        for rel in root.findall("relation"):
            entry1 = rel.attrib["entry1"]
            entry2 = rel.attrib["entry2"]
            rtype = rel.attrib.get("type")

            subtypes = []
            for sub in rel.findall("subtype"):
                subtypes.append(sub.attrib.get("name"))

            relations.append({
                "source": entry1,
                "target": entry2,
                "type": rtype,
                "subtypes": subtypes
            })

        # -------------------------
        # Build nodes
        # -------------------------
        nodes = {}
        entry_to_fu = defaultdict(list)

        # --- Gene entries → FU ---
        for eid, e in entries.items():
            if e["type"] != "gene":
                continue

            genes = e["genes"]
            if not genes:
                continue

            logic = "OR" if len(genes) > 1 else "SINGLE"
            fu_id = f"FU_{uuid.uuid4().hex[:8]}"

            # FU node
            nodes[fu_id] = {
                "node_id": fu_id,
                "node_type": "functional_unit",
                "label": fu_id,
                "logic": logic
            }

            for g in genes:
                nodes[g] = {
                    "node_id": g,
                    "node_type": "gene",
                    "label": g,
                    "logic": ""
                }

                entry_to_fu[eid].append(fu_id)

        # --- Group entries → AND FU ---
        for gid, comps in groups.items():
            genes = []
            for cid in comps:
                genes.extend(entries[cid]["genes"])

            fu_id = f"FU_{uuid.uuid4().hex[:8]}"

            nodes[fu_id] = {
                "node_id": fu_id,
                "node_type": "functional_unit",
                "label": fu_id,
                "logic": "AND"
            }

            for g in genes:
                nodes[g] = {
                    "node_id": g,
                    "node_type": "gene",
                    "label": g,
                    "logic": ""
                }

            entry_to_fu[gid].append(fu_id)

        # --- Pathway node ---
        nodes[pathway_id] = {
            "node_id": pathway_id,
            "node_type": "pathway",
            "label": pathway_id,
            "logic": ""
        }

        # -------------------------
        # Build edges
        # -------------------------
        edges = []

        def position_type(position_id):
            return "reaction" if position_id.startswith("rn:") else "node"

        # --- Gene ↔ FU edges ---
        for eid, fus in entry_to_fu.items():
            genes = entries[eid]["genes"]
            pathway_positions = entries[eid]["pathway_positions"]

            for fu in fus:
                for g in genes:
                    for pos in pathway_positions:
                        edges.append({
                            "source": g,
                            "target": fu,
                            "edge_type": "gene_to_FU",
                            "edge_subtype": "",
                            "pathway_position_id": pos,
                            "pathway_position_type": position_type(pos)
                        })

                        edges.append({
                            "source": fu,
                            "target": g,
                            "edge_type": "FU_to_gene",
                            "edge_subtype": "",
                            "pathway_position_id": pos,
                            "pathway_position_type": position_type(pos)
                        })

                # --- FU → pathway ---
                for pos in pathway_positions:
                    edges.append({
                        "source": fu,
                        "target": pathway_id,
                        "edge_type": "FU_to_pathway",
                        "edge_subtype": "",
                        "pathway_position_id": pos,
                        "pathway_position_type": position_type(pos)
                    })

        # --- Relation edges (new part) ---
        for rel in relations:
            src = rel["source"]
            tgt = rel["target"]

            subtypes = "|".join(rel["subtypes"])

            src_positions = entries[src]["pathway_positions"]
            tgt_positions = entries[tgt]["pathway_positions"]

            pathway_positions = list(dict.fromkeys(src_positions + tgt_positions))

            # --- gene ↔ gene ---
            for g1 in entries[src]["genes"]:
                for g2 in entries[tgt]["genes"]:
                    for pos in pathway_positions:
                        edges.append({
                            "source": g1,
                            "target": g2,
                            "edge_type": rel["type"],
                            "edge_subtype": subtypes,
                            "pathway_position_id": pos,
                            "pathway_position_type": position_type(pos)
                        })

            # --- FU ↔ FU ---
            for fu1 in entry_to_fu[src]:
                for fu2 in entry_to_fu[tgt]:
                    for pos in pathway_positions:
                        edges.append({
                            "source": fu1,
                            "target": fu2,
                            "edge_type": rel["type"],
                            "edge_subtype": subtypes,
                            "pathway_position_id": pos,
                            "pathway_position_type": position_type(pos)
                        })

        return list(nodes.values()), edges

    # ------------------------------------------------------------
    # Convert to Orange Table
    # ------------------------------------------------------------

    def to_table(self, rows):
        if not rows:
            return None

        # All columns are strings → use metas
        meta_vars = [StringVariable(k) for k in rows[0].keys()]
        domain = Domain([], metas=meta_vars)

        data = [
            [str(row.get(var.name, "")) for var in meta_vars]
            for row in rows
        ]

        return Table.from_list(domain, data)
