import datetime
from datetime import datetime
import copy
import pandas as pd
import numpy as np
import math
import ciw
import imp
import re
import statistics
import matplotlib.pyplot as plt

transitions = imp.load_source('transitions', 'src/transitions.py')
custom_ciw = imp.load_source('custom_ciw', 'src/custom_ciw.py')

#===============================================================

def gather_set(data):  
    """Gets all days, weeks, year from data."""
    set_dates = set()
    for c in data.columns:
        set_c = set(data[c])
        set_dates = set_dates.union(set_c)
    listed_dates = list(set_dates)
    return listed_dates


def averagePatternArrival(data, activity_codes, headers):
    """Calculates average number recorded per day, for each activity."""
    data_2 = copy.deepcopy(data)
    data_2.replace({' ': pd.NaT}, inplace=True)
    cols_remove = [col for col in data_2.columns if col not in headers]
    data_2.drop(cols_remove, axis = 1, inplace=True)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    for column in activity_codes.values():
        data_2[column] = data_2[column].dt.strftime('%A, %U, %y')
    
    # Get all dates
    list_gather_set_days = gather_set(data_2)

    day_dict = {}
    for day in days:
        list_day_name = 'list_' + day
        list_day = [i for i in list_gather_set_days if day in i]
        list_day = sorted(list_day)
        day_dict[list_day_name] = list_day

    all_average_in_day = {}
    for key, activity in activity_codes.items():
        average_in_day = [data_2[activity].value_counts().reindex(value).mean() for value in day_dict.values()]
        all_average_in_day[key] = average_in_day
    cap_pattern = {activity: [0 if pd.isna(c) == True else int(round(c,0)) for c in cap]  for activity, cap in all_average_in_day.items()}

    return cap_pattern


def getRoutes(sim_type, data, letters):
    """Get raw data actual pathways and convert to node routes."""
    all_actual_pathways = [data[i] for i in range(len(data))]
    split_routes = [re.findall('.',route) for route in all_actual_pathways]
    Routes = [[letters.index(r) + 1 for r in route] for route in split_routes]
    if sim_type == 'Raw Pathways':
        Routes = [[1] + route for route in Routes]
    return Routes


def condense_patterns(letters, capacity_pattern_dict):
    """Combines capacity for multiples of acitvity.
    
    If data was formatted using double codes - Get capacity and merge to general single code
    """
    pattern_dict = {}
    for letter in letters:
        activity_pattern = []
        pattern = [0 for i in range(7)]
        for code, values in capacity_pattern_dict.items():
            if code[0] == letter:
                activity_pattern.append(values)
        for l in range(len(activity_pattern)):
            pattern = [sum(x) for x in zip(pattern, activity_pattern[l])]
        pattern_dict[letter] = pattern
    return pattern_dict


def define_input_capacity(data, activity_codes, headers, letters, original_name):
    """Define server capacity from average performed each named day."""
    capacity_pattern_dict = averagePatternArrival(data, activity_codes, headers)

    if original_name == 'original_formatted':
        if letters[0] == 'Dummy':
            letters = letters[1:]
        capacity_pattern_dict = condense_patterns(letters, capacity_pattern_dict)

    return capacity_pattern_dict


def define_input_routing(sim_type, data, letters, Matrix_prob):
    """Define routes for simulation.

    + Raw Pathways and Process Medoids: use get routes
    + Full Transitions and Clustered Trnasitions: use transition matrix
    """
    if sim_type == 'Raw Pathways' or sim_type == 'Process Medoids':
        Routes = getRoutes(sim_type, data, letters)
    else:
        Routes = Matrix_prob
    return Routes


#===============================================================

