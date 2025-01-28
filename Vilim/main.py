import graphs

from graphs import sample

graphs.print_map(
    graphs.init_partition(sample, 11, by = "population"),	 
    label="population"
)