import re
from collections import Counter
from graphviz import Digraph
import pandas as pd
import numpy as np
import statistics
import matplotlib.pyplot as plt
import math
import copy


#===============================================================================================

def counts_from_pathway_data(results_data):
    """Count number of each activity from pathways.
    
    Used in results.
    """
    all_string = ''
    for pathway in results_data:
        all_string += pathway
    list_all = re.findall('.',all_string)
    counts = Counter(list_all)
    return counts


def find_start_activity(letters, pathways, counts, proportion):
    """Count number of times each activity was first activity i.e. arrival activity."""
    pathways = copy.deepcopy(pathways).dropna()
    # include extra for exit node
    Start = [0 for i in range(len(letters)+1)]
    for r, row in enumerate(pathways):
        if proportion == True:
            addition = counts[r]
        else:
            addition = 1
        Start[letters.index(row[0])] += addition
    return Start


def find_transitions(letters, pathways, counts, proportion):
    """Produce transition matrix between activities.
    
    Including activity to exit in final column.
    """
    pathways = copy.deepcopy(pathways).dropna()
    TM = [[0 for i in range(len(letters)+1)] for j in range(len(letters))]
    for r,row in enumerate(pathways):
        if proportion == True:
            addition = counts[r]
        else:
            addition = 1
        for letter in letters:
            if letter in row:
                next_l = row[row.index(letter)+1:row.index(letter) + 2]
                if row[0] == letter:
                    TM[0][letters.index(letter)] += 0
                    if next_l != '':
                        TM[letters.index(letter)][letters.index(next_l)] += addition
                elif next_l == '':
                    TM[letters.index(letter)][len(letters)] += addition
                else:
                    TM[letters.index(letter)][letters.index(next_l)] += addition
    return TM


def convert_to_prob(Matrix):
    """Conver count transition matrix to probability."""
    prob_matrix = [[r/sum(row) if sum(row) != 0 else r for r in row] for row in Matrix]
    return prob_matrix


def adjust_to_1(row):
    """If total sum larger than 1, remove the differnce from largest value."""
    total = sum(row)
    if total > 1:
        largest = max(row)
        replace = row.index(largest)
        row[replace] = largest - (total-1)
    return row
        

def get_transitions(pathways_df, letters, adjust):
    """Produce probability transition matrix.

    + Start: row vector for counts activity was first
    + draw_matrix: Total matrix including start and end nodes for drawing network
    + Matrix_prob: Trnasition matrix between activities only i.e. excludes start and end
    """
    if type(adjust) == float:
        # remove pathways occur < adjust percent of time
        Start = find_start_activity(letters, pathways_df, [1 for i in pathways_df], False)
        TM = find_transitions(letters, pathways_df, [1 for i in pathways_df], False)
        Matrix = [Start] + TM
        percent = sum(Matrix[0])*adjust
        Matrix = [[0 if r < percent else r for r in row] for row in Matrix]
    elif type(adjust) == bool:
        # standard transitions
        Start = find_start_activity(letters, pathways_df, None, False)
        TM = find_transitions(letters, pathways_df, None, False)
        Matrix = [Start] + TM
    else:
        # transitions for process based, adjust is prop_counts
        Start = find_start_activity(letters, pathways_df, adjust, True)
        TM = find_transitions(letters, pathways_df, adjust, True)
        Matrix = [Start] + TM

    Matrix_prob = convert_to_prob(Matrix)
    draw_matrix = copy.deepcopy(Matrix_prob)
    
    # remove start and end nodes
    Matrix_prob.pop(0)
    for row in Matrix_prob:
        row.pop(-1)
    Matrix_prob = [adjust_to_1(row) for row in Matrix_prob]

    return(Start, draw_matrix, Matrix_prob)


#===================== Drawing ===========================

def draw_network(letters, Matrix, file_name, LR, penwidth, round_to):
    """Draws transition network."""
    letters_SE = ['Start'] + letters + ['end']
    Matrix_Draw = copy.deepcopy(Matrix)
    if penwidth == True:
        start_penwidth = str(sj/2)
        TM_penwidth = str(Matrix_Draw[n][m]/2)
    else:
        start_penwidth = str(1)
        TM_penwidth = str(1)

    
    dot = Digraph(format='pdf')
    Start = Matrix_Draw[0]
    for si,sj in enumerate(Start):
        if Start[si] > 0:
            if Start[si] == 1:
                dot.node(letters_SE[si+1], letters_SE[si+1])
                dot.edge(letters_SE[0], letters_SE[si+1], color='grey')
            else:
                dot.node(letters_SE[si+1], letters_SE[si+1])
                dot.edge(letters_SE[0], letters_SE[si+1],label=str(round(sj, round_to)), penwidth=start_penwidth)
    
    del letters_SE[0]
    del Matrix_Draw[0]
    for n,i in enumerate(letters_SE[:-1]):
        for m,j in enumerate(letters_SE):
            if Matrix_Draw[n][m] != 0:
                if Matrix_Draw[n][m] == 1:
                    dot.node(i, i)
                    dot.edge(i,j, color='grey')
                else:
                    dot.node(i, i)
                    dot.edge(i,j,label=str(round(Matrix_Draw[n][m], round_to)), penwidth=TM_penwidth)
    
    if LR == True:
        dot.graph_attr['rankdir'] = 'LR'   

    dot.render(file_name,view=False)


