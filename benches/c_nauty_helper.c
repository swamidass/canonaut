#include <nauty.h>

/*
 * Thin wrapper around densenauty for benchmarking against canonaut.
 *
 * g      : input graph  (n*m setwords, MSB-0 adjacency bit-matrix)
 * lab    : pre-allocated int[n]   (filled by nauty: canonical labeling)
 * ptn    : pre-allocated int[n]   (re-initialised by nauty: defaultptn=TRUE)
 * orbits : pre-allocated int[n]   (filled by nauty: orbit indices)
 * canong : pre-allocated graph[n*m] (canonical graph output)
 * m      : setwords per row  (= ceil(n/WORDSIZE))
 * n      : number of vertices
 */
void c_nauty_dense_canonize(
    graph *g,
    int *lab, int *ptn, int *orbits,
    graph *canong,
    int m, int n
) {
    DEFAULTOPTIONS_GRAPH(opts);
    opts.getcanon = TRUE;
    statsblk stats;
    densenauty(g, lab, ptn, orbits, &opts, &stats, m, n, canong);
}