def define_arrivals(sim_type, letters, individuals, arrivals, Routes):
    """Set up arrivals distribution from arrivals table.

    + Raw Pathways: Limited Exponential for dummy node of total arrival rate
    + Full Transitions: Exponential activiy arrival rate
    + Clustered Transitions: Class per cluster with Exponential activity arrival rate
    + Process Medoids: Class per centroid with Exponential activity arrival rate
    """
    if sim_type == 'Raw Pathways':
        Arrival = [custom_ciw.LimitedExponential(arrivals[0][0],individuals)] + [ciw.dists.NoArrivals() for i in letters]

    if sim_type == 'Full Transitions':
        Arrival = [ciw.dists.Exponential(arrivals[0][code]) if arrivals[0][code] != 0 else ciw.dists.NoArrivals() for code in range(len(letters))]
    
    if sim_type == 'Clustered Transitions':
        Arrival = {}
        for c, class_arrivals in enumerate(arrivals):
            arrival_dist = [ciw.dists.Exponential(class_arrivals[code]) if class_arrivals[code] != 0 else ciw.dists.NoArrivals() for code in range(len(letters))]
            class_name = 'Class '+ str(c)
            Arrival[class_name] = arrival_dist

    if sim_type == 'Process Medoids':
        Arrival = {}
        for c, route in enumerate(Routes):
            arrival_dist = [ciw.dists.Exponential(arrivals[0][c]) if route[0] - 1 == code else ciw.dists.NoArrivals() for code in range(len(letters))]
            class_name = 'Class '+ str(c)
            Arrival[class_name] = arrival_dist

    return Arrival


def define_service(sim_type, letters, service, cluster_k):
    """Set up service rate from service table.

    Either Deterministic or Exponential based on user choice.

    + Raw Pathways: Service rate per activity plus deterministic 0 for dummy arrival node
    + Full Transitions: Service rate per activity
    + Clustered Transitions: Class per cluster with Service rate per activity
    + Process Medoids: Class per centroid with Service rate per activity
    """
    # Det 0.1 as default
    Service_distribution = []
    for code in letters:
        if service[code][0] == 'Deterministic':
            code_service = ciw.dists.Deterministic(service[code][1])
        else:
            code_service = ciw.dists.Exponential(1/service[code][1])
        Service_distribution.append(code_service)

    if sim_type== 'Raw Pathways':
        Service = [ciw.dists.Deterministic(0)] + Service_distribution

    elif sim_type == 'Full Transitions':
        Service = Service_distribution

    else:
        Service = {}
        for c in range(cluster_k):
            class_name = 'Class '+ str(c)
            Service[class_name] = Service_distribution

    return Service


def pattern_server_schedules(cap_pattern, total_arrival_days):
    """Convert the capaity pattern into ciw format."""
    num_weeks = math.ceil(total_arrival_days/7)
    total_arrival_days_cap_pattern = [cap_pattern for i in range(num_weeks)]
    server_number = [0] + [item for sublist in total_arrival_days_cap_pattern for item in sublist]
    
    server_schedule = [[server, time] for time, server in enumerate(server_number)]
    server_schedule.pop(0)
    
    return server_schedule 


def build_server_schedules(sim_type, cap_pattern, total_arrival_days, week):
    """Build the 5 day or 7 day weekly capacity pattern, for the desired number of total days."""
    weekly_pattern = [pattern + [0, 0] if len(pattern) == 5 else pattern for pattern in cap_pattern.values()]

    all_server_schedules = []
    for pattern in weekly_pattern:
        server_schedule = pattern_server_schedules(pattern, total_arrival_days)
        all_server_schedules.append(server_schedule)
    
    if sim_type == 'Raw Pathways':
        if week == '5 days':
            dummy_pattern = [total_arrival_days for _ in range(5)] + [0, 0]
            dummy_server = [pattern_server_schedules(dummy_pattern, total_arrival_days)]
        else:
            dummy_server = [[[total_arrival_days, i] for i in range(1, total_arrival_days)]]
        all_server_schedules = dummy_server + all_server_schedules

    return all_server_schedules


def define_servers(sim_type, warm_type, letters, overall_period, capacity, week, warm):
    """Define server schedules dependant on warm start type.
    
    + Itterative: increase total arrival days to cover period
    + Warm Start: reduce capacity to 0 for specified days per activity
    """
    if warm_type == 'Itterative':
        total_arrival_days = int(warm*overall_period)
    else:
        total_arrival_days = int(1.5*overall_period)
    all_server_schedules = build_server_schedules(sim_type, capacity, total_arrival_days, week)

    if warm_type == 'Warm Start':
        if sim_type == 'Raw Pathways':
            warm = [0] + warm
        all_server_schedules_WS = copy.deepcopy(all_server_schedules)
        for i, wait in enumerate(warm):
            for w in range(wait):
                all_server_schedules_WS[i][w][0] = 0
        Schedules = all_server_schedules_WS
    else:
        Schedules = all_server_schedules

    return Schedules


