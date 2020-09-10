import pandas as pd
import numpy as np
import re


def pos_to_char(pos):
    """Convert integer into character."""
    character = chr(int(65 + pos))

    return character


def codes(headersL):
    """Create a dictionary with an character code as key and column name as value."""
    x = -1
    activity_codes = {}
    for col_name in headersL:
        x += 1
        activity_codes[pos_to_char(x)] = col_name

    return activity_codes


def multi_headers(data, column_id):
    """Get column names, except unique id."""
    headers = [column for column in data.columns if column != column_id]

    return headers


def rename_duplicates(data, id_column, activity_column, dates_column):    
    """Rename duplicates by appending _value, ordered by date."""
    id_numbers = [data[id_column][i] for i in range(len(data))]
    # remove duplicates
    id_numbers = list(dict.fromkeys(id_numbers))

    for id_number in id_numbers:
        selected = data.loc[data[id_column] == id_number]
        set_selected = set(selected[activity_column])
        
        for activity in set_selected:
            selected_test = selected.loc[selected[activity_column] == activity]
            # create orderes list of dates of activity
            list_selected = sorted([i for i in selected_test[dates_column]])
            for x in range(len(selected_test)):
                row = selected_test.index[x]
                test_number = list_selected.index(selected_test[dates_column][row])
                # remove used date to catch multiples
                list_selected[test_number] = 'removed'
                data.at[row, activity_column] =  data[activity_column][row] + '_' + str(test_number)
                
    data = data.pivot(index=id_column, columns=activity_column, values=dates_column)
    index_data = pd.DataFrame([i for i in data.index], columns=[id_column])    
    data = index_data.join(data, on=id_column) 
                
    return data
    

def multi_codes(headersL):
    """This will create a dictionary with an character numeric code as key and column name as value, e.g. A0 : Test."""
    activity_codes = {}
    general_activity_codes = {}
    split = [header.split('_') for header in headersL]
    general = ['_'.join(header.split('_')[:-1]) for header in headersL]
    general_set = list(dict.fromkeys(general))
    
    for g, general_name in enumerate(general):
        index = general_set.index(general_name)
        activity_codes[pos_to_char(index) + split[g][-1]] = headersL[g]
        general_activity_codes[pos_to_char(index)] = general_set[index]

    return(general_activity_codes, activity_codes)


def condense_pathways(row):
    """Condense the two code pathways into first code only."""
    split_2 = re.findall('..', row.loc['multi_pathways'])
    remove = [code[0] for code in split_2]
    condense = ''.join(remove)

    return condense


def find_pathways(row, activity_codes):
    """Create a string from keys of dictionary in chronological date order."""
    activity = {
        code: row[activity_codes[code]] for code in activity_codes.keys()
    }
    order = [key for key in activity.keys() if pd.isna(activity[key]) != True]
    order.sort(key = lambda x: activity[x]) 

    return "".join(order)


def find_time_from_previous(row, cat, activity_codes):
    """Extract the number of days from the previous activity for single character codes."""
    if cat in row['pathways']:
        if row['pathways'][0] != cat:
            end_date = row[activity_codes[cat]]
            first_intervention = row['pathways'].split(cat)[0][-1]
            start_date = row[activity_codes[first_intervention]]
        else:
            return np.nan
        return (end_date - start_date).days

    return np.nan


def find_time_from_previous_Double(row, cat, activity_codes):
    """Extract the number of days from the previous activity for double character codes."""
    if cat in row['multi_pathways']:
        if row['multi_pathways'][0:2] != cat:
            end_date = row[activity_codes[cat]]
            # double character codes
            first_intervention = row['multi_pathways'].split(cat)[0][-2] + row['multi_pathways'].split(cat)[0][-1]
            start_date = row[activity_codes[first_intervention]]
        else:
            return np.nan
        return (end_date - start_date).days
        
    return np.nan


def create_Weightings(chosen_ranks):
    """Calculate the weighting based on the rank."""
    Rank = {}
    factor = 1/(len(chosen_ranks)-1)
    for code,rank in chosen_ranks.items():
        weight = 1 + (factor * (len(chosen_ranks)-1-rank))
        Rank[code] = weight

    return Rank


def freq_Rankings(activity_codes, data):
    """Rank keys based on frequency within df."""
    Rank = {}
    Total = {}
    i = 0
    for code in activity_codes.keys():
        total = data.str.contains(code).sum()
        Total[code] = total
    for code in sorted(Total, key=Total.get, reverse = True):
        Rank[code] = i
        i += 1

    return Rank

