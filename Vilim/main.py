import graphs as g

G1 = g.get_map("sample_map")

g.KaFFPa(
    G1, 
    k=144,
    check_format=False,
    imbalance=3
)

g.print_map(G1, color="color", label="population")