#================= Plots =========================

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

    sum_facts = [abs(pair[0]-pair[1]) for pair in facts]
    smallest = min(sum_facts)
    shape = facts[sum_facts.index(smallest)]
    return shape

#---------------- Wait times ------------------

def plot_totaltime(save_location, simulation_name, df_all):
    """Plot histogram of total time in system."""
    fig, ax = plt.subplots(1, 1, figsize=[10, 10])
    
    # data for plot
    waits = [df_all['totaltime'][i] for i in range(len(df_all))]
    if int(max(waits)) < 20:
        bins = [i for i in range(0,int(max(waits)), 1)]
    else:
        bins = [i for i in range(0,int(max(waits)), 5)]

    # create plot
    ax.hist(waits, bins=bins)
    ax.set_title('Total Time in System - ' + simulation_name)
    ax.set_ylabel('Frequency')
    ax.set_xlabel('Days')
    if int(max(waits)) <= 40:
        ax.set_xticks(bins)
    elif int(max(waits)) <= 50:
        ax.set_xticks([i for i in range(0,int(max(waits)),10)])
        ax.set_xticks(bins)
    elif int(max(waits)) <= 100:
        ax.set_xticks([i for i in range(0,int(max(waits)),25)])
    else:
        ax.set_xticks([i for i in range(0,int(max(waits)),50)])

    # save
    plot_name = 'TotalTime_' + simulation_name
    fig.savefig(save_location + 'Plots/Simulation/' + plot_name + '.png', bbox_inches='tight', facecolor="None")    
    plt.close()


def plot_activity_waittimes(save_location, simulation_name, df_all, letters):
    """Plot histogram of waiting time per activity."""
    if letters[0] == '':
        letters = letters[1:]

    size = len(letters)
    shape = subplot_shape(size)
    fig, ax = plt.subplots(shape[1], shape[0], figsize=[shape[0]*5, shape[1]*5])
    pos = 0

    for l, letter in enumerate(letters):
        # data for plot
        waits = [df_all[letter][i] for i in range(len(df_all))]
        if simulation_name == 'original':
            waits = [x for x in waits if str(x) != 'nan']
        elif simulation_name == 'original_formatted':
            waits = [y for x in waits for y in x if str(y) != 'nan']
        else:
            waits = [y for x in waits for y in x if y != ' ']

        # if no waits, plot empty
        if sum(waits) != 0:
            if int(max(waits)) < 20:
                bins = [i for i in range(0,int(max(waits)), 1)]
            else:
                bins = [i for i in range(0,int(max(waits)), 5)]
            
            # create plot
            locy = int(pos/shape[0])
            locx = pos%shape[0]
            ax[locy, locx].hist(waits, bins=bins)
            ax[locy,locx].set_title(letter)
            ax[locy,locx].set_ylabel('Frequency', fontsize=14)
            ax[locy,locx].set_xlabel('Wait days', fontsize=14)
            if int(max(waits)) <= 30:
                ax[locy,locx].set_xticks(bins)
            elif int(max(waits)) <= 50:
                ax[locy,locx].set_xticks([i for i in range(0,int(max(waits)),10)])
                ax[locy,locx].set_xticks(bins)
            elif int(max(waits)) <= 100:
                ax[locy,locx].set_xticks([i for i in range(0,int(max(waits)),25)])
            else:
                ax[locy,locx].set_xticks([i for i in range(0,int(max(waits)),50)])
        else:
            locy = int(pos/shape[0])
            locx = pos%shape[0]
            ax[locy,locx].set_title(letter + ' - Always First Activity')
        pos+=1

    # remove blank subplots
    for i in range(shape[0]*shape[1] - size):
        fig.delaxes(ax.flatten()[size+i])
    fig.subplots_adjust(wspace=0.5, hspace=0.5)
    fig.suptitle('Wait Time per Activity - ' + simulation_name, y=0.94, fontsize=14)

    plot_name = 'Activity_Waits_' + simulation_name 
    fig.savefig(save_location + 'Plots/Simulation/' + plot_name + '.png', bbox_inches='tight', facecolor="None")     
    plt.close()


