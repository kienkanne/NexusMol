from pathlib import Path


def matchmixer(prepped_recs, prepped_ligs, prepped_suffix, mode="mix"):
    pairs = []
    if mode == "mix":
        for prepped_rec in prepped_recs:
            for prepped_lig in prepped_ligs:
                pairs.append((prepped_rec, prepped_lig))

    # Disable validate for now
    elif mode == "match":
        rec_dict = {prepped_rec: _name_from_prepped(prepped_rec, prepped_suffix) for prepped_rec in prepped_recs}
        lig_dict_inverted = {_name_from_prepped(prepped_lig, prepped_suffix): prepped_lig for prepped_lig in prepped_ligs}

        for rec, name in rec_dict.items():
            if name in lig_dict_inverted:
                pairs.append((rec, lig_dict_inverted[name]))

    return pairs


def _to_path(item):
    if hasattr(item, "receptor"):
        return Path(item.receptor)
    if isinstance(item, (list, tuple)) and item:
        return Path(item[0])
    return Path(item)


def _name_from_prepped(item, suffix):
    from nexus.dock.utils._strip_prepared_suffix import _strip_prepared_suffix
    return _strip_prepared_suffix(str(_to_path(item)), suffix)