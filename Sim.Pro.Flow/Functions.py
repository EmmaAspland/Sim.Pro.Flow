import wx.grid as gridlib
import pandas as pd
import numpy as np
import copy
import ciw
import re
import math
import statistics
import random

import imp
adapt = imp.load_source('adapt', 'src/adapt.py')
summary = imp.load_source('summary', 'src/Summary.py')
cluster = imp.load_source('cluster', 'src/clustering.py')

transitions = imp.load_source('transitions', 'src/transitions.py')
capacity = imp.load_source('capacity', 'src/capacity.py')
results = imp.load_source('results', 'src/results.py')
sim = imp.load_source('sim', 'src/simulation.py')
custom_ciw = imp.load_source('custom_ciw', 'src/custom_ciw.py')


#========= Data Panel ===========
#--------------- on Columns ----------------
def onHeaders_selection(columns, selected):
    """Create list of selected column names."""
    headers = [columns[value] for value in selected]
    return headers


def create_codes(headers):  
    """Create character code for each activity."""  
    activity_codes = adapt.codes(headers)
    letters = [key for key in activity_codes.keys()]
    return(letters, activity_codes)


def Create_pathways_data(activity_codes, data, save_location, data_name):
    """Creates pathway data for non formatted input data.

    Add pathway, waiting time per activity and total time in system to data.
    df created is each unique pathways and the number of times performed.
    """
    data['pathways'] = data.apply(lambda row: adapt.find_pathways(row, activity_codes),axis=1)

    
    for index,key in enumerate(activity_codes.keys()):
        data[key] = data.apply(lambda row: adapt.find_time_from_previous(row, key, activity_codes), axis=1)
        if index == 0:
            first = key
        if index == len(activity_codes)-1:
            last = key
    data['totaltime'] = data.apply(lambda row: row[first:last].sum(),axis=1)
    data = data.replace(' ', np.NaN)
    df = transitions.pathway_counts(data)
        
    with pd.ExcelWriter(save_location + 'SimProFlow_' + data_name, mode='w') as writer:
        data.to_excel(writer,'Data')
        df.to_excel(writer,'dataframe')

    return(data, df)


#-------------- on Format -----------------

def Create_multi_pathways_data(data, id_column, activity_column, dates_column, columns, selected, save_location, data_name):
    """Creates pathway data for formatted input data.

    Add multi_pathway (double codes) and pathway (single codes), and total time in system to data.
    Waiting time per single code activity recorded with list of waiting time. 
    df created is each unique pathways and the number of times performed.
    """
    if id_column != None:
        # format data
        data = data.dropna().reset_index(drop=True)
        data = adapt.rename_duplicates(data, id_column, activity_column, dates_column)
        headers = adapt.multi_headers(data, id_column)
    else:
        # multi columns
        headers = onHeaders_selection(columns, selected)


    activity_codes, multi_activity_codes = adapt.multi_codes(headers)
    letters = [code for code in activity_codes.keys()]
    multi_letters = [code for code in multi_activity_codes.keys()]

    data['multi_pathways'] = data.apply(lambda row: adapt.find_pathways(row, multi_activity_codes),axis=1)
    data['pathways'] = data.apply(lambda row: adapt.condense_pathways(row), axis=1)

    for index,key in enumerate(multi_activity_codes.keys()):
        data[key] = data.apply(lambda row: adapt.find_time_from_previous_Double(row, key, multi_activity_codes), axis=1)
        
    for general_key in activity_codes.keys():
        all_code = [key for key in multi_activity_codes.keys() if key[0] == general_key]
        data[general_key] = data[all_code].values.tolist()
        
    for index,key in enumerate(multi_activity_codes.keys()):
        if index == 0:
            first = key
        if index == len(multi_activity_codes)-1:
            last = key
    data['totaltime'] = data.apply(lambda row: row[first:last].sum(),axis=1)

    for key in multi_activity_codes.keys():
        data = data.drop(key, axis=1)
        
    data = data.replace(' ', np.NaN)
    df = transitions.pathway_counts(data)
        
    with pd.ExcelWriter(save_location + 'SimProFlow_' + data_name, mode='w') as writer:
        data.to_excel(writer,'Data')
        df.to_excel(writer,'dataframe')
        
    return(data, df, activity_codes, multi_activity_codes, headers, letters, multi_letters)


def Create_Summary_Sheet(data, df, multi_activity_codes, save_location, original_name):
    """Create summary sheet and save to output folder."""
    summary.SummarySheet(data, df, multi_activity_codes, save_location, original_name)


#========= Clustering Panel ===========