#---------------- Utilisation ------------------

def cap_utilisation(sim_recs, letters, min_date, max_date):
    """Gets capacity used per simulation day.
    
    Number remaining in queue at the end of each day recorded.
    """    

    all_cap_used = {}
    all_queue_remaining = {}
    for i, activity in enumerate(letters):
        n = i+2
        sim_recs_n = sim_recs[sim_recs.node == n]

        cap_used = []
        queue_remaining = []
        for day in range(min_date, max_date+1): # changed
            start_day = day - 1
            finish_day = day
            sec = sim_recs_n.loc[(sim_recs_n.service_start_date >= start_day) & 
                                         (sim_recs_n.service_start_date < finish_day)]
            # cpacity
            cap_used_day = len(sec)
            cap_used.append(cap_used_day)

            # queue remaining
            service_dates = [i for i in sec.service_end_date]
            if len(set(service_dates)) == 1:
                size = min(sec.queue_size_at_departure)
            else: 
                last_date = sec.service_end_date.max()
                size = sec.loc[sec.service_end_date == last_date].queue_size_at_departure.max()
            queue_remaining.append(size)

        all_cap_used[activity] = cap_used
        all_queue_remaining[activity] = queue_remaining
    
    return(all_cap_used, all_queue_remaining)


def actual_cap_reduced(server_schedule, all_cap_used, letters, min_date, max_date):
    """Gets capacity per day over server schedule period."""
    server_schedule = copy.deepcopy(server_schedule)
    # remove dummy server schedule
    if len(server_schedule) != len(letters):
        server_schedule.pop(0)
    
    all_actual_cap = [[i[0] for i in j] for j in server_schedule]
    actual_cap = [i[min_date-1:max_date] for i in all_actual_cap] # changed to collect from min to max date

    # added to account for ciw schedules loop
    repeat = max_date - len(all_actual_cap[0])
    if repeat > 0:
        repeat_extra = [i[0:repeat] for i in all_actual_cap]
        actual_cap = [actual + extra for actual, extra in zip(actual_cap, repeat_extra)]

    actual_cap_dict = {letter: actual_cap[i] for i,letter in enumerate(letters)}
    return actual_cap_dict


def cap_util_percentage(server_schedule, all_cap_used, letters, actual_cap):
    """Calculates percentage used of capacity avaliable each simulation day."""
    all_cap_perc_used = {}
    for i, activity in enumerate(letters):
        all_cap_used_n = all_cap_used[activity]
        actual_cap_n = actual_cap[activity]
        
        cap_perc_used = []
        for used, avaliable in zip(all_cap_used_n, actual_cap_n):
            if avaliable != 0:
                cap_perc_used.append(used/avaliable)
            else:
                cap_perc_used.append(np.nan)

        all_cap_perc_used[activity] = cap_perc_used
    
    return all_cap_perc_used


def plot_Perc_Cap_Used(all_cap_perc_used, save_location, simulation_name, min_date, max_date):
    """Plot the percentage of capacity used per simulation day."""
    plot_max = max_date - min_date + 1 # added to find the plot range
    x_days = [i for i in range(plot_max)] # changed to plot over plot_max range
    
    size = len(all_cap_perc_used)
    shape = subplot_shape(size)
    fig, ax = plt.subplots(shape[1], shape[0], figsize=[shape[0]*5, shape[1]*5])
    pos = 0

    for code, cap_perc in all_cap_perc_used.items():
        # create plot
        locy = int(pos/shape[0])
        locx = pos%shape[0]
        pos+=1
        ax[locy,locx].plot(x_days,cap_perc, marker='.') # added marker
        ax[locy,locx].set_title(code)
        ax[locy,locx].set_ylabel('Percentage', fontsize=14)
        ax[locy,locx].set_xlabel('Day', fontsize=14)

    # remove blank subplots
    for i in range(shape[0]*shape[1] - size):
        fig.delaxes(ax.flatten()[size+i])
    fig.suptitle('Percentage of Capacity Used - ' + simulation_name, y=0.9, fontsize=14)
    fig.subplots_adjust(wspace=0.5, hspace=0.5)

    plot_name = 'Utilisation_Percent_' + simulation_name 
    fig.savefig(save_location + 'Plots/Simulation/' + plot_name + '.png', bbox_inches='tight', facecolor="None")     
    plt.close()


