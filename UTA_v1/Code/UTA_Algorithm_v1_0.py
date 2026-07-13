"""
UTA Algorithm v1.0
Uncertainty Transformation Analysis

Author: Martin Pitre
Version: 1.0

Formula:
U_new = U_old - R + C + S - M
"""

def uta(U_old, R, C, S, M):
    """
    U_old = starting uncertainty
    R = uncertainty reduced
    C = uncertainty created
    S = uncertainty split into branches
    M = uncertainty merged/resolved together
    """
    U_new = U_old - R + C + S - M
    return U_new

if __name__ == "__main__":
    print("U_new =", uta(10, 4, 2, 1, 3))
