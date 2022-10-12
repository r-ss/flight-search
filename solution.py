"""
Author: Alexey Antipov
https://github.com/r-ss
https://www.linkedin.com/in/alexantipov/
"""

import argparse
import csv
import json
import timeit
import bisect
import copy
from datetime import datetime, timedelta
from typing import List, Dict


DT_FORMAT_READABLE = "%d-%b-%Y, %H:%M" # Sep 15 2018 12:45
MIN_LAYOVER = timedelta(hours = 1) # layover time should not be less than 1 hour and more than 6 hours
MAX_LAYOVER = timedelta(hours = 6)

parser = argparse.ArgumentParser(description="Flight request")
parser.add_argument("datafile", help="Path to SCV file with flights data")
parser.add_argument("origin", help="Source airport code")
parser.add_argument("destination", help="Destination airport code")
parser.add_argument("--bags", help="How many bags", default=0)
parser.add_argument("--return", dest="is_return", help="Is a return or one-way flight", action="store_true", default=False)
parser.add_argument("--console", dest="console", help="Output to console instead of JSON", action="store_true", default=False)
args = parser.parse_args()

datafile = args.datafile
origin = args.origin
destination = args.destination
bags = 0
is_return = False
json_output = True

if args.bags:
    bags = int(args.bags)

if args.is_return:
    is_return = args.is_return

if args.console:
    json_output = not args.console

def log(s: str) -> None:  # util to print
    if not json_output:
        print(s)

log(f"Requested {'return' if is_return else 'one-way'} flight from {origin} to {destination} with {bags} bags, datafile={datafile}")

class Flight:
    """ Represents flight from one airport to another """
    def __init__(self, dict: Dict) -> None:
        self.flight_no = dict["flight_no"]
        self.origin = dict["origin"]
        self.destination = dict["destination"]
        self.departure = datetime.fromisoformat(dict["departure"])
        self.arrival = datetime.fromisoformat(dict["arrival"])
        self.base_price = float(dict["base_price"])
        self.bag_price = float(dict["bag_price"])
        self.bags_allowed = float(dict["bags_allowed"])

    @property
    def duration(self) -> timedelta:
        return self.arrival - self.departure

    def __repr__(self) -> str:
        return f"Flight {self.flight_no} {self.origin} > {self.destination}, dep: {self.departure.strftime(DT_FORMAT_READABLE)}, duration: {self.duration}"

class Trip:
    """ Represents complete trip from one airport to another with or without layover(s) """
    def __init__(self, origin):
        self.origin = origin
        self.destination = origin
        self.departure = None
        self.arrival = None
        self.flights = []
    
    def add_flight(self, flight: Flight) -> None:
        if flight.origin != self.destination:
            raise ValueError(f"Arrival and departure airports do not match {self.destination}, {flight['origin']}")
        new_trip = self.copy()
        new_trip.destination = flight.destination
        new_trip.flights.append(flight)
        if self.departure is None:
            new_trip.departure = flight.departure
        new_trip.arrival = flight.arrival
        return new_trip 

    @property
    def trip_duration(self) -> timedelta:
        return self.flights[-1].arrival - self.flights[0].departure

    @property
    def trip_cost(self) -> float:
        cost = 0.0
        for f in self.flights:
            cost += f.base_price + f.bag_price * bags
        return cost
    
    def copy(self):
        """ semi-deep copy including its own copy of list of flights but excluding each flight itself """

        new_trip = copy.copy(self)
        new_trip.flights = self.flights.copy()
        return new_trip 

    def __repr__(self) -> str:
        return f"- {'Layover' if len(self.flights) > 1 else 'Direct'} Trip ({len(self.flights)}) {self.origin} > {self.destination} - {self.flights} - trip_duration: {self.trip_duration}, trip_cost: {self.trip_cost}"