def Get_default_ranks(activity_codes, data):
    """Generates the default rankings per activity based on occurance frequency in data."""
    default_rank = adapt.freq_Rankings(activity_codes, data)
    return default_rank


def Get_Weights(dict_rank):
    """Converts rankings into weights."""
    Weights = adapt.create_Weightings(dict_rank)   
    return Weights


def GetMedoids(select_medoids, df, max_k, data, comp_Matrix, Specify_textbox):
    """From user selections, generate initial medoids for clustering."""
    if select_medoids.IsChecked(0):
        # ensure no repeats
        all_options = [i for i in range(len(df))]
        set_medoids = random.sample(all_options, max_k)
    elif select_medoids.IsChecked(1):
        # as df is ordered by counts
        set_medoids = [i for i in range(max_k)]
    elif select_medoids.IsChecked(2):
        sum_matrix = [sum(x) for x in comp_Matrix]
        smallest = sorted(sum_matrix)[:max_k]
        set_medoids = [sum_matrix.index(sum_values) for sum_values in smallest]   
    elif select_medoids.IsChecked(3) == True:  
        specify_medoids = Specify_textbox.GetValue()
        if specify_medoids == 'Enter values':
            return([], 'Enter values Error')
        potential_set_medoids = list(map(int, specify_medoids.split(',')))                     
        if len(potential_set_medoids) != max_k:
            return(potential_set_medoids, 'Large Error')
        set_medoids = potential_set_medoids
    return(set_medoids, 'No')


def RunClustering(data, df, comp_Matrix, set_medoids, max_k, save_location, save_name, result_type, include_centroids):
    """Run clustering and display results level from user selection."""    
    cluster_results = cluster.classic_cluster(data, df, comp_Matrix, set_medoids, max_k, save_location, save_name, results=result_type, include_centroids=include_centroids)
    return cluster_results


def RunProcessClustering(data, df, letters, comp_Matrix, set_medoids, max_k, save_location, save_name, tol, result_type, include_centroids, adjust):
    """Run process clustering and display results level from user selection."""
    k, process_cluster_results, plot_name = cluster.process_cluster(data, df, letters, comp_Matrix, set_medoids, max_k, save_location , save_name, tol,
                                                  results=result_type, include_centroids=include_centroids, adjust=adjust)
    return (k, process_cluster_results, plot_name)

#========= Draw ===========

def get_draw_network(sim_type, letters, Matrix, save_location, file_name, process_k, centroids, adjust, LR, penwidth, round_to):
    """Draw transitions network.

    + Full Transitions: One diagram for whole transtions matrix
    + Clustered Transtions: Diagram per class (k) for class transition matrix
    + Process Based: Three diagrams, full transitions, seperated pathways and linked by postion.
    """
    if sim_type == 'Full Transitions':
        save_file_name = save_location + 'Network_diagrams/' + file_name
        transitions.draw_network(letters, Matrix, save_file_name, LR, penwidth, round_to)
    
    if sim_type == 'Clustered Transitions':
        for c_class, c_matrix in Matrix.items():
            c_file_name = save_location + 'Network_diagrams/'  + file_name + '_' + c_class
            transitions.draw_network(letters, c_matrix, c_file_name, LR, penwidth, round_to)
    
    if sim_type == 'Process Medoids':
        adjust_save_file_name = save_location + 'Network_diagrams/' + file_name + '_' + str(process_k) + '_adjust_' + str(adjust)
        transitions.draw_network(letters, Matrix[0], adjust_save_file_name, LR, penwidth, round_to)
        file_name_network = save_location + 'Network_diagrams/'  + file_name + '_' + str(process_k)
        transitions.draw_network(letters, Matrix[1], file_name_network, LR, penwidth, round_to)

        file_name_centroids = file_name_network + '_pathways'
        transitions.draw_centroids(centroids, str(process_k), file_name_centroids)

        max_length = centroids[str(process_k)].str.len().max()
        first = [[path[i:i+1] for path in centroids[str(process_k)]] for i in range(0, max_length)]
        all_firsts = [list(set(row)) for row in first]
        for r, row in enumerate(all_firsts):
            all_firsts[r] = ['End' if x=='' else x for x in row]

        file_name_grouped = file_name_network + '_linked'
        transitions.draw_centroids_linked(centroids[str(process_k)], all_firsts, file_name_grouped) 

#========= Simulation ===========

def initialise_results_tables(data, letters):
    """Iitialise the four simulation results data frames."""
    dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, original_transitions = results.initialise_results_tables(data, 'pathways', letters)
    return(dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, original_transitions)