def plot_queue_remaining(all_queue_remaining, save_location, simulation_name, min_date, max_date):
    """Plot the queue remaining at the end of each simulation day."""
    plot_max = max_date - min_date + 1 # added to find the plot range
    x_days = [i for i in range(plot_max)] # changed to plot over plot_max range
    
    size = len(all_queue_remaining)
    shape = subplot_shape(size)
    fig, ax = plt.subplots(shape[1], shape[0], figsize=[shape[0]*5, shape[1]*5])
    pos = 0

    for code, queue in all_queue_remaining.items(): # changed variable name
        # create plot
        locy = int(pos/shape[0])
        locx = pos%shape[0]
        pos+=1
        ax[locy,locx].plot(x_days,queue, marker='.') # changed variable name, added marker
        ax[locy,locx].set_title(code)
        ax[locy,locx].set_ylabel('Number of Individuals', fontsize=14)
        ax[locy,locx].set_xlabel('Day', fontsize=14)

    # remove blank subplots
    for i in range(shape[0]*shape[1] - size):
        fig.delaxes(ax.flatten()[size+i])
    fig.suptitle('Number in Queue at End of Day - ' + simulation_name, y=0.9, fontsize=14)
    fig.subplots_adjust(wspace=0.5, hspace=0.5)

    plot_name = 'Utilisation_Queue_' + simulation_name 
    fig.savefig(save_location + 'Plots/Simulation/' + plot_name + '.png', bbox_inches='tight', facecolor="None")     
    plt.close()


def util_results(all_cap_perc_used, week_type, min_date):
    """Reports total average percentage capacity used and average percentage capacity used per named day."""

    starting_day_adjust = (min_date-1)%7 # added for itterative to adjust for not starting on monday

    util_results_dict = {}
    for activity, cap_perc_used in all_cap_perc_used.items():
        possible_days = [cap_perc for cap_perc in cap_perc_used if np.isnan(cap_perc) != True] # added - no. possible days 
        all_util_100 = [round((len([i for i in cap_perc_used if i == 1.0])/len(possible_days))*100,2)] # percent of possible days run use 100% of capacity
        
        cap_perc_used = [np.nan]*starting_day_adjust +  cap_perc_used # added for itterative to adjust for not starting on monday

        day_perc = []
        for day in range(week_type):
            average_perc_day_list = [cap_per for i,cap_per in enumerate(cap_perc_used) if i % 7 == day] # collect all percent for named day
            average_perc_day_list = [average for average in average_perc_day_list if np.isnan(average) != True] # added for warm start and itterative - remove all nan
            if len(average_perc_day_list) == 0: # if never run on day
                day_perc.append(np.nan)                
            else:
                average_perc_day = (sum(average_perc_day_list)/len(average_perc_day_list))*100
                day_perc.append(round(average_perc_day,2))
            
        util_results_dict[activity] = all_util_100 + day_perc
        
    df_util_results = pd.DataFrame.from_dict(util_results_dict, orient='index')
    columns_names = ['Percentage Util 100%'] + ['Average Percent Util Day_' + str(day) for day in range(week_type)]
    df_util_results.columns = columns_names
    
    return df_util_results


def run_utilisation_results(sim_recs, letters, server_schedule, week_type, save_location, simulation_name):
    """Run utilisation results, including results table, percentage utilisation plot and remaining queue plot.
    
    Utilisation defined as percentage used of capacity avaliable.
    """
    # remove dummy node letter
    if letters[0] == '':
        letters = letters[1:]

    max_date = math.ceil(sim_recs.exit_date.max()) # added
    min_date = math.ceil(sim_recs.exit_date.min()) # added

    all_cap_used, all_queue_remaining = cap_utilisation(sim_recs, letters, min_date, max_date)
    actual_cap = actual_cap_reduced(server_schedule, all_cap_used, letters, min_date, max_date)
    all_cap_perc_used = cap_util_percentage(server_schedule, all_cap_used, letters, actual_cap)

    plot_Perc_Cap_Used(all_cap_perc_used, save_location, simulation_name, min_date, max_date)
    plot_queue_remaining(all_queue_remaining, save_location, simulation_name, min_date, max_date)

    df_util_results = util_results(all_cap_perc_used, week_type, min_date)

    return df_util_results


