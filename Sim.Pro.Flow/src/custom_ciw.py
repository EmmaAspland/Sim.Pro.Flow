import ciw

from random import random
from math import isinf

from ciw.auxiliary import random_choice, flatten_list
from ciw.data_record import DataRecord
from ciw.server import Server


#========== Custom =============
# NEW
class CustomNode(ciw.Node):
    """Custom node to block service after slot capacity reached.
    
    Slot capacity is the number of servers.
    """
    def __init__(self, id_, simulation):
        super().__init__(id_, simulation)
        self.current_count = 0 # added
    
    def begin_service_if_possible_accept(self, next_individual):
        """Custom node to 

        Begins the service of the next individual (at acceptance point):
          - give an arrival date and service time
          - if there's a free server, give a start date and end date
          - attach server to individual
        """
        self.slot_capacity = self.c # include this if we want capacity=servers
        next_individual.arrival_date = self.get_now()
        free_server = self.find_free_server()
        if (free_server is not None or isinf(self.c)) and (self.current_count < self.slot_capacity): # added
            self.current_count += 1 # added
            # indented
            next_individual.service_start_date = self.get_now()
            next_individual.service_time = self.get_service_time(next_individual)
            next_individual.service_end_date = self.increment_time(
                self.get_now(), next_individual.service_time)
            if free_server is not None:
                self.attach_server(free_server, next_individual)

    def begin_service_if_possible_release(self):
        """
        Begins the service of the next individual (at point
        of previous individual's release)
          - check if there are any interrupted individuals
            left to restart service
          - give an arrival date and service time
          - give a start date and end date
          - attach server to individual
        """
        self.slot_capacity = self.c # include this if we want capacity=servers
        srvr = self.find_free_server()
        if (srvr is not None) and (self.current_count < self.slot_capacity): # added
            # indented
            if self.number_interrupted_individuals > 0:
                self.begin_interrupted_individuals_service(srvr)
            else:
                for ind in self.all_individuals:
                    if not ind.server:
                        self.current_count += 1 # added
                        ind.service_start_date = self.get_now()
                        ind.service_time = self.get_service_time(ind)
                        ind.service_end_date = self.increment_time(
                            ind.service_start_date, ind.service_time)
                        self.attach_server(srvr, ind)
                        break

    def begin_service_if_possible_change_shift(self):
        """
        If there are free servers after a shift change:
          - restart interrupted customers' services
          - begin service of any waiting cutsomers
            - give a start date and end date
            - attach servers to individual
        """
        self.slot_capacity = self.c # include this if we want capacity=servers
        if self.current_count < self.slot_capacity: # added
            # indented
            free_servers = [s for s in self.servers if not s.busy]
            for srvr in free_servers:
                if self.number_interrupted_individuals > 0:
                    self.begin_interrupted_individuals_service(srvr)
                else:
                    for ind in self.all_individuals:
                        if not ind.server:
                            self.current_count += 1 # added
                            ind.service_start_date = self.get_now()
                            ind.service_time = self.get_service_time(ind)
                            ind.service_end_date = self.increment_time(
                                ind.service_start_date, ind.service_time)
                            self.attach_server(srvr, ind)
                            break

    def change_shift(self):
        """
        Implment a server shift change:
         - adds / deletes servers, or indicates which servers should go off duty
         - begin any new services if free servers
        """
        # dont reset unless something happens - if we dont want to change evry day but every x days, need if statement
        self.current_count = 0 # added
        shift = self.next_event_date % self.cyclelength

        try:
            indx = self.schedule.index(shift)
        except:
            tms = [obs[0] for obs in self.schedule]
            diffs = [abs(x - float(shift)) for x in tms]
            indx = diffs.index(min(diffs))

        self.take_servers_off_duty()
        self.add_new_servers(indx)

        self.c = self.schedule[indx][1]
        self.next_shift_change = next(self.date_generator)
        self.begin_service_if_possible_change_shift()


class LimitedDeterministic(ciw.dists.Deterministic):
    """
    Effectively stops cusomers arriving after limit reached
    Deterministic Distribution
    """
    def __init__(self, rate, limit):
        super().__init__(rate)
        self.limit = limit
        self.number_of_customers_sampled = 0
    
    def sample(self, t=None, ind=None):
        if self.number_of_customers_sampled < self.limit:
            self.number_of_customers_sampled += 1
            return super().sample()
        else:
            return float('Inf')


class LimitedExponential(ciw.dists.Exponential):
    """
    Effectively stops cusomers arriving after limit reached
    Exponential Distribution
    """
    def __init__(self, rate, limit):
        super().__init__(rate)
        self.limit = limit
        self.number_of_customers_sampled = 0
    
    def sample(self, t=None, ind=None):
        if self.number_of_customers_sampled < self.limit:
            self.number_of_customers_sampled += 1
            return super().sample()
        else:
            return float('Inf')
            
#=========================================================