def initial_vis_inputs(data, headers, activity_codes, formatted):
    """Generate initial values from raw data for results tables."""
    initial_individuals = len(data)
    overall_min, overall_max, overall_period = capacity.get_total_time_period(data, headers)
    df_start = transitions.initial_last_arrival(data, activity_codes, formatted)
    column_min, column_max, real_last_arrival = capacity.get_column_time_period(df_start.Start_dates)
    return(initial_individuals, real_last_arrival, overall_period)


def get_vis_summary(results_data, time_column, pathway_column, table_letters, letters, 
                    dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, 
                    original_transitions, simulation_transitions, 
                    intervention_codes, target, individuals, 
                    save_location, simulation_name, listed_times, 
                    last_arrival, period):
    """Fill results tables."""
    T1_results, T2_results, T3_results, T4_results = results.run_results(results_data, time_column, pathway_column, table_letters, letters, 
                                                                        dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, 
                                                                        original_transitions, simulation_transitions, 
                                                                        intervention_codes, target, individuals, 
                                                                        save_location, simulation_name, listed_times, 
                                                                        last_arrival, period)

    sim.plot_totaltime(save_location, simulation_name, results_data)
    sim.plot_activity_waittimes(save_location, simulation_name, results_data, table_letters)
    return(T1_results, T2_results, T3_results, T4_results)


def get_period(data, headers):
    """Get overall period covered by raw data."""
    overall_min, overall_max, overall_period = capacity.get_total_time_period(data, headers)
    return overall_period


def AutoSetupInputs(sim_type, data, activity_codes, multi_activity_codes, headers, letters, individuals, overall_period, clusters, process_k, centroids, original_name, adjust):
    """Generate basic sim default inputs.
    
    Service default 0.1 for all types.
    Servers capacity same for all.

    + Raw Pathways: Routing and arrivals at dummy node created
    + Full Transitions: arrivals row matrix and routing transition matrix
    + Clustered Transitions: arrivals row matrix and routing transition matrix per class (k)
    + Process Medoids: Routing of centroids and arrivals per class 
    """
    # if formatted data use multi_activity_codes
    if original_name == 'original_formatted':
        input_servers = sim.define_input_capacity(data, multi_activity_codes, headers, letters, original_name)
    else:
        input_servers = sim.define_input_capacity(data, activity_codes, headers, letters, original_name)
    input_service = 0.1

    if sim_type == 'Raw Pathways':
        draw_matrix = []
        input_routing = sim.define_input_routing(sim_type, data['pathways'], letters, None)
        input_arrival = individuals/overall_period

    if sim_type == 'Full Transitions':
        # allow draw of adjusted matrix
        input_arrival, draw_matrix, Matrix_prob = transitions.get_transitions(data['pathways'], letters, False) 
        input_routing = sim.define_input_routing(sim_type, data['pathways'], letters, Matrix_prob)             

    if sim_type == 'Clustered Transitions':  
        pathway_counts = transitions.pathway_counts(data)
        propergated_clusters = transitions.propergate_clusters(pathway_counts, clusters)
        input_arrival = {}
        input_routing = {}
        draw_matrix = {}
        for c, cluster in enumerate(propergated_clusters):
            class_name = 'Class '+ str(c)
            prop_df = pd.DataFrame(cluster)
            prop_df.columns = ['centroids']
            Start, c_draw_matrix, Matrix_prob = transitions.get_transitions(prop_df.centroids, letters, False)
            input_arrival[class_name] = Start
            input_routing[class_name] = Matrix_prob
            draw_matrix[class_name] = c_draw_matrix

    if sim_type == 'Process Medoids':
        draw_matrix = []
        adjust_input_arrival, adjust_draw_matrix, adjust_Matrix_prob = transitions.get_transitions(data['pathways'], letters, adjust) 
        draw_matrix.append(adjust_draw_matrix)
        Start, process_draw_matrix, Matrix_prob = transitions.get_transitions(centroids[str(process_k)], letters, centroids['prop_counter_' + str(process_k)]) 
        draw_matrix.append(process_draw_matrix)
        input_arrival = {}
        for c, route in enumerate(centroids[str(process_k)]):
            arrival = [centroids['prop_counter_' + str(process_k)][c] if route[0] == code else 'NoArrivals' for code in letters]
            class_name = 'Class '+ str(c)
            input_arrival[class_name] = arrival        
        input_routing = sim.define_input_routing(sim_type, centroids[str(process_k)], letters, None)

    return(input_arrival, input_service, input_servers, input_routing, draw_matrix)


