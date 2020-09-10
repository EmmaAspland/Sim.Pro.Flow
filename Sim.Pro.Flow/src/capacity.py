from scipy.stats import poisson
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sympy as sp
import math
from collections import Counter
from tqdm import tqdm
import datetime
import copy
from sympy.abc import a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z

#===============================================================================================
# Preperation

def list_column(column, original_name):
    """Get all non nan values from column."""
    if original_name == 'original_formatted':
        list_filled = [[x for x in row if str(x) != 'nan'] for row in column]
    else:
        list_filled = [[_] for _ in column]  
    return list_filled


def Dict_num_activity(list_filled):  
    """Get the number of times each activity was performed per individual."""
    num_activity = []
    for _ in list_filled:
        if len(_) == 1:
            if pd.isna(_[0]) == True:
                num = 0
            else:
                num = 1
        else:
            num = len(_)
        num_activity.append(num)
    Counter_num_activity = Counter(num_activity)
    return Counter_num_activity    


def List_num_activity(Counter_num_activity):
    """Gets list from counter of number each activity was performed per individual."""
    num_activity = [k for k in Counter_num_activity.keys()]
    num_activity.sort()
    counts_num_activity = [Counter_num_activity[v] for v in num_activity]
    counts_num_activity_non_zero = sum([Counter_num_activity[v] for v in num_activity if v != 0])
    return(num_activity, counts_num_activity, counts_num_activity_non_zero)


def get_column_time_period(column):
    """Gets the total time period covered in a column."""
    dates = [date for date in column if pd.isna(date) != True] 
    if dates != []:
        column_min = min(dates)
        column_max = max(dates)
        column_period = column_max - column_min
        column_period = column_period.days
    else:
        column_min = datetime.datetime.max
        column_max = datetime.datetime.min
        column_period = column_min
    # include start and end day
    column_period += 1
    return(column_min, column_max, column_period)


def get_total_time_period(data, headers):
    """Gets the total time period covered in the data."""
    overall_min = datetime.datetime.max
    overall_max = datetime.datetime.min
    for column in headers:
        column_min, column_max, column_period = get_column_time_period(data[column])
        if column_min < overall_min:
            overall_min = column_min
        if column_max > overall_max:
            overall_max = column_max
    overall_period = overall_max - overall_min
    overall_period = overall_period.days
    return(overall_min, overall_max, overall_period)

#===============================================================================================

def ArrivalPoissonDistribution(occurances):
    """Create Poisson distribution of number of activity per day."""
    Max = poisson.ppf(0.99, occurances)
    referals = [i for i in range(0,int(Max)+1)]
    prob = poisson.pmf(referals, occurances)
    prob[-1] = prob [-1] + 1-sum(prob)
    return(referals, prob)


def PlotArrivalPoissonDistriution(referals, prob, input, save):
    """Stem plot of arrival Poisson distribution."""
    fig, ax = plt.subplots()   
    ax.stem(referals, prob, use_line_collection=True, basefmt="grey")
    ax.set_ylabel('Probability')
    ax.set_xlabel('Incoming Referrals')
    ax.set_title('Arrival Distribution (Av. Rate =' + str(round(input,3)) + ')')
    plt.grid()
    if save == True:
         plt.savefig('Probability_incoming_patients.png')   
    plt.close()

#===============================================================================================

def expansion(num_num_activity, patients):
    """Performs bionomial expansion."""
    # Will work for a maximum of letter in alphabet
    convert = [chr(97 + int(num)) for num in range(num_num_activity)]
    eq = '(' + ' + '.join(convert) +')**' + str(patients)
    ex_eq = str(eval(eq).expand())
    return(ex_eq, convert)


def nDemand(num_activity, patients, p_num_activity, size):
    """Probability of number of activity being performed (columns), per number of individuals arriving (rows)."""
    f_zero = [0 for i in range(num_activity[0]*patients)]
    formula, convert = expansion(len(p_num_activity), patients)
    
    for num, let in enumerate(convert):
        formula = formula.replace(let, str(p_num_activity[num]))
    formula = formula.split(' + ')
    formula_2 = [eval(formula[i]) for i,j in enumerate(formula)]
    
    e_zero = [0 for i in range(size-len(f_zero)-len(formula_2))]
    row = f_zero + formula_2 + e_zero
    
    return row