#-------------------- Trials ---------------------

def list_convert_results(raw_results, orient):
    """Convert dataframe results to list for confidence interval calculation preperation."""
    if orient == 'row':
        results = [r if isinstance(r, list) != True else r[1] for r in raw_results.iloc[0]]
        results = results[1:]
    if orient == 'column':
        results = [r for r in raw_results.iloc[:,1]]
    return results


def Confidence_Interval(results):
    """Calculate the mean and confidence interval."""
    pop_mean = float(statistics.mean(results))
    pop_std = float(statistics.pstdev(results))
    sq_n = float(math.sqrt(len(results)))
    z_95 = 1.96

    CI_L = pop_mean - z_95*(pop_std/sq_n)
    CI_U = pop_mean + z_95*(pop_std/sq_n)
    
    results = [round(pop_mean,2), [round(CI_L,2), round(CI_U,2)]]
    return results


def calculate_CI(All_Results):
    """Perform confidence interval calculation"""
    all_CI_results = []
    for result in range(len(All_Results[0])):
        converted_results = [row[result] for row in All_Results]
        results_CI = Confidence_Interval(converted_results)
        all_CI_results.append(results_CI)
    return all_CI_results


def T1_CI_results(T1, dataframe_T1, simulation_name, target):
    """Summarise trials results into single entry for table 1."""
    all_CI_results = calculate_CI(T1)
    all_CI_results = [simulation_name] + all_CI_results
    all_CI_results[3] = [target, all_CI_results[3]]
    # add to dataframe_T1
    all_results_T1_series = pd.Series(all_CI_results, index = dataframe_T1.columns)
    dataframe_T1 = dataframe_T1.append(all_results_T1_series, ignore_index=True)
    return dataframe_T1


def T2_T4_CI_results(T_2_4, dataframe_T2_T4, letters, model_name):
    """Summarise trial runs results into single entry for table 2 or 4."""
    all_CI_results = calculate_CI(T_2_4)

    # add to dataframe
    all_waiting_results = pd.DataFrame([[activity, all_CI_results[i]] for i,activity in enumerate(letters)])
    all_waiting_results.columns = ['Activity', model_name]
    dataframe_T2_T4 = dataframe_T2_T4.join(all_waiting_results.set_index('Activity'), on='Activity')
    return dataframe_T2_T4


def Standard_Deviation(All_Results, pos):
    """Calculate the standard deviation to evaluate number of trial runs required."""
    converted = [row[pos] for row in All_Results]
    if isinstance(converted[0], list) == True:
        converted = [row[1] for row in converted]

    stdev = float(statistics.pstdev(converted))
    
    return stdev


def plot_stdev(save_location, simulation_name, table_name, All_StDev, dataframe_T, runs, letters, orient):
    """Plot Standard deviation results per run.
    
    Figure not callable within GUI.
    """
    if orient == 'columns':
        titles = [column for column in dataframe_T.columns if column != 'Name']
    if orient == 'letters':
        titles = letters
        
    x_values = [i for i in range(runs)]

    size = len(titles)
    shape = subplot_shape(size)
    fig, ax = plt.subplots(shape[1], shape[0], figsize=[shape[0]*5, shape[1]*5])
    for result in range(size):
        locx = int(result%shape[0])
        locy = int(result/shape[0])
        list_results = [row[result] for row in All_StDev]
        ax[locy,locx].plot(x_values,list_results)
        ax[locy,locx].set_title(titles[result])
        ax[locy,locx].set_ylabel('Population Standard Deviation')
        ax[locy,locx].set_xlabel('Run')
        
    # remove blank subplots
    for i in range(shape[0]*shape[1] - size):
        fig.delaxes(ax.flatten()[size+i])
    fig.subplots_adjust(wspace=0.5, hspace=0.5)
    plot_name = simulation_name + '_' + table_name
    fig.suptitle(plot_name, y=0.94, fontsize=14)
    fig.savefig(save_location + 'Plots/Simulation/Trials/' + plot_name + '.png', bbox_inches='tight', facecolor="None")     
    plt.close()
