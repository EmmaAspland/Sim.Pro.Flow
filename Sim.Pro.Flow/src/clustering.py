import numpy as np
import pandas as pd
from pyclustering.cluster.kmedoids import kmedoids
from pyclustering.utils.metric import distance_metric, type_metric
from sklearn.metrics import silhouette_samples, silhouette_score
from collections import Counter
import matplotlib.pyplot as plt
import imp

import wx
import wx.lib.scrolledpanel as scrolled

transitions = imp.load_source('transitions', 'src/transitions.py')

class ClusterFrame(wx.Frame):
    """
    Frame to display clustering reaults.
    """
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, 'All Cluster Information')
        self.panel = scrolled.ScrolledPanel(self)
        vbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add(wx.StaticLine(self.panel, size=(-1, 5000)), 0, wx.ALL, 5)
        hbox = wx.BoxSizer(wx.VERTICAL)
        hbox.Add(wx.StaticLine(self.panel, size=(5000, -1)), 0, wx.ALL, 5)
        vbox.Add(hbox)
        self.panel.SetSizer(vbox)

        self.panel.SetupScrolling()
        self.panel.SetSizer(vbox)

        self.SetSize((600, 500))
        self.Centre()

#======== Classic ================

def cluster_results(cframe, y, k, set_medoids, medoids, pathways_medoids, Frequency, Score):
    """
    Generate static text to display clustering results.
    """
    x = 20
    medoids_label = 'The initial medoids were :' + str(set_medoids)
    k_label = 'k is ' + str(k)
    center_label = 'The cluster centers are ' + str(medoids) + ': ' + str(pathways_medoids)
    freq_label = 'The frequency of pathways in each cluster is ' + str(Frequency)
    sil_label = 'The average silhouette score is ' + str(Score)

    medoids = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=medoids_label, pos=(x,y))
    k_is = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=k_label, pos=(x,y+20))
    center = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=center_label, pos=(x,y+40))
    freq = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=freq_label, pos=(x,y+60))
    sil = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=sil_label, pos=(x,y+80))

    return cframe


def run_clustering(comp_Matrix, set_medoids, df, k):
    """
    Runs k-medoids clustering.
    """
    initial_medoids = [0]*k
    for n in range(0,k):
        initial_medoids[n] = set_medoids[n]

    kmedoids_instance = kmedoids(comp_Matrix, initial_medoids, data_type="distance_matrix")

    kmedoids_instance.process()
    clusters = kmedoids_instance.get_clusters()
    medoids = kmedoids_instance.get_medoids()

    pathways_medoids = [None]*k
    for n in range(0,k):
        pathways_medoids[n] = df[medoids[n]]

    assign = [0 for x in range(len(df))]
    for i in range(len(medoids)):
        for j in range(len(df)):
            if j in clusters[i]:
                assign[j] = medoids[i]

    Frequency = Counter(assign)

    Score = silhouette_score(comp_Matrix, assign, metric='precomputed')

    return (clusters, medoids, assign, pathways_medoids, Frequency, Score)


def classic_cluster(data, df, comp_Matrix, set_medoids, max_k, save_location , save_name, results, include_centroids):
    """
    Takes in user specifications for clustering.
    Uses silhouette score to evaluate clustering.
    Saves solution as specified.
    """
    cframe = ClusterFrame()
    y = 20
    Max_Score = -1
    Best_k = 0

    if results == 'Best k (ex 2)':
        lower = 3
    elif results == 'k only':
        lower = max_k
    else:
        lower = 2

    for k in range(lower,max_k+1):
        clusters, medoids, assign, pathways_medoids, Frequency, Score = run_clustering(comp_Matrix, set_medoids, df, k)
        
        if include_centroids == 'Yes':    
            column_name = 'Centroids K = ' + str(k)
            save_centroids = pd.DataFrame({'Pathways' : df, column_name: assign})
            with pd.ExcelWriter(save_location + 'Cluster_Centroids.xlsx', engine="openpyxl", mode='a') as writer:
                save_centroids.to_excel(writer,save_name + '_df')
        
        if results == 'All':
            cframe = cluster_results(cframe, y, k, set_medoids, medoids, pathways_medoids, Frequency, Score)
            y += 120
        if results == 'k only':
            cframe = cluster_results(cframe, y, k, set_medoids, medoids, pathways_medoids, Frequency, Score)
        else:
            if Score >= Max_Score:
                Max_Score = Score
                Best_k = k
                medoids_Best_k = medoids
                pathways_medoids_Best_k = pathways_medoids
                Frequency_Best_k = Frequency
                Score_Best_k = Score
                Best_clusters = clusters
    
    if results == 'Best k' or results == 'Best k (ex 2)':
        cframe = cluster_results(cframe, y, Best_k, set_medoids, medoids_Best_k, pathways_medoids_Best_k, Frequency_Best_k, Score_Best_k)

    cframe.Show()

    if results == 'k only':
        return clusters
    elif results == 'All':
        return        
    else:
        return Best_clusters
    
