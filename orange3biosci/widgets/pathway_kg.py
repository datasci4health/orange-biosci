import os
import uuid
from collections import defaultdict
from importlib.resources import files

from AnyQt.QtCore import QTimer
from AnyQt.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton

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
    resizing_enabled = False

    class Outputs:
        nodes = widget.Output("Nodes", Table)
        edges = widget.Output("Edges", Table)

    class Error(widget.OWWidget.Error):
        file_error = widget.Msg("{}")

    want_main_area = False

    filename = Setting("")
    relative_to_workflow = Setting(False)
    auto_extract = Setting(False)
    aggregate_functional_units = Setting(True)

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------

    def __init__(self):
        super().__init__()

        box = gui.widgetBox(self.controlArea, "KGML File")

        self.file_edit = QLineEdit()
        self.file_edit.setText(self.filename)
        self.file_edit.textChanged.connect(self.on_file_changed)
        self.file_edit.editingFinished.connect(self.on_file_edit_finished)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_button)
        gui.widgetBox(box).layout().addLayout(file_layout)

        gui.checkBox(
            box, self, "relative_to_workflow", "Relative to Workflow File",
            callback=self.on_relative_path_changed
        )

        gui.checkBox(
            self.controlArea, self, "aggregate_functional_units",
            "Aggregate Functional Units",
            callback=self.on_aggregate_functional_units_changed
        )

        actions_box = gui.widgetBox(self.controlArea, orientation="horizontal")
        self.extract_button = gui.button(
            actions_box, self, "Extract KG", callback=self.process
        )
        gui.checkBox(
            actions_box, self, "auto_extract", "Extract Automatically",
            callback=self.on_auto_extract_changed
        )

        # self.setFixedSize(self.layout().sizeHint())
        self.adjustSize()

        if self.auto_extract and self.filename:
            QTimer.singleShot(0, self.process)

    def browse_file(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open Pathway File", "", "KGML files (*.xml *.kgml);;BioPAX files (*.xml *.owl *.bp *.biopax);;All files (*)"
        )
        if fname:
            if self.relative_to_workflow:
                fname = self.make_relative_path(fname)
            self.filename = fname
            self.file_edit.setText(fname)
            self.setStatusMessage(os.path.basename(fname))
            if self.auto_extract:
                self.process()

    def on_file_changed(self):
        self.filename = self.file_edit.text()

    def on_file_edit_finished(self):
        if self.auto_extract:
            self.process()

    def on_relative_path_changed(self):
        if not self.filename:
            return

        if self.relative_to_workflow:
            self.filename = self.make_relative_path(self.filename)
        else:
            self.filename = self.get_absolute_path(self.filename)
        self.file_edit.setText(self.filename)

    def on_auto_extract_changed(self):
        if self.auto_extract:
            self.process()

    def on_aggregate_functional_units_changed(self):
        if self.auto_extract:
            self.process()

    def make_relative_path(self, path):
        workflow_dir = self.workflowEnv().get("basedir", "")
        if workflow_dir and os.path.isabs(path):
            try:
                return os.path.relpath(path, workflow_dir)
            except ValueError:
                pass
        return path

    def get_absolute_path(self, path):
        if path and not os.path.isabs(path):
            workflow_dir = self.workflowEnv().get("basedir", "")
            if workflow_dir:
                return os.path.abspath(os.path.join(workflow_dir, path))
        return path

    def current_filename(self):
        return self.get_absolute_path(self.filename)

    # ------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------

    def process(self):
        self.Error.clear()

        if not self.filename:
            self.Outputs.nodes.send(None)
            self.Outputs.edges.send(None)
            return

        filename = self.current_filename()
        try:
            tree = etree.parse(filename)
        except (OSError, etree.XMLSyntaxError) as exc:
            self.Outputs.nodes.send(None)
            self.Outputs.edges.send(None)
            self.Error.file_error(str(exc))
            return

        root = tree.getroot()

        if root.tag == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF":
            pathway_id, entries, groups, relations = self.parse_biopax(root)
        else:
            pathway_id, entries, groups, relations = self.parse_kegg(root)

        nodes, edges = self.build_graph_from_data(
            pathway_id, entries, groups, relations, self.aggregate_functional_units
        )

        self.Outputs.nodes.send(self.to_table(nodes))
        self.Outputs.edges.send(self.to_table(edges))
        self.setStatusMessage(os.path.basename(filename))

    # ------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------

    def parse_kegg(self, root):
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

        return pathway_id, entries, groups, relations

    def parse_biopax(self, root):
        entries = {}
        groups = {}
        relations = []

        bp = "http://www.biopax.org/release/biopax-level3.owl#"
        rdf = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        ns = {"bp": bp, "rdf": rdf}

        # Pathway
        pathways = root.findall("bp:Pathway", ns)
        if pathways:
            pid = pathways[0].get(f"{{{rdf}}}about") or pathways[0].get(f"{{{rdf}}}ID")
            if pid:
                if pid.startswith("#"): pid = pid[1:]
                pathway_id = pid.split("#")[-1]
            else:
                pathway_id = "pathway"
        else:
            pathway_id = "pathway"

        # Physical Entities (treat as gene)
        for entity_type in ["Protein", "Dna", "Rna", "SmallMolecule", "PhysicalEntity"]:
            for elem in root.findall(f"bp:{entity_type}", ns):
                eid = elem.get(f"{{{rdf}}}about") or elem.get(f"{{{rdf}}}ID")
                if not eid: continue
                if eid.startswith("#"): eid = eid[1:]

                name_elem = elem.find("bp:displayName", ns)
                if name_elem is None:
                    name_elem = elem.find("bp:standardName", ns)
                name = name_elem.text if name_elem is not None else eid.split("#")[-1]

                entries[eid] = {
                    "id": eid,
                    "type": "gene",
                    "name": name,
                    "genes": [name],
                    "reactions": [],
                    "pathway_positions": [eid]
                }

        # Complexes (treat as group)
        for elem in root.findall("bp:Complex", ns):
            gid = elem.get(f"{{{rdf}}}about") or elem.get(f"{{{rdf}}}ID")
            if not gid: continue
            if gid.startswith("#"): gid = gid[1:]

            comps = []
            for comp in elem.findall("bp:component", ns):
                res = comp.get(f"{{{rdf}}}resource")
                if res:
                    if res.startswith("#"): res = res[1:]
                    comps.append(res)

            groups[gid] = comps

        # Relations (BiochemicalReaction)
        for elem in root.findall("bp:BiochemicalReaction", ns):
            lefts = []
            for e in elem.findall("bp:left", ns):
                r = e.get(f"{{{rdf}}}resource")
                if r:
                    if r.startswith("#"): r = r[1:]
                    lefts.append(r)
            rights = []
            for e in elem.findall("bp:right", ns):
                r = e.get(f"{{{rdf}}}resource")
                if r:
                    if r.startswith("#"): r = r[1:]
                    rights.append(r)

            subtypes = []
            name_elem = elem.find("bp:displayName", ns)
            if name_elem is not None and name_elem.text:
                name_lower = name_elem.text.lower()
                if "phosphorylat" in name_lower: subtypes.append("phosphorylation")
                if "dephosphorylat" in name_lower: subtypes.append("dephosphorylation")
                if "ubiquitinat" in name_lower and "deubiquitinat" not in name_lower: subtypes.append("ubiquitination")
                if "deubiquitinat" in name_lower: subtypes.append("deubiquitination")
                if "methylat" in name_lower and "demethylat" not in name_lower: subtypes.append("methylation")
                if "demethylat" in name_lower: subtypes.append("demethylation")
                if "acetylat" in name_lower and "deacetylat" not in name_lower: subtypes.append("acetylation")
                if "deacetylat" in name_lower: subtypes.append("deacetylation")

            for l in lefts:
                for r in rights:
                    relations.append({
                        "source": l,
                        "target": r,
                        "type": "biochemical_reaction",
                        "subtypes": subtypes
                    })

        # Relations (Control)
        for ctrl_type in ["Control", "Catalysis", "Modulation", "TemplateReactionRegulation"]:
            for elem in root.findall(f"bp:{ctrl_type}", ns):
                controllers = []
                for e in elem.findall("bp:controller", ns):
                    r = e.get(f"{{{rdf}}}resource")
                    if r:
                        if r.startswith("#"): r = r[1:]
                        controllers.append(r)
                controlleds = []
                for e in elem.findall("bp:controlled", ns):
                    r = e.get(f"{{{rdf}}}resource")
                    if r:
                        if r.startswith("#"): r = r[1:]
                        controlleds.append(r)

                ctrl_type_elem = elem.find("bp:controlType", ns)
                ctrl_subtype = []
                if ctrl_type_elem is not None and ctrl_type_elem.text:
                    ctrl_subtype.append(ctrl_type_elem.text.lower())

                for c in controllers:
                    for d in controlleds:
                        relations.append({
                            "source": c,
                            "target": d,
                            "type": ctrl_type.lower(),
                            "subtypes": ctrl_subtype
                        })

        return pathway_id, entries, groups, relations

    def build_graph_from_data(self, pathway_id, entries, groups, relations, aggregate_functional_units=True):

        def get_genes(cid, visited=None):
            if visited is None:
                visited = set()
            if cid in visited:
                return []
            visited.add(cid)
            
            if cid in groups:
                res = []
                for child in groups[cid]:
                    res.extend(get_genes(child, visited))
                return res
            elif cid in entries:
                return entries[cid]["genes"]
            return []

        # -------------------------
        # Build nodes
        # -------------------------
        nodes = {}
        entry_to_fu = defaultdict(list)
        entry_to_genes = defaultdict(list)

        # --- Gene entries → FU ---
        for eid, e in entries.items():
            if e["type"] != "gene":
                continue

            genes = e["genes"]
            if not genes:
                continue
            entry_to_genes[eid] = genes

            for g in genes:
                nodes[g] = {
                    "node_id": g,
                    "node_type": "gene",
                    "label": g
                }
                if aggregate_functional_units:
                    nodes[g]["logic"] = ""

            if aggregate_functional_units:
                logic = "OR" if len(genes) > 1 else "SINGLE"
                fu_id = f"FU_{uuid.uuid4().hex[:8]}"

                # FU node
                nodes[fu_id] = {
                    "node_id": fu_id,
                    "node_type": "functional_unit",
                    "label": fu_id,
                    "logic": logic
                }

                entry_to_fu[eid].append(fu_id)

        # --- Group entries → AND FU ---
        for gid, comps in groups.items():
            genes = []
            for cid in comps:
                genes.extend(get_genes(cid))
            entry_to_genes[gid] = genes

            for g in genes:
                nodes[g] = {
                    "node_id": g,
                    "node_type": "gene",
                    "label": g
                }
                if aggregate_functional_units:
                    nodes[g]["logic"] = ""

            if aggregate_functional_units:
                fu_id = f"FU_{uuid.uuid4().hex[:8]}"

                nodes[fu_id] = {
                    "node_id": fu_id,
                    "node_type": "functional_unit",
                    "label": fu_id,
                    "logic": "AND"
                }

                entry_to_fu[gid].append(fu_id)

        # --- Pathway node ---
        nodes[pathway_id] = {
            "node_id": pathway_id,
            "node_type": "pathway",
            "label": pathway_id
        }
        if aggregate_functional_units:
            nodes[pathway_id]["logic"] = ""

        # -------------------------
        # Build edges
        # -------------------------
        edges = []
        gene_pathway_candidates = {
            (gene, pos)
            for eid, genes in entry_to_genes.items()
            for gene in genes
            for pos in entries.get(eid, {}).get("pathway_positions", [eid])
        }
        gene_fu_pathway_positions = set()

        # --- Gene → FU and FU → pathway edges ---
        if aggregate_functional_units:
            for eid, fus in entry_to_fu.items():
                genes = entry_to_genes[eid]
                pathway_positions = entries.get(eid, {}).get("pathway_positions", [eid])

                for fu in fus:
                    for g in genes:
                        edges.append({
                            "source": g,
                            "target": fu,
                            "edge_type": "gene_to_FU",
                            "edge_subtype": "",
                            "pathway_position_id": ""
                        })

                    # --- FU → pathway ---
                    for pos in pathway_positions:
                        edges.append({
                            "source": fu,
                            "target": pathway_id,
                            "edge_type": "FU_to_pathway",
                            "edge_subtype": "",
                            "pathway_position_id": pos
                        })
                        for g in genes:
                            gene_fu_pathway_positions.add((g, pos))

        for gene, pos in sorted(gene_pathway_candidates - gene_fu_pathway_positions):
            edges.append({
                "source": gene,
                "target": pathway_id,
                "edge_type": "gene_to_pathway",
                "edge_subtype": "",
                "pathway_position_id": pos
            })

        # --- Relation edges ---
        for rel in relations:
            src = rel["source"]
            tgt = rel["target"]

            subtypes = "|".join(rel["subtypes"])

            if aggregate_functional_units and entry_to_fu[src] and entry_to_fu[tgt]:
                # --- FU ↔ FU ---
                for fu1 in entry_to_fu[src]:
                    for fu2 in entry_to_fu[tgt]:
                        edges.append({
                            "source": fu1,
                            "target": fu2,
                            "edge_type": rel["type"],
                            "edge_subtype": subtypes,
                            "pathway_position_id": ""
                        })
            else:
                # --- gene ↔ gene ---
                for g1 in entry_to_genes[src]:
                    for g2 in entry_to_genes[tgt]:
                        edges.append({
                            "source": g1,
                            "target": g2,
                            "edge_type": rel["type"],
                            "edge_subtype": subtypes,
                            "pathway_position_id": ""
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