class Schedule:
    """ Represents schedule of flight in a form of dict by origin key """

    def __init__(self, flights: List[Flight]) -> None:
        self.flights_dict = {}
        self.load_schedule(flights)

    def load_schedule(self, flights: List[Flight]) -> None:
        for flight in flights:
            if flight.origin not in self.flights_dict:
                self.flights_dict[flight.origin] = []
            self.flights_dict[flight.origin].append(flight)
    
    def get_departures(self, origin, time_from=None, time_to=None, excluded_destinations=None):
        """ Get all flights departing from origin """

        if origin not in self.flights_dict:
            return []
        departing_flights = self.flights_dict[origin]
        if time_from is not None:
            # choose only flights with departure later than time_from
            i = bisect.bisect_left(departing_flights, time_from, key=lambda x: x.departure)
            departing_flights = departing_flights[i:]
        if time_to is not None:
            # choose only flights with departures earlier than time_to
            i = bisect.bisect_right(departing_flights, time_to, key=lambda x: x.departure)
            departing_flights = departing_flights[:i]
        if excluded_destinations is not None:
            # filter out excluded destinations
            departing_flights = [flight for flight in departing_flights if flight.destination not in excluded_destinations]

        return departing_flights

    def search(self, origins, destinations, is_return=False):
        """ Search all flights according to parameters and return them as list of trips """

        def dfs(trip, visited):  # deep first search - outbound journey
            results = []
            if trip.destination in destinations:
                return [trip]  # already at destination
            else:
                # transfers left
                excluded_destinations = origins + visited 
                if len(visited) == 1:  # first flight in trip
                    time_from = None
                    time_to = None
                else:  # transfer
                    time_from = trip.arrival+MIN_LAYOVER
                    time_to = trip.arrival+MAX_LAYOVER
                departing_flights = self.get_departures(trip.destination, 
                                                               time_from=time_from,
                                                               time_to=time_to,
                                                               excluded_destinations=excluded_destinations)
                for flight in departing_flights:  # search all possible connections
                    new_trip = trip.add_flight(flight)
                    new_visited = visited.copy()
                    new_visited.append(flight.destination)
                    results.extend(dfs(new_trip, new_visited))
            
            return results
        
        def dfs_back(trip, visited):  # deep first search - return journey
            results = []
            if trip.destination == trip.origin:  # back at origin, finish the trip
                return [trip]
            else:
                excluded_destinations = visited
                if len(visited) == 1:  # first flight of return journey
                    time_from = trip.arrival
                    time_to = None
                else:  # transfer
                    time_from = trip.arrival+MIN_LAYOVER
                    time_to = trip.arrival+MAX_LAYOVER
                departing_flights = self.get_departures(trip.destination, 
                                                        time_from=time_from,
                                                        time_to=time_to,
                                                        excluded_destinations=excluded_destinations)
                for flight in departing_flights:  # search all possible connections
                    new_trip = trip.add_flight(flight)
                    new_visited = visited.copy()
                    new_visited.append(flight.destination)
                    results.extend(dfs_back(new_trip, new_visited))
            
            return results
        
        # check if all airport codes exist
        for origin in origins:
            if origin not in self.flights_dict:
                raise KeyError(f'Bad origin airport code {origin}')
        for destination in destinations:
            if destination not in self.flights_dict:
                raise KeyError(f'Bad destination airport code {destination}')
        if set(origins).intersection(destinations):
            raise ValueError('Overlap')

        results = []
        for origin in origins:
            trip = Trip(origin)
            results = dfs(trip, [origin])
        
        if is_return:  # search return flights
            outbound_results = results
            results = []
            for trip in outbound_results:
                results.extend(dfs_back(trip, [trip.destination]))
        
        results.sort(key=lambda x: x.trip_cost, reverse=False) # sort trips by total price
        return results
    

def read_csv(file) -> List[Flight]:
    list = []
    with open (file, 'r') as csv_file:
        for line in csv.DictReader(csv_file):
            flight = Flight(line)
            list.append(flight)
        csv_file.close()
    return list


def print_trips_as_json(trips: List[Trip]) -> None:
    print(json.dumps(trips, default=lambda o: o.isoformat() if (isinstance(o, datetime)) else o.__dict__, indent=4))


if __name__ == '__main__':
    benchmark_start = timeit.default_timer()

    flights = read_csv(datafile)
    flights = list(filter(lambda f: (f.bags_allowed >= bags), flights))  # filter all flights by bags number

    schedule = Schedule(flights)
    combinations = schedule.search([origin], [destination], is_return=is_return)
    benchmark_end = timeit.default_timer() - benchmark_start
    for c in combinations:
        log(c)
    log(f"found { len(combinations)} flights combinations in {benchmark_end:.2f} s")

    if json_output:
        print_trips_as_json(combinations)

"""

Thanks for interesting task
I'm looking for the remote job now.

"""