#======== Process =================

def violinplot(non_zero, difference_mean, k, axes, no_cons):     
    """
    Generates violin plot of the transitions percentage points differece
    between the original transistions and the cluster transitions.
    """   
    axes.violinplot(non_zero, showmeans=True)
    axes.set_ylim([0,1.1])
    axes.set_title(str(k) + '_' + str(no_cons) + '_' + str(round(difference_mean,3)), fontsize=14)
    axes.tick_params(axis='both', which='major', labelsize=14)
    return axes


def subplot_shape(size):
    """
    Get the most square shape for the plot axes values.
    If only one factor, increase size and allow for empty slots.
    """
    facts = [[i, size//i] for i in range(1, int(size**0.5) + 1) if size % i == 0]
    # re-calc for prime numbers larger than 3 to get better shape
    while len(facts) == 1:
        size += 1
        facts = [[i, size//i] for i in range(1, int(size**0.5) + 1) if size % i == 0]

    sum_facts = [sum(i) for i in facts]
    smallest = min(sum_facts)
    shape = facts[sum_facts.index(smallest)]
    
    return shape


def difference(letters, centroids, counts, original_transitions):
    """
    Calculates the difference matrix:
    Takes the absolute difference of percentage point from original to cluster transitions.
    """
    Start, centroid_transitions, Matrix_prob  = transitions.get_transitions(centroids, letters, counts)
    number_connections = np.count_nonzero(centroid_transitions)
    Difference_c = [[abs(a-b) for a,b in zip(original_transitions[j],centroid_transitions[j])] for j in range(len(original_transitions))]
    return(Difference_c, number_connections)


def process_cluster_results(cframe, results, set_medoids, tol, original_non_zero, highlight_results):
    """
    Generate static text to display process clustering results.
    """
    x = 20
    y = 20
    medoids_label = 'The initial medoids were :' + str(set_medoids)
    medoids_text = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=medoids_label, pos=(20,y))
    y += 20
    def_results = 'The results are displayed as: [k, number of connections, percentage points different, silhouette score]' 
    def_results = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=def_results, pos=(20,y))
    y += 20

    results_label_2 = ''
    if results != 'k only':
        results_label = 'The highlighted results below were within tolerance ' + str(tol) + ' of ' + str(original_non_zero) + ' connections' 
        if results != 'All':
            results_label_2 = 'The suggested \'best\' results are shown results. \nNote this is just a suggestion, as highlighted is the k with the closest number of connection \nand lowest mean percentage points difference' 
    else:
        results_label = 'The selected k results are shown below' 
    results_text = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=results_label, pos=(20,y))
    y += 20
    if results_label_2 != '':
        results_text = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=results_label_2, pos=(20,y))
        y += 60

    for row in highlight_results:
        row_label = wx.StaticText(cframe.panel, id=wx.ID_ANY, label=str(row), pos=(20,y))
        y += 20

    return cframe


