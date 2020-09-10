import re
from collections import Counter
from graphviz import Digraph
import pandas as pd
import numpy as np
import statistics
import matplotlib.pyplot as plt
import math
import copy
import imp

summary = imp.load_source('summary', 'src/Summary.py')
transitions = imp.load_source('transitions', 'src/transitions.py')


def initialise_results_tables(results_data, pathway_column, letters):
    """Setup the four initial results tables

    T1 = General simulation summary
    T2 = no. occurances of each activity
    T3 = top ten most occuring pathways and their counts
    T4 = Average waiting time for each activity
    """
    dataframe_T1 = pd.DataFrame(columns=['Name',
                              'Mean Time in System',
                              'Median Time in System',
                              'Target [days, %]',
                              'No. Unique Pathways', 
                              'Occurs Once',
                              'Occurs > Once',
                              'Total Transitions',
                              'Mean Transitions',
                              'Largest Transition',
                              'Day Last Arrival',
                              'Overall Period'])

    dataframe_T2 = pd.DataFrame({'Activity': letters})

    dataframe_T3 = pd.DataFrame()

    dataframe_T4 = pd.DataFrame({'Activity': letters})

    original_transitions = transitions.find_transitions(letters, results_data[pathway_column], None, False)

    return(dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, original_transitions)


def T1_results(results_data, time_column, pathway_column, dataframe_T1, 
                original_transitions, simulation_transitions, 
                intervention_codes, target, individuals, 
                save_location, simulation_name, 
                last_arrival, period):
    """Get simulation summary results."""
    # mean time in system
    totaltime = [float(results_data[time_column][i]) for i in range(len(results_data))]
    mean_time = round(statistics.mean(totaltime),2)
    # median time in system
    median_time = round(statistics.median(totaltime),2)
    # % <target days
    target_achieved = round((len(results_data[results_data[time_column] < target])/len(results_data))*100,2)
    # number of unique pathways
    unique = round(len(set(results_data[pathway_column])),0)
    # number pathways occurred only once
    once = round(len(results_data[pathway_column].value_counts()[results_data[pathway_column].value_counts()<2]),0)
    # number pathways occured more than once
    once_more = round(len(results_data[pathway_column].value_counts()[results_data[pathway_column].value_counts()>=2]),0)
    # combine Results
    combo_results = [simulation_name, mean_time, median_time, [target, target_achieved], unique, once, once_more]

    # Total Transitions
    difference_matrix, difference_value = transitions.transitions_compare(save_location, simulation_name, original_transitions, simulation_transitions)
    combo_results.append(difference_value)
    # Mean Transitions
    average_difference = round(difference_value/(len(difference_matrix[0])*len(difference_matrix)),2)
    combo_results.append(average_difference)
    # Largest Transition
    largest_difference = np.max(difference_matrix)
    combo_results.append(largest_difference)

    # Last Arrival
    if type(last_arrival) != int:
        day_last_arrival = round(last_arrival[last_arrival.id_number == individuals].arrival_date.min(),0)
        combo_results.append(day_last_arrival)
    else:
        combo_results.append(last_arrival)

    # overall time period
    if type(period) != int:
        time_period = round(period.exit_date.max() - period.exit_date.min(),0)
        combo_results.append(time_period)
    else:
        combo_results.append(period)

    # add to dataframe_T1
    results_T1_series = pd.Series(combo_results, index = dataframe_T1.columns)
    results_T1 = dataframe_T1.append(results_T1_series, ignore_index=True)

    return results_T1


def T2_results(results_data, pathway_column, letters, dataframe_T2, simulation_name):
    """Get the number of occurances of each activity."""
    # number of each activity
    counts = transitions.counts_from_pathway_data(results_data[pathway_column])
    counts_T2 = [counts[key] for key in letters]
    counts_T2_results_data = pd.DataFrame([[key, counts[key]] for key in letters])
    counts_T2_results_data.columns = ['Activity', simulation_name]
    results_T2 = dataframe_T2.join(counts_T2_results_data.set_index('Activity'), on='Activity')
    return results_T2


def T3_results(results_data, pathway_column, dataframe_T3, save_location, simulation_name):
    """Get top ten occuring pathways and their counts."""
    subset = results_data[pathway_column].value_counts()[results_data[pathway_column].value_counts()>=2]
    
    # Top ten
    results_data_subset = pd.DataFrame(subset).reset_index()
    pathway_name = 'pathway_' + simulation_name
    count_name = 'count_' + simulation_name
    results_data_subset.columns = [pathway_name, count_name]
    top_ten = results_data_subset.loc[0:9]
    results_T3 = pd.concat([dataframe_T3, top_ten], axis=1, join='outer')
    return results_T3


def reduce_listed_times(results_data, column):
    """If the waiting times are stored in a list, reduce the list."""
    results_data_nan = copy.deepcopy(results_data)
    results_data_nan = results_data_nan.replace(' ', np.NaN)
    working_column = [c for c in results_data_nan[column]]
    all_values= []
    for l in working_column:
        if isinstance(l, list):
            for e in l:
                all_values.append(e)
        else:
            all_values.append(l)
    reduced_result = pd.DataFrame(all_values).mean(skipna=True)
    return reduced_result[0]


def T4_results(results_data, table_letters, dataframe_T4, listed_times, simulation_name):
    """Average waiting time for each activity."""
    if listed_times == True:
        waiting_results = pd.DataFrame([[column, reduce_listed_times(results_data, column)] for column in table_letters])
    else:
        waiting_results = pd.DataFrame([[column, results_data[column].mean(skipna=True)] for column in table_letters])
        
    waiting_results.columns = ['Activity', simulation_name]
    results_T4 = dataframe_T4.join(waiting_results.set_index('Activity'), on='Activity')
    results_T4 = results_T4.round({simulation_name: 2})
    results_T4 = results_T4.fillna(0)
    return results_T4


def run_results(results_data, time_column, pathway_column, table_letters, letters, 
                dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, 
                original_transitions, simulation_transitions, 
                intervention_codes, target, individuals, 
                save_location, simulation_name, listed_times, 
                last_arrival, period):
    """Fill the four results tables."""
    Table1_results = T1_results(results_data, time_column, pathway_column, dataframe_T1, 
                                original_transitions, simulation_transitions, 
                                intervention_codes, target, individuals, 
                                save_location, simulation_name, 
                                last_arrival, period)

    Table2_results = T2_results(results_data, pathway_column, letters, dataframe_T2, simulation_name)

    Table3_results = T3_results(results_data, pathway_column, dataframe_T3, save_location, simulation_name)

    Table4_results = T4_results(results_data, table_letters, dataframe_T4, listed_times, simulation_name)
    return(Table1_results, Table2_results, Table3_results, Table4_results)