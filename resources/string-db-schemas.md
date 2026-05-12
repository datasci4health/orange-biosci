# STING-db Interaction Data

* Download from: https://string-db.org/cgi/download.pl

## Summary

### Interaction Data

File | Description
-----|------------
9606.protein.links.v12.0.txt.gz | protein network data (full network, scored links between proteins)
9606.protein.links.detailed.v12.0.txt.gz | protein network data (full network, incl. subscores per channel)
9606.protein.links.full.v12.0.txt.gz | protein network data (full network, incl. distinction: direct vs. interologs)
9606.protein.physical.links.v12.0.txt.gz | protein network data (physical subnetwork, scored links between proteins)
9606.protein.physical.links.detailed.v12.0.txt.gz | protein network data (physical subnetwork, incl. subscores per channel)
9606.protein.physical.links.full.v12.0.txt.gz | protein network data (physical subnetwork, incl. distinction: direct vs. interologs)

### Accessory Data

File | Description
-----|------------
9606.protein.aliases.v12.0.txt.gz | aliases for STRING proteins: locus names, accessions, descriptions...

## Details

### Interaction Data

#### 9606.protein.links.v12.0.txt.gz

```
protein1 protein2 combined_score
9606.ENSP00000000233 9606.ENSP00000356607 173
9606.ENSP00000000233 9606.ENSP00000427567 154
9606.ENSP00000000233 9606.ENSP00000253413 151
```

#### 9606.protein.links.detailed.v12.0.txt.gz

```
protein1 protein2 neighborhood fusion cooccurence coexpression experimental database textmining combined_score
9606.ENSP00000000233 9606.ENSP00000356607 0 0 0 45 134 0 81 173
9606.ENSP00000000233 9606.ENSP00000427567 0 0 0 0 128 0 70 154
9606.ENSP00000000233 9606.ENSP00000253413 0 0 0 118 49 0 69 151
```

#### 9606.protein.links.full.v12.0.txt.gz

```
protein1 protein2 neighborhood neighborhood_transferred fusion cooccurence homology coexpression coexpression_transferred experiments experiments_transferred database database_transferred textmining textmining_transferred combined_score
9606.ENSP00000000233 9606.ENSP00000356607 0 0 0 0 0 0 45 0 134 0 0 0 81 173
9606.ENSP00000000233 9606.ENSP00000427567 0 0 0 0 0 0 0 0 128 0 0 0 70 154
9606.ENSP00000000233 9606.ENSP00000253413 0 0 0 0 0 49 111 0 49 0 0 0 69 151
```

#### 9606.protein.physical.links.v12.0.txt.gz

```
protein1 protein2 combined_score
9606.ENSP00000000233 9606.ENSP00000257770 311
9606.ENSP00000000233 9606.ENSP00000226004 161
9606.ENSP00000000233 9606.ENSP00000434442 499
```

#### 9606.protein.physical.links.detailed.v12.0.txt.gz

```
protein1 protein2 experimental database textmining combined_score
9606.ENSP00000000233 9606.ENSP00000257770 312 0 0 311
9606.ENSP00000000233 9606.ENSP00000226004 162 0 0 161
9606.ENSP00000000233 9606.ENSP00000434442 0 500 0 499
```

#### 9606.protein.physical.links.full.v12.0.txt.gz

```
protein1 protein2 homology experiments experiments_transferred database database_transferred textmining textmining_transferred combined_score
9606.ENSP00000000233 9606.ENSP00000257770 0 312 0 0 0 0 0 311
9606.ENSP00000000233 9606.ENSP00000226004 0 162 0 0 0 0 0 161
9606.ENSP00000000233 9606.ENSP00000434442 0 0 0 500 0 0 0 499
```

### Accessory Data

#### 9606.protein.aliases.v12.0.txt.gz

```
#string_protein_id	alias	source
9606.ENSP00000000233	2B6H	Ensembl_PDB
9606.ENSP00000000233	2B6H	UniProt_DR_PDB
9606.ENSP00000000233	381	Ensembl_HGNC_entrez_id
```