def nDemand_dot_prob(nDemand, prob):
    """Dot product of the arrivals probability distribution with demand matrix."""
    # Transponse nDemand matrix
    nDemand_T = [list(i) for i in zip(*nDemand)]    
    nDemand_T_array = np.array(nDemand_T)
    demand = nDemand_T_array.dot(prob)
    # Ensure demand sum to 1
    demand_sum = sum(demand)
    demand[-1] = demand[-1] - (demand_sum-1)
    return demand


def expected(demand, max_x2):
    """Returns the expected value of number of activity."""
    all_referals = [i for i in range(0,max_x2)]
    expected_value = sum([a*b for a,b in zip(demand,all_referals)])
    return(all_referals, expected_value)


def PlotProbRequests(all_referals, demand, expected_value, save):
    """Stem plot of probabiilty of number activity requests."""
    fig, ax = plt.subplots()   
    ax.stem(all_referals, demand, use_line_collection=True, basefmt="grey")
    ax.set_ylabel('Probability')
    ax.set_xlabel('Requests')
    ax.set_title('(Av. Rate =' + str(expected_value) + ')')
    plt.grid()
    if save == True:    
        plt.savefig('Probability_requests.png')
    plt.close()


def PlotCumulativeRequests(cumulative, referals, save):
    """Stem plot of cumulative probabiilty of number activity requests."""
    fig, ax = plt.subplots()   
    ax.stem(referals,cumulative , use_line_collection=True, basefmt="grey")
    ax.set_ylabel('Cumulative Probability')
    ax.set_xlabel('Requests')
    plt.grid()
    if save == True:
        plt.savefig('Probability_requests_cumulative.png')
    plt.close()


#===============================================================================================

def p_sequence(expected_value, days_a_week, upper_bound, step):
    """Calcualtes the capacity values to test."""
    lower_p = math.ceil(days_a_week*expected_value/0.99)
    # PSEQ per week, pseq per day
    PSEQ = sorted(list(set([int(lower_p + step*i) for i in range(upper_bound)])))
    pseq = [round(i/days_a_week, 2) for i in PSEQ]
    return(pseq, PSEQ)


def TransMatrix(demand, c):
    """Constriuct transition matrix. 
    
    If capacity < requests then remainder requests left in queue.
    """
    D = []
    max = 999
    for k in range(max+1):
        row = [0 for i in range(max)]
        if k <= c:
            row[0:len(demand)-1] = demand
            D.append(row)
        else:
            row[k-c:k-c+len(demand)-1] = demand
            if len(row) > max + 1:
                difference = len(row) - (max + 1)
                row[len(row)-difference-1:len(row)] = [sum(row[len(row)-difference-1:len(row)])]
            D.append(row)
    return D


def SteadyState(P_matrix, eps):
    """Calculates the steady state of the matrix."""
    error = 1
    pi = np.array([1/1000 for i in range(1000)])
    count = 0
    while error > eps:
        count += 1
        previous = pi
        pi = pi.dot(P_matrix)
        error = max(abs( pi - previous ))
    return pi


def data_all_pi(pseq, PSEQ, demand, eps):        
    """Apply steady state calculation to combined capacity matrix."""
    all_pi = pd.DataFrame()
    for a, p_c in enumerate(pseq):
        alpha = round(p_c%1,2)
        C = [math.floor(p_c), math.ceil(p_c)]
        c_lower_matrix = TransMatrix(demand, C[0])   
        c_upper_matrix = TransMatrix(demand, C[1])   
        alpha_c_lower_matrix = np.array([[i*(1-alpha) for i in j] for j in c_lower_matrix])
        alpha_c_upper_matrix = np.array([[i*(alpha) for i in j] for j in c_upper_matrix])
        P_matrix = alpha_c_lower_matrix + alpha_c_upper_matrix
        solved_pi = SteadyState(P_matrix, eps)
        all_pi[PSEQ[a]] = solved_pi
    return all_pi