def process_cluster(data, df, letters, comp_Matrix, set_medoids, max_k, save_location, save_name, tol, results, include_centroids, adjust):
    """
    Takes in user specifications for process clustering.
    Uses difference matrix and difference mean to evaluate clustering.
    Saves solution as specified.
    """
    cframe = ClusterFrame()
    if results == 'Best k (ex 2)':
        lower = 3
    elif results == 'k only':
        lower = max_k
    else:
        lower = 2

    if results == 'All':
        shape = subplot_shape(max_k)
        pos = 0
        fig, ax = plt.subplots(shape[1], shape[0], figsize=[15,20])
    else:
        fig, ax = plt.subplots(1, 1, figsize=[15,20])

    Start, original_transitions, Matrix_prob  = transitions.get_transitions(data.pathways, letters, adjust)
    original_non_zero = np.count_nonzero(original_transitions)
    all_centroids = pd.DataFrame()
    highlight_results = ['']

    # setup for best results
    best_diff_cons = original_non_zero
    best_diff_mean = 1.0
    best_k = 0

    for k in range(lower,max_k+1):
        clusters, medoids, assign, pathways_medoids, Frequency, Score = run_clustering(comp_Matrix, set_medoids, df.pathway, k)
        # get results
        counter_name = 'counter_' + str(k)
        prop_counter_name = 'prop_counter_' + str(k)
        propergated_clusters_foot = transitions.propergate_clusters(df, clusters)
        current_selected = pd.DataFrame({str(k) : pathways_medoids,
                                        counter_name : [Frequency[v] for v in medoids],
                                        prop_counter_name : [len(cluster) for cluster in propergated_clusters_foot]})
        all_centroids = pd.concat([all_centroids, current_selected], axis=1, sort=False)
        # calculate difference
        diff, no_cons = difference(letters, current_selected[str(k)], current_selected[prop_counter_name], original_transitions)
        non_zero = []
        for row in diff:
            non_zero += [r for r in row if r > 0]
        difference_value = sum([sum(row) for row in diff])
        difference_mean = difference_value/len(non_zero)        
        # set up display results
        diff_cons = abs(original_non_zero - no_cons)
        if results == 'k only':
            highlight_results.append([k, no_cons, difference_mean, Score])
        elif diff_cons <= tol:
            if results == 'All':
                highlight_results.append([k, no_cons, difference_mean, Score])
            else:
                if diff_cons < best_diff_cons:
                    highlight_results[0] = [k, no_cons, difference_mean, Score]
                    best_current_selected = current_selected
                    best_diff_cons = diff_cons
                    best_diff_mean = difference_mean
                    best_k = k
                if diff_cons == best_diff_cons:
                    if difference_mean < best_diff_mean:
                        highlight_results[0] = [k, no_cons, difference_mean, Score]
                        best_current_selected = current_selected
                        best_diff_cons = diff_cons
                        best_diff_mean = difference_mean
                        best_k = k

        # produce plot
        if results == 'All':
            axes = ax[int(pos/shape[0]), pos%shape[0]]
            pos+=1
            violinplot(non_zero, difference_mean, k , axes, no_cons)
        elif results == 'k only':
            violinplot(non_zero, difference_mean, k , ax, no_cons)
    if results == 'Best k' or results == 'Best k (ex 2)':
        if best_k != 0:
            violinplot(non_zero, difference_mean, k , ax, no_cons)

    # remove blank subplots
    if results == 'All':
        for i in range(shape[0]*shape[1] - (k - 1)):
            fig.delaxes(ax.flatten()[(k-1)+i])
    fig.subplots_adjust(wspace=0.5, hspace=0.5)
    plot_name = save_name + '_' + results + '_' + str(max_k)
    fig.savefig(save_location + 'Plots/Process_Violin_Plots/' + plot_name + '.png', bbox_inches='tight', facecolor="None")      
    plt.close() 

    if include_centroids == 'Yes': 
        column_name = 'Centroids K = ' + str(k)
        save_centroids = pd.DataFrame({'Pathways' : df.pathway, column_name: assign})
        with pd.ExcelWriter(save_location + 'Process_Centroids.xlsx', engine="openpyxl", mode='a') as writer:
            all_centroids.to_excel(writer,save_name)
            save_centroids.to_excel(writer, save_name + '_df')

    cframe = process_cluster_results(cframe, results, set_medoids, tol, original_non_zero, highlight_results)

    cframe.Show()
    if results == 'k only':
        return (k, current_selected, plot_name)
    elif results != 'All':
        if best_k != 0 :
            return (best_k, best_current_selected, plot_name)
        else:
            return (None, None, None)
    else:
        return (k, current_selected, plot_name)