import pyclustering
from pyclustering.cluster.kmedoids import kmedoids
from pyclustering.utils.metric import distance_metric, type_metric
from collections import Counter
from sklearn.metrics import silhouette_samples, silhouette_score
import pandas as pd

#====================================================================================================================

def Initialise(Pathway_row, Pathway_column, Gap, Rank):
    """Initialise the scoring matrix for Modified Needleman-Wunsch Algorithm."""
    # Create empty matrix
    matrix = [[0 for c in range(len(Pathway_column))] for r in range(len(Pathway_row))]

    # Initialise frist row and column with r*gap value
    for r, code_r in enumerate(Pathway_row[1:]):
        matrix[r+1][0] = matrix[r][0] + Gap + Rank[code_r]
    for c, code_c in enumerate(Pathway_column[1:]):
        matrix[0][c+1] = matrix[0][c] + Gap + Rank[code_c]

    return matrix


def Mod_NW(Pathway_row, Pathway_column, Gap, Match, Swap, No_Swap, Rank, Groups):
    """Calculate the Modified Needleman-Wunsh distance between two strings.
    
    Requires a dictionary of rankings and groups with character as key.
    Requires numeric penalty values for gap, match, swap and no swap.
    """
    Pathway_row = ' ' + Pathway_row
    Pathway_column = ' ' + Pathway_column
    matrix = Initialise(Pathway_row, Pathway_column, Gap, Rank)

    for r, code_r in enumerate(Pathway_row[1:]):
        for c, code_c in enumerate(Pathway_column[1:]):
            
            if code_r == code_c:
                Penalty = matrix[r][c] * (Match + 1/(matrix[r][c] + Rank[code_r]))
            elif Groups[code_r] == Groups[code_c]:
                Penalty = matrix[r][c] + Swap + abs(Rank[code_r] - Rank[code_c])
            else:
                Penalty = matrix[r][c] + No_Swap + (Rank[code_r] + Rank[code_c])
                
            Gap_r = matrix[r + 1][c] + Gap + Rank[code_c]
            Gap_c = matrix[r][c + 1] + Gap + Rank[code_r]
            matrix[r + 1][c + 1] = min(Penalty, Gap_r, Gap_c)
    return matrix[-1][-1]

#====================================================================================================================

def traceback(matrix, Pathway_row, Pathway_column):
    """Express string match alignment in terms of gaps (G), swaps (S) and matches (M)."""
    r = len(Pathway_row) - 1
    c = len(Pathway_column) - 1
    Traceback = ''

    while r != 0 or c != 0:
    
        D = matrix[r*2-1][c*2-1]
        L = matrix[r*2][c*2-1]
        U = matrix[r*2-1][c*2]
    
        if min(D,L,U) == L:
            Traceback = 'G' + Traceback
            c -= 1
        if min(D,L,U) == U:
            Traceback = 'G' + Traceback
            r -= 1
        if min(D,L,U) == D:
            r -= 1
            c -= 1
            if Pathway_row[r] == Pathway_column[c]:
                Traceback = 'M' + Traceback
            else:
                Traceback = 'S' + Traceback
    return Traceback

#====================================================================================================================

def Initialise_Full_Matrix(Pathway_row, Pathway_column, Gap, Rank):
    """Initialise the scoring matrix for Needleman-Wunsch Algorithm - Full Matrix."""
    # Create empty matrix
    Length_Pathway_row, Length_Pathway_column = len(Pathway_row), len(Pathway_column)
    matrix = [[0 for c in range(Length_Pathway_column*2-1)] for r in range(Length_Pathway_row*2-1)]

    # Initialise frist row and column with r*gap value
    for r, code_r in enumerate(Pathway_row[1:]):
        matrix[r*2+2][0] = matrix[r*2][0] + Gap + Rank[code_r]
    for c, code_c in enumerate(Pathway_column[1:]):
        matrix[0][c*2+2] = matrix[0][c*2] + Gap + Rank[code_c]
    return matrix

def Mod_NW_Full_Matrix(Pathway_row, Pathway_column, Gap, Match, Swap, No_Swap, Rank, Groups, Traceback):    
    """Calculate the Modified Needleman-Wunsh distance between two strings.
    The full matrix of values will be produced.
    
    Requires a dictionary of rankings and groups with character as key.
    Requires numeric penalty values for gap, match, swap and no swap.
    """
    Pathway_row = ' ' + Pathway_row
    Pathway_column = ' ' + Pathway_column

    matrix = Initialise_Full_Matrix(Pathway_row, Pathway_column, Gap, Rank)

    for r in range(1,len(Pathway_row)):
        for c in range(1,len(Pathway_column)):
            
            if Pathway_row[r] == Pathway_column[c]:
                Penalty = matrix[r*2-2][c*2-2] * (Match + 1/(matrix[r*2-2][c*2-2] + Rank[Pathway_row[r]]))
            elif Groups[Pathway_row[r]] == Groups[Pathway_column[c]]:
                Penalty = matrix[r*2-2][c*2-2] + Swap + abs(Rank[Pathway_row[r]] - Rank[Pathway_column[c]])
            else:
                Penalty = matrix[r*2-2][c*2-2] + No_Swap + (Rank[Pathway_row[r]] + Rank[Pathway_column[c]])
                
            Gap_r = matrix[r*2][c*2-2] + Gap + Rank[Pathway_column[c]]
            Gap_c = matrix[r*2-2][c*2] + Gap + Rank[Pathway_row[r]]
            
            matrix[r*2-1][c*2-1] = Penalty
            matrix[r*2][c*2-1] = Gap_r
            matrix[r*2-1][c*2] = Gap_c
            matrix[r*2][c*2] = min(Penalty, Gap_r, Gap_c)

    if Traceback == True:
        Traceback = traceback(matrix, Pathway_row, Pathway_column)
        return Traceback 
    else:
        return pd.DataFrame(matrix)