def ConstructSim(sim_type, week, warm_type, letters, individuals, overall_period, cluster_k,
                arrivals, service, capacity, warm, Routes):
    """Constructs the simulation network.


    Takes warm up type into consideration.
    + Routing type for process based different for Raw Pathways and Process Cetroids
    + Both routing functions defined here.
    """
    def raw_routing_function(ind):
        """Return route from id_number - for Raw Pathways."""
        route_number = ind.id_number - 1
        return copy.deepcopy(Routes[route_number])

    def process_routing_function(ind):
        """Return route from customer class - for Process Medoids."""
        route_number = ind.customer_class
        return copy.deepcopy(Routes[route_number])

    if warm_type == 'Itterative':
        time_run = individuals * warm
        individuals = individuals * warm
    else:
        time_run = individuals

    Arrival = sim.define_arrivals(sim_type, letters, individuals, arrivals, Routes)
    Service = sim.define_service(sim_type, letters, service, cluster_k)
    Servers = sim.define_servers(sim_type, warm_type, letters, overall_period, capacity, week, warm)


    if sim_type == 'Raw Pathways':
        if warm_type == 'Itterative':
            Routes = Routes * warm
        All_Routing = [raw_routing_function for _ in range(len(letters)+1)]
    elif sim_type == 'Process Medoids':
        All_Routing = [process_routing_function for _ in range(len(letters))]
    else:
        All_Routing = Routes

    Network = ciw.create_network(
                            arrival_distributions = Arrival,
                            service_distributions = Service,
                            number_of_servers = Servers,
                            routing = All_Routing
                            )

    return(Network, Servers, time_run, individuals)


def RunBasicSim(Network, sim_seed, time_run):
    """Run the simulation."""
    ciw.seed(sim_seed)
    Q = ciw.Simulation(Network, node_class=custom_ciw.CustomNode)
    Q.simulate_until_max_customers(time_run, method='Finish', progress_bar=True)
    return(Q)


def RunSimData(Q, warm_type, warm, letters, Servers_Schedules, week_type,
                    dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, 
                    original_transitions, 
                    activity_codes, target, individuals, 
                    save_location, simulation_name, basic):
    """Produce the simulation results.

    Results adjusted if warm up Itterative selected.
    + Basic simulation will include utilisation table and graphics and waiting time graphics
    + Otherwise not produced becuase trials run
    """
    if letters[0] == 'Dummy':
        original_letters = letters[1:]
        current_letters = [''] + original_letters
    else:
        original_letters = letters
        current_letters = letters

    df_recs = pd.DataFrame(Q.get_all_records())
    df_recs2, all_unique_pathways, sim_waiting_columns = transitions.convert_records(Q, current_letters, True)
    df_all = transitions.sim_results(df_recs2, all_unique_pathways)
    if basic == True:
        with pd.ExcelWriter(save_location + 'Raw_Sim_Results.xlsx', engine="openpyxl", mode='a') as writer:
            df_all.to_excel(writer,simulation_name)

    if warm_type == 'Itterative':
        start_collection = individuals - int((individuals/warm))
        individuals = int((individuals/warm))
        df_recs = df_recs[df_recs.id_number > start_collection]
        df_recs = df_recs.reset_index()
        df_all = df_all[df_all.id_number > start_collection]
        df_all = df_all.reset_index()
        simulation_name = simulation_name + '_selected'
        if basic == True:
            with pd.ExcelWriter(save_location + 'Raw_Sim_Results.xlsx', engine="openpyxl", mode='a') as writer:
                df_all.to_excel(writer,simulation_name)


    simulation_transitions = transitions.find_transitions(original_letters, df_all['pathway'], None, False)
    dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4 = get_vis_summary(df_all, 'totaltime', 'pathway', sim_waiting_columns, current_letters, 
                                                                            dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, 
                                                                            original_transitions, simulation_transitions, 
                                                                            activity_codes, target, individuals, 
                                                                            save_location, simulation_name, listed_times=True, 
                                                                            last_arrival=df_recs, period=df_recs)

    if basic == True:
        week_type = int(week_type[0])
        df_utilisation = sim.run_utilisation_results(df_recs, current_letters, Servers_Schedules, week_type, save_location, simulation_name)
        return(dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, df_utilisation)
    else:
        return(dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4)


#----------------- Trials -------------------------