def PlotSteadyState(all_pi, PSEQ, use_default_max_plot):
    """Plot the steady state probability of number in queue."""
    if use_default_max_plot == True:
        max_plot = 50
    plot_p = pd.DataFrame(all_pi.loc[:max_plot])
    
    fig, ax = plt.subplots()   
    for a, alpha in enumerate(PSEQ):
        ax.plot(plot_p.index, plot_p[alpha], label=str(alpha))
    ax.legend(loc='best')
    ax.set_ylabel('Steady State Probability')
    ax.set_xlabel('Queued Tests')
    plt.grid()
    plt.close()


def WaitDays(all_pi, pseq, PSEQ, default_view):    
    """Convert steady state queued into wait days."""
    waitdays_data = copy.deepcopy(all_pi)
    waitdays_grouped = pd.DataFrame()

    if default_view == True:
        view = 25
    else:
        view = default_view

    for a, p_c in enumerate(pseq):
        alpha = round(p_c%1,2)
        C = [math.floor(p_c), math.ceil(p_c)]
        waitdays_name = 'waitdays_' + str(PSEQ[a])
        waitdays_data[waitdays_name] = [math.ceil(i/((C[0]*(1-alpha)) + (C[1]*alpha))) for i in range(len(waitdays_data))]
        column_name = 'cumulative_' + str(PSEQ[a])
        waitdays_data[column_name] = 1 - waitdays_data[PSEQ[a]].cumsum()

        waitdays_grouped_alpha = copy.deepcopy(waitdays_data)
        waitdays_grouped_alpha = waitdays_grouped_alpha.groupby([waitdays_name]).min()
        waitdays_grouped_alpha = waitdays_grouped_alpha.loc[:view]
        waitdays_grouped_alpha.loc[0] = [1 for i in waitdays_grouped_alpha.loc[0]]    
        waitdays_grouped[column_name] = waitdays_grouped_alpha[column_name]
        if len(waitdays_grouped) != view:
            format_dataframe = pd.DataFrame([0 for i in range(view)])
            waitdays_grouped = format_dataframe.join(waitdays_grouped)
    waitdays_grouped.index.rename('waitdays', inplace=True)

    return(waitdays_data, waitdays_grouped)


def PlotWaitDays(axes, waitdays_data_grouped, activity, percent_target, days_target, PSEQ, use_default_max_plot):
    """Plot probability of wait days."""
    if use_default_max_plot == True:
        max_plot = 25

    waitdays_plot = waitdays_data_grouped.copy()
    waitdays_plot = waitdays_plot.loc[:max_plot]
    waitdays_plot.loc[0] = [1 for i in waitdays_plot.loc[0]]

    for a, alpha in enumerate(PSEQ):
        column_name = 'cumulative_' + str(alpha)
        axes.plot(waitdays_plot.index, waitdays_plot[column_name], label=str(alpha))
    axes.legend(loc=10, bbox_to_anchor=(0.85, 0, 0.5, 1))
    axes.set_ylim(0,1)
    axes.set_yticks(np.arange(0, 1.1, step=0.1))
    axes.set_ylabel('Probability')
    axes.set_xlabel('Wait time (t working days)')
    axes.set_title(activity + '_' + str(percent_target) + '_' + str(days_target))
    axes.grid()

def target_capacity(waitdays_data_grouped, days_target, percent_target):
    """Return the capacity necessecary to achieve percetage wait days target."""
    target_row = waitdays_data_grouped.loc[waitdays_data_grouped.index == days_target]
    target_row_list = target_row.values.flatten().tolist()
    target_range = [i for i in target_row_list if i < percent_target]
    outcome_percentage = max(target_range)
    
    outcome_column = target_row.columns[(target_row == outcome_percentage).iloc[0]][0]
    outcome_capacity = outcome_column.split('_')[-1]
    
    return(outcome_capacity)

#====================================================================================================
# Run Capacity


