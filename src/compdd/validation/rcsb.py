from pathlib import Path
import json
import urllib.request

from compdd.validation.casf import UnsupportedLigandError


class RCSBClient:
    base_url = "https://data.rcsb.org/rest/v1/core"

    def __init__(self, cache_dir, fetch_json=None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fetch_json = fetch_json or self._fetch_json

    def _fetch_json(self, url):
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _cached_json(self, cache_name, url):
        path = self.cache_dir / cache_name
        if path.is_file():
            with open(path) as handle:
                return json.load(handle)

        data = self.fetch_json(url)
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w") as handle:
            json.dump(data, handle, indent=2)
        tmp_path.replace(path)
        return data

    def entry(self, entry_id):
        entry_id = entry_id.lower()
        return self._cached_json(
            f"{entry_id}_entry.json",
            f"{self.base_url}/entry/{entry_id}",
        )

    def nonpolymer_entity(self, entry_id, entity_id):
        entry_id = entry_id.lower()
        return self._cached_json(
            f"{entry_id}_nonpolymer_{entity_id}.json",
            f"{self.base_url}/nonpolymer_entity/{entry_id}/{entity_id}",
        )

    def chemcomp(self, comp_id):
        comp_id = comp_id.upper()
        return self._cached_json(
            f"chemcomp_{comp_id}.json",
            f"{self.base_url}/chemcomp/{comp_id}",
        )

    def ligand_metadata(self, entry_id, ligand_id):
        entry = self.entry(entry_id)
        entity_ids = entry.get("rcsb_entry_container_identifiers", {}).get("non_polymer_entity_ids", [])
        matches = []

        for entity_id in entity_ids:
            entity = self.nonpolymer_entity(entry_id, entity_id)
            comp_id = _extract_comp_id(entity)
            if comp_id and comp_id.upper() == ligand_id.upper():
                chemcomp = self.chemcomp(comp_id)
                smiles = _extract_canonical_smiles(chemcomp)
                if smiles:
                    matches.append({
                        "entry_id": entry_id.lower(),
                        "entity_id": str(entity_id),
                        "ligand_id": comp_id.upper(),
                        "name": _extract_name(entity) or _extract_name(chemcomp),
                        "smiles": smiles,
                    })

        if len(matches) != 1:
            raise UnsupportedLigandError(
                f"Expected one clear RCSB non-polymer match for {entry_id}:{ligand_id}; found {len(matches)}"
            )
        return matches[0]


def _extract_comp_id(entity):
    paths = [
        ("pdbx_entity_nonpoly", "comp_id"),
        ("nonpolymer_comp", "chem_comp", "id"),
        ("rcsb_nonpolymer_entity_container_identifiers", "chem_comp_id"),
        ("rcsb_nonpolymer_entity_container_identifiers", "nonpolymer_comp_id"),
        ("rcsb_nonpolymer_entity_container_identifiers", "chem_ref_def_id"),
        ("chem_comp", "id"),
    ]
    for path in paths:
        value = entity
        for key in path:
            value = value.get(key, {}) if isinstance(value, dict) else {}
        if isinstance(value, str) and value:
            return value
    return None


def _extract_name(entity):
    comp = entity.get("nonpolymer_comp", {}) if isinstance(entity, dict) else {}
    chem_comp = comp.get("chem_comp", {}) if isinstance(comp, dict) else {}
    return chem_comp.get("name") or chem_comp.get("pdbx_synonyms") or ""


def _iter_descriptors(obj):
    if isinstance(obj, dict):
        if "descriptor" in obj and "type" in obj:
            yield obj
        for value in obj.values():
            yield from _iter_descriptors(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_descriptors(item)


def _extract_canonical_smiles(entity):
    descriptors = list(_iter_descriptors(entity))
    preferred = []
    fallback = []

    for descriptor in descriptors:
        dtype = str(descriptor.get("type", "")).upper()
        program = str(descriptor.get("program", "")).upper()
        value = descriptor.get("descriptor")
        if not value:
            continue
        if "SMILES_CANONICAL" in dtype and "OPENEYE" in program:
            preferred.append(value)
        elif "SMILES_CANONICAL" in dtype:
            fallback.append(value)
        elif dtype == "SMILES":
            fallback.append(value)

    if preferred:
        return preferred[0]
    if fallback:
        return fallback[0]
    return None
