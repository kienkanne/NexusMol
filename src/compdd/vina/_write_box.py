def _write_box(center, size):
    cx, cy, cz = center
    sx, sy, sz = size

    hx = sx / 2
    hy = sy / 2
    hz = sz / 2

    corners = [
        (cx - hx, cy - hy, cz - hz),  # 1
        (cx + hx, cy - hy, cz - hz),  # 2
        (cx + hx, cy - hy, cz + hz),  # 3
        (cx - hx, cy - hy, cz + hz),  # 4
        (cx - hx, cy + hy, cz - hz),  # 5
        (cx + hx, cy + hy, cz - hz),  # 6
        (cx + hx, cy + hy, cz + hz),  # 7
        (cx - hx, cy + hy, cz + hz),  # 8
    ]

    atom_names = ["DUA", "DUB", "DUC", "DUD",
                  "DUE", "DUF", "DUG", "DUH"]

    conect = [
        (1, 2, 4, 5),
        (2, 1, 3, 6),
        (3, 2, 4, 7),
        (4, 1, 3, 8),
        (5, 1, 6, 8),
        (6, 2, 5, 7),
        (7, 3, 6, 8),
        (8, 4, 5, 7),
    ]

    with open("rec_box.pdb", "w") as f:

        f.write("HEADER    CORNERS OF BOX\n")
        f.write(
            f"REMARK    CENTER (X Y Z)"
            f"{cx:10.3f}{cy:8.3f}{cz:8.3f}\n"
        )

        f.write(
            f"REMARK    DIMENSIONS (X Y Z)"
            f"{sx:10.3f}{sy:8.3f}{sz:8.3f}\n"
        )

        for i, ((x, y, z), atom_name) in enumerate(zip(corners, atom_names), start=1):

            line = (
                f"ATOM  {i:5d} {atom_name:<4} BOX A   1    "
                f"{x:8.3f}{y:8.3f}{z:8.3f}"
                f"  1.00  0.00\n"
            )

            f.write(line)

        for c in conect:
            line = "CONECT" + "".join(f"{x:5d}" for x in c)
            f.write(line + "\n")