def run_capacity(column, period, original_name):
    """Run the initial analysis for capacity.
    
    Returns expected value and demand.
    """
    list_filled = list_column(column, original_name)
    Counter_num_activity = Dict_num_activity(list_filled)
    num_activity, counts_num_activity, counts_num_activity_non_zero = List_num_activity(Counter_num_activity)

    arrivals = counts_num_activity_non_zero/period

    num_patients = len(column)
    prob_num_test = []
    for p in counts_num_activity:
        prob_num_test.append(p/num_patients)

    referals, prob = ArrivalPoissonDistribution(arrivals)
        
    p_num = np.array(prob_num_test)
    size = num_activity[-1] * referals[-1]
    nDemand_matrix = [nDemand(num_activity, patients, p_num, size+1) for patients in referals]
    
    demand = nDemand_dot_prob(nDemand_matrix, prob)
    all_referals, expected_value = expected(demand, size+1)

    return(expected_value, demand)


def run_steady_state(activity, expected_value, demand, days_a_week, upper_bound, step, eps, default_view):
    """Run steady state calculation.
    
    Returns waitdays raw data, waitdays grouped by day and PSEQ values.
    """
    pseq, PSEQ = p_sequence(expected_value, days_a_week, upper_bound, step)
    all_pi = data_all_pi(pseq, PSEQ, demand, eps)

    waitdays_data, waitdays_data_grouped = WaitDays(all_pi, pseq, PSEQ, default_view=default_view)
    
    return(waitdays_data, waitdays_data_grouped, PSEQ)


def subplot_shape(size):
    """Get the most square shape for the plot axes values.

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


def run_target_capacity(save_location, num_calcs, data, activity_codes, calculated_cap, cap_input_dict, overall_period, days_a_week, original_name, eps):
    """Run all functions necessecary to calculate the weekly capacity required to achieve percentage wait days target."""
    weekly_capacity_dict = {}
    size = len([code for code, values in cap_input_dict.items() if values[5] == 'Yes'])
    shape = subplot_shape(size)
    fig, ax = plt.subplots(shape[1], shape[0], figsize=[shape[0]*5, shape[1]*5])
    pos=0

    for a, code in tqdm(enumerate(activity_codes.keys())):
        if cap_input_dict[code][5] == 'Yes':
            percent_target, days_target, step_times, step_inc = int(cap_input_dict[code][0]), int(cap_input_dict[code][1]), int(cap_input_dict[code][2]), int(cap_input_dict[code][3])
            percent_target = round(1 - percent_target/100,2)

            if original_name == 'original_formatted':
                expected_value, demand = run_capacity(data[code], overall_period, original_name)
            else:
                expected_value, demand = run_capacity(data[activity_codes[code]], overall_period, original_name)
            if expected_value == 0.0:
                weekly_capacity_dict[code] = 'Error: Expected_Value_Too_Small'
            else:
                waitdays_data, waitdays_data_grouped, PSEQ = run_steady_state(code, expected_value, demand, days_a_week, step_times, step_inc, eps, int(cap_input_dict[code][4]))

                if shape[0] == 1:
                    if shape[1] == 1:
                        axes = ax
                    else:
                        axes = ax[pos]
                else:
                    axes = ax[int(pos/shape[0]), pos%shape[0]]
                pos+=1
                PlotWaitDays(axes, waitdays_data_grouped, code, percent_target, days_target, PSEQ, True)
                
                weekly_capacity = target_capacity(waitdays_data_grouped, days_target, percent_target)                
                weekly_capacity_dict[code] = weekly_capacity

    # merge results
    calculated_cap = {key: [percent_target, days_target, weekly_capacity_dict[key], 'Yes'] if key in weekly_capacity_dict else [value[0], value[1], value[2], 'No'] for key, value in calculated_cap.items()}

    # remove blank subplots
    for i in range(shape[0]*shape[1] - size):
        fig.delaxes(ax.flatten()[size+i])
    fig.subplots_adjust(wspace=0.5, hspace=0.5)
    calc_name = 'Cal_Cap_' + str(num_calcs)
    fig.savefig(save_location + 'Plots/Capacity/' + calc_name + '.png', bbox_inches='tight', facecolor="None")  
    plt.close()

    return(calc_name, calculated_cap)