def draw_centroids(centroids_df, column_name, file_name):
    """Draws exact centroid pathways."""
    dot = Digraph(format='pdf')

    for i in range(len(centroids_df)):
        cluster_name = 'cluster_' + str(i)
        L_labels = re.findall('.',centroids_df[column_name][i])  
        L_plotting = [cluster_name + l + str(num) for num, l in enumerate(L_labels)]  
        edge_tuples = [(L_plotting[l], L_plotting[l+1]) for l in range(0, len(L_plotting)-1)]    

        with dot.subgraph(name=cluster_name) as c:
            for lk, lv in enumerate(L_plotting):
                c.node(lv, L_labels[lk])
            c.edges(edge_tuples)
            c.attr(label = cluster_name)

    dot.graph_attr['rankdir'] = 'LR'     
    
    dot.render(file_name,view=False)  


def step_edge(pos, data, all_firsts):
    """Prepares data for draw_centroids_linked.
    
    Groups transitions per position in string and records count.
    """
    edge_counts = [[0 for i in range(len(all_firsts[pos]))] for j in range(len(all_firsts[pos-1]))]
    for row in data:
        current = row[pos-1:pos]
        next = row[pos:pos+1]
        
        if current == '':
            i_coord = all_firsts[pos-1].index('End')
        else:
            i_coord = all_firsts[pos-1].index(current)
        if next == '':
            j_coord = all_firsts[pos].index('End')
        else:
            j_coord = all_firsts[pos].index(next)

        if current =='' and next=='':
            edge_counts[i_coord][j_coord] += 0
        else:
            edge_counts[i_coord][j_coord] += 1
    return edge_counts


def draw_centroids_linked(centroids_df, all_firsts, file_name):    
    """Draws transitions in terms of position in which the activity occurs."""
    dot = Digraph('G')
    previous_plotting = []
    for i in range(len(all_firsts)):
        cluster_name = 'cluster_' + str(i)
        plotting = [cluster_name + l + str(num) for num, l in enumerate(all_firsts[i])]
        edge_tuples = [(plotting[l], plotting[l+1]) for l in range(0, len(plotting)-1)] 

        with dot.subgraph(name=cluster_name) as c:
            c.attr(rank='same')
            for jk, jv in enumerate(all_firsts[i]):
                c.node(plotting[jk], jv)   
            for et in edge_tuples:
                c.edge(et[0], et[1], style="invisible",dir="none")


        if i != 0:
            edge_counts = step_edge(i, centroids_df, all_firsts)
            for xk, xv in enumerate(previous_plotting):
                for yk, yv in enumerate(plotting):
                    if edge_counts[xk][yk] != 0:
                        if edge_counts[xk][yk] == 1:
                            dot.edge(xv, yv,tailport="e", headport="w", constraint='false', color='grey')
                        else:
                            dot.edge(xv, yv, xlabel=str(edge_counts[xk][yk]), tailport="e", headport="w", constraint='false')
        previous_plotting = plotting


    dot.attr(splines='line')
    dot.graph_attr['rankdir'] = 'TB'  

    dot.render(file_name,view=False)


#=======================================================================================================================

def sim_unique_pathway(df_recs, patient_number, letters, finished):
    """Get pathway string from nodes in simulation data."""
    if finished == True:
        finished_patient_records = df_recs[df_recs['destination'] == -1]
        finished_patient_number = list(finished_patient_records['id_number'])
        if not patient_number in finished_patient_number:
            return
         
    patient_records = df_recs[df_recs['id_number'] == patient_number]
    patient_nodes = list(patient_records['node'])
    end_destination = list(patient_records['destination'])[-1]
    unique_pathway = [letters[_ - 1] for _ in patient_nodes]
    if end_destination != -1: 
        unique_pathway = unique_pathway + ['..']
    unique_pathway = ''.join(unique_pathway)
    
    totaltime = int(patient_records['service_start_date'].max()) - int(patient_records['arrival_date'].min())
    customer_class = list(patient_records.customer_class)[0]

    return([patient_number, unique_pathway, totaltime, customer_class])


