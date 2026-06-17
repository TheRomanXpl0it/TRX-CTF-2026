import numpy as np
from scipy.linalg import ldl


print("-------------------------- [SOLVE] --------------------------")
A = np.array([
    [    -26.,  -182.,   -130.,  -1196.,   -962.,   -130.,   -598.,   -468.,    676.],
    [  -182.,  -1235.,   -481.,  -7397.,  -4979.,  -2041.,  -5161.,  -2574.,   5434.],
    [  -130.,   -481.,   4075.,   4571.,  14345., -12899., -13541.,   5490.,  11132.],
    [ -1196.,  -7397.,   4571., -25577.,   4297., -40273., -57397.,  -6660.,  47254.],
    [  -962.,  -4979.,  14345.,   4297.,  52989., -68137., -79919.,  18920.,  47288.],
    [  -130.,  -2041., -12899., -40273., -68137.,  57938.,  23237., -45137.,  12762.],
    [  -598.,  -5161., -13541., -57397., -79919.,  23237.,  21983.,  42538., -58136.],
    [  -468.,  -2574.,   5490.,  -6660.,  18920., -45137.,  42538., -21769.,   -1316.],
    [   676,   5434,   11132,   47254,   47288,   12762,   -58136,   -1316,    3116.]])

offset = -77 
N = 9



# -------------------- CUSTOM ldl -------------------- 

def ldlt_decomposition(A):
    """
    Performs LDL^T decomposition on a symmetric matrix A.
    A = L @ D @ L.T
    """
    n = A.shape[0]
    L = np.eye(n)  # Initialize L as Identity (diagonal 1s)
    D = np.zeros((n, n))
    
    for j in range(n):
        # Calculate D[j, j]
        # Formula: D_jj = A_jj - sum_{k=0 to j-1} L_jk^2 * D_kk
        sum_d = sum(L[j, k]**2 * D[k, k] for k in range(j))
        D[j, j] = A[j, j] - sum_d
        
        # Calculate L[i, j] for i > j
        # Formula: L_ij = (1/D_jj) * (A_ij - sum_{k=0 to j-1} L_ik * L_jk * D_kk)
        for i in range(j + 1, n):
            sum_l = sum(L[i, k] * L[j, k] * D[k, k] for k in range(j))
            L[i, j] = (A[i, j] - sum_l) / D[j, j]
            
    return L, D


L, D, perm = ldl(A)
P = np.eye(N)[perm]
# L, D = ldlt_decomposition(A)
# print("Permutation matrix L:")
# print(L)
# print("Diagonal matrix D:")
# print(D)


flag = ""
for i, row in enumerate(P@L):
    for j, val in enumerate(row):
        if i > j:
            flag += chr(int(val - offset))

for i in range(N):
    x = D[i][i] - offset
    flag += chr(int(x))
print("Retrieved flag:", flag)