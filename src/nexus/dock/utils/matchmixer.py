def matchmixer(prepped_recs, prepped_ligs):
    pairs = []
    for prepped_rec in prepped_recs:
        for prepped_lig in prepped_ligs:
            pairs.append((prepped_rec, prepped_lig))

    return pairs