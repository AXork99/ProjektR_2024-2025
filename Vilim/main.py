import graphs

from graphs import sample

graphs.print_map(
    graphs.init_partition(sample, 7, by = "population"),	 
    label="population"
)

for node, data in sample.nodes(data=True):
    print(node, data["part"])