def RunTrialSim(Network, trials, time_run, warm_type, warm, letters, Servers_Schedules, week_type,
                dataframe_T1, dataframe_T2, dataframe_T3, dataframe_T4, 
                original_transitions, 
                activity_codes, target, individuals, 
                save_location, simulation_name, basic):
    """Run simulation for trials.

    Seed will change for each run.
    Results recorded and then reported in the form of confidence intervals.
    Results only for T1, T2 and T4.
    Standard deviation graphics produced to allow user decision on sufficient runs.
    """
    # Set up empty tables for results
    Trials_dataframe_T1 = pd.DataFrame(columns=['Name',
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
    Trials_dataframe_T2 = pd.DataFrame({'Activity': letters})
    Trials_dataframe_T3 = pd.DataFrame()
    Trials_dataframe_T4 = pd.DataFrame({'Activity': letters})


    All_T1_Results_T, All_T2_Results_T, All_T4_Results_T = [], [], []
    All_StDev_1, All_StDev_2, All_StDev_4 = [], [], []

    for run in range(trials):
        sim_seed = run
        Q = RunBasicSim(Network, sim_seed, time_run)

        T1_results_CI_T, T2_results_CI_T, dataframe_T3, T4_results_CI_T = RunSimData(Q, warm_type, warm, letters, Servers_Schedules, week_type,
                                                                            Trials_dataframe_T1, Trials_dataframe_T2, Trials_dataframe_T3, Trials_dataframe_T4, 
                                                                            original_transitions, 
                                                                            activity_codes, target, individuals, 
                                                                            save_location, simulation_name, basic)

        T1_results_CI_T_C = sim.list_convert_results(T1_results_CI_T, 'row')
        T2_results_CI_T_C = sim.list_convert_results(T2_results_CI_T, 'column')
        T4_results_CI_T_C = sim.list_convert_results(T4_results_CI_T, 'column')
        
        # Record all the results in list form for confidence interval calculation
        All_T1_Results_T.append(T1_results_CI_T_C)
        All_T2_Results_T.append(T2_results_CI_T_C)
        All_T4_Results_T.append(T4_results_CI_T_C)
        StDev_1 = [sim.Standard_Deviation(All_T1_Results_T, pos) for pos in range(len(All_T1_Results_T[0]))]
        All_StDev_1.append(StDev_1)
        StDev_2 = [sim.Standard_Deviation(All_T2_Results_T, pos) for pos in range(len(All_T2_Results_T[0]))]
        All_StDev_2.append(StDev_2)
        StDev_4 = [sim.Standard_Deviation(All_T4_Results_T, pos) for pos in range(len(All_T4_Results_T[0]))]
        All_StDev_4.append(StDev_4)

    dataframe_T1_T = sim.T1_CI_results(All_T1_Results_T, dataframe_T1, simulation_name, target)
    dataframe_T2_T = sim.T2_T4_CI_results(All_T2_Results_T, dataframe_T2, letters, simulation_name)
    dataframe_T4_T = sim.T2_T4_CI_results(All_T4_Results_T, dataframe_T4, letters, simulation_name)

    sim.plot_stdev(save_location, simulation_name, 'Table 1', All_StDev_1, dataframe_T1_T, trials, letters, 'columns')
    sim.plot_stdev(save_location, simulation_name, 'Table 2', All_StDev_2, dataframe_T2_T, trials, letters, 'letters')
    sim.plot_stdev(save_location, simulation_name, 'Table 4', All_StDev_4, dataframe_T4_T, trials, letters, 'letters')

    return(dataframe_T1_T, dataframe_T2_T, dataframe_T4_T)


#========= Capacity ===========

def CreatePattern(week_cap, days):
    """Smooth the weekly capacity over the selected number of days.
    
    Evenly spread the capacity across the week, with any excess added in increments of one
    starting at first day of the week.
    """
    average = week_cap/days
    excess = week_cap%days
    pattern = [int(average) for _ in range(days)]
    for e in range(excess):
        pattern[e] += 1
    return pattern


def CalculateCapacity(save_location, num_calcs, data, activity_codes, calculated_cap, 
                      cap_input_dict, overall_period, days_a_week, original_name):
    """Runs target capacity calculation.
    
    eps is the tolerance, currently hard coded as 1e-5.
    """
    eps = 1e-5
    if days_a_week == 0:
        days_a_week = 5
    if days_a_week == 1:
        days_a_week = 7

    calc_name, calculated_capacity = capacity.run_target_capacity(save_location, num_calcs, 
                                                                  data, activity_codes, calculated_cap, cap_input_dict, 
                                                                  overall_period, days_a_week, original_name, eps)

    cap_pattern = [CreatePattern(int(week_cap[2]), days_a_week) for week_cap in calculated_capacity.values()]
    return(calc_name, calculated_capacity, cap_pattern)