def convert_records(Q, letters, finished):
    """Convert format of ciw records to reflect the input data."""
    recs = Q.get_all_records()
    df_recs = pd.DataFrame(recs)
    df_recs['waiting_days'] = [int(df_recs.loc[i, "service_start_date"]) - int(df_recs.loc[i, "arrival_date"]) for i in range(len(df_recs))]
    df_recs2 = df_recs.groupby(['id_number', 'node']).agg(lambda x: x.tolist()).reset_index()
    df_recs2 = df_recs2.pivot(index='id_number', columns='node', values='waiting_days').fillna(' ')   
    df_recs2.columns = [letters[c-1] for c in df_recs2.columns]
    
    sim_waiting_colums = [column for column in df_recs2.columns]
    list_patient_numbers = list(set(df_recs['id_number']))    

    all_unique_pathways = []
    for patient_number in list_patient_numbers:
        all_unique_pathways.append(sim_unique_pathway(df_recs, patient_number, letters, finished=finished))
    all_unique_pathways = [x for x in all_unique_pathways if x]

    return(df_recs2, all_unique_pathways, sim_waiting_colums)


def sim_results(df_recs2, all_unique_pathways):
    """Combine desired ciw output with converted results."""
    df_all_unique_pathways = pd.DataFrame.from_records(all_unique_pathways)
    df_all_unique_pathways.columns = ['id_number', 'pathway', 'totaltime', 'customer_class']
    df_all = pd.merge(df_recs2, df_all_unique_pathways, how='right', on='id_number')
    return(df_all)

#=======================================================================================================================


def transitions_compare(save_location, simulation_name, original_transitions, simulation_transitions):
    """Compute the difference matrix between two transition matricies."""
    difference_matrix = [[a-b for a,b in zip(original_transitions[j],simulation_transitions[j])] for j in range(len(original_transitions))]
    difference_matrix_df = pd.DataFrame(difference_matrix)
    with pd.ExcelWriter(save_location + 'Simulation_Difference_Matrix.xlsx', engine="openpyxl", mode='a') as writer:
        difference_matrix_df.to_excel(writer,simulation_name)

    abs_difference_matrix = [[abs(a-b) for a,b in zip(original_transitions[j],simulation_transitions[j])] for j in range(len(original_transitions))]
    difference_value = sum(sum(abs_difference_matrix,[]))
    return(abs_difference_matrix, difference_value)


def initial_last_arrival(df_full, intervention_codes, formatted):
    """Get the arrival day for the last individual arrived."""
    if formatted == True:
        # double code
        Start_code = [df_full['multi_pathways'][i][0:2] for i in range(len(df_full))]
    else:
        Start_code = [df_full['pathways'][i][0] for i in range(len(df_full))]
    Start_activity = [intervention_codes[code] for code in Start_code]
    Start_dates = [df_full[Start_activity[i]][i] for i in range(len(df_full))]
    df_start = pd.DataFrame({'Start_dates': Start_dates})

    return df_start

#========================================================================================

def pathway_counts(data):
    """
    Gets frequency count for each pathway
    """
    pathway_counts = pd.DataFrame(data.pathways.value_counts())
    pathway_counts.reset_index(level=0, inplace=True)
    pathway_counts.columns = ['pathway', 'counts']
    # ensures order is allways the same
    # order will be by counts, if counts the same then reverse alphabetical
    pathway_counts= pathway_counts.sort_values(by=['counts', 'pathway'], ascending=False)
    pathway_counts.reset_index(level=0, inplace=True, drop=True)
    
    return pathway_counts


def propergate_clusters(pathway_counts, clusters_NWA):
    """Propergate cluster results by number of times pathway occurs."""
    propergated_clusters_index = []
    propergated_clusters = []

    for i, cluster in enumerate(clusters_NWA):
        prop_cluster_index = [[index]*pathway_counts['counts'].iloc[index] for index in cluster]
        red_cluster_index = [index for list_of_index in prop_cluster_index for index in list_of_index]

        prop_cluster_foot = [[pathway_counts['pathway'].iloc[index]]*pathway_counts['counts'].iloc[index] for index in cluster]
        red_cluster_foot = [index for list_of_index in prop_cluster_foot for index in list_of_index]

        propergated_clusters_index.append(red_cluster_index)
        propergated_clusters.append(red_cluster_foot)   
        
    return propergated_clusters