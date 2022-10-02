import argparse
import csv
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict


DT_FORMAT_PARSE = "%Y-%m-%dT%H:%M:%S"
DT_FORMAT_PRINT = "%d-%b-%Y, %H:%M" # Sep 15 2018 12:45
MIN_LAYOVER = timedelta(hours = 1) # layover time should not be less than 1 hour and more than 6 hours
MAX_LAYOVER = timedelta(hours = 6)

parser = argparse.ArgumentParser(description="Flight request")
parser.add_argument("datafile", help="path to SCV file with flights data")
parser.add_argument("origin", help="Source airport code")
parser.add_argument("destination", help="Destination airport code")
parser.add_argument("--bags", help="How many bags", default=0)
parser.add_argument("--return", dest="is_return", help="Is a return or one-way flight", action="store_true", default=False)
parser.add_argument("--json", dest="json_output", help="Generate ouptut JSON", action="store_true", default=False)
args = parser.parse_args()

datafile = args.datafile
origin = args.origin
destination = args.destination
bags = 0
is_return = False
json_output = False

if args.bags:
    bags = int(args.bags)

if args.is_return:
    is_return = args.is_return

if args.json_output:
    json_output = args.json_output

def log(s: str) -> None:
    if not json_output:
        print(s)

log(f"Requested {'return' if is_return else 'one-way'} flight from {origin} to {destination} with {bags} bags, datafile={datafile}")

class Airport:
    def __init__(self, code: str) -> None:
        self.code = code
        self.arrivals: List[Flight] = []
        self.departures: List[Flight] = []

    @property
    def departures_codes(self) -> List[str]:
        codes = []
        for flight in self.departures:
            codes.append(flight.destination)
        return sorted(list(set(codes)))
    
    def __repr__(self) -> str:
        return f"Airport {self.code} {len(self.departures)}/{len(self.arrivals)}" # CODE + Departures / Arrivals

class Flight:
    def __init__(self, dict: Dict) -> None:
        self.flight_no = dict["flight_no"]
        self.origin = dict["origin"]
        self.destination = dict["destination"]
        self.departure = datetime.strptime(dict["departure"], DT_FORMAT_PARSE)
        self.arrival = datetime.strptime(dict["arrival"], DT_FORMAT_PARSE)
        self.base_price = float(dict["base_price"])
        self.bag_price = float(dict["bag_price"])
        self.bags_allowed = float(dict["bags_allowed"])

    @property
    def duration(self) -> timedelta:
        return self.arrival - self.departure

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.isoformat() if (isinstance(o, datetime)) else o.__dict__, indent=4)

    def __repr__(self) -> str:
        return f"Flight {self.flight_no} {self.origin} > {self.destination}, dep: {self.departure.strftime(DT_FORMAT_PRINT)}, duration: {self.duration}"


class Trip:    
    def __init__(self, flights: List[Flight] = []) -> None:
        self.flights = flights
        self.origin = self.trip_origin
        self.destination = self.trip_destination
        self.total_price = self.trip_cost
        self.total_time = str(self.trip_duration)

    @property
    def trip_origin(self) -> str:
        return self.flights[0].origin

    @property
    def trip_destination(self) -> str:
        return self.flights[-1].destination

    @property
    def trip_duration(self) -> timedelta:
        return self.flights[-1].arrival - self.flights[0].departure

    @property
    def trip_cost(self) -> float:
        cost = 0.0
        for f in self.flights:
            cost += f.base_price + f.bag_price * bags
        return cost

    @property
    def bags_count_valid(self) -> bool:
        if any(f.bags_allowed < bags for f in self.flights):
            return False
        return True

    # def toJSON(self):
    #     data = {
    #         "flights": self.flights,
    #         "trip_origin": self.trip_origin,
    #         "trip_destination": self.trip_destination,
    #         "total_price": self.trip_cost,
    #         "total_time": str(self.trip_duration)
    #     }
    #     return json.dumps(data, default=lambda o: o.isoformat() if (isinstance(o, datetime)) else o.__dict__, indent=4)
    #     # return json.dumps(self, default=lambda o: o.isoformat() if (isinstance(o, datetime)) else o.__dict__, indent=4)

    def __repr__(self) -> str:
        return f"- {'Layover' if len(self.flights) > 1 else 'Direct'} Trip ({len(self.flights)}) {self.trip_origin} > {self.trip_destination} - {self.flights} - trip_duration: {self.trip_duration}, trip_cost: {self.trip_cost}"


def read_csv(file) -> List[Flight]:
    list = []
    with open (file, 'r') as csv_file:
        for line in csv.DictReader(csv_file):
            flight = Flight(line)
            list.append(flight)
        csv_file.close()
    return list

def filter_flights(data: List[Flight], origin, destination, bags) -> List[Flight]:
    # filtered = filter(lambda item: item["origin"] == origin or item["destination"] == destination, data)
    filtered = filter(lambda item: int(item.bags_allowed) >= bags, data)
    ls = list(filtered)
    log(f"filtered { len(ls)} flights")
    return ls




def search_combinations(flights, paths, origin, destination):
    bin = [] # to store found combinations

    def search_flight(origin, destination) -> Optional[Dict]:
        for flight in flights:
            if flight.origin == origin and flight.destination == destination:
                return flight
        return None

    def check_layover_time(arr, dep) -> bool:
        if dep < arr or dep - arr < MIN_LAYOVER or dep - arr > MAX_LAYOVER:
            return False
        return True

    for path in paths:

        # log("Processing path:", path)

        if len(path) == 2:
            # search direct flights:
            for index, flight in enumerate(flights):
                if flight.origin == origin and flight.destination == destination:
                    # log("Found direct flight", flight)
                    trip = Trip([flight])
                    if trip.bags_count_valid:

                        # for f in trip.flights:
                        #     print(f.to_json())

                        bin.append(trip)
                    # log(trip)

                    # flights.pop(index)

        if len(path) > 2:
            # search layover flights:
            trip_bin = []
            for i in range(len(path)-1):
                
                code_orig = path[i]
                code_dest = path[i+1]
                # log(f"Looking for flight from {code_orig} to {code_dest}...")
                for index, flight in enumerate(flights):
                    flight = search_flight(code_orig, code_dest)
                    if flight:
                        # check layover time
                        # log("Found layover flight", flight, trip_bin, i)
                        if len(trip_bin):
                            prev_flight = trip_bin[-1]
                            if not check_layover_time(prev_flight.arrival, flight.departure):
                                # log("Bad layover", flight.departure - prev_flight.arrival)
                                # trip_bin = []
                                continue
                            # else:
                                # log("Good layover", flight.departure - prev_flight.arrival)
                        trip_bin.append(flight)
                        # break
            if len(trip_bin) == len(path)-1:
                trip = Trip(trip_bin)
                if trip.bags_count_valid:

                    # for f in trip.flights:
                    #     print(f.to_json())

                    bin.append(trip)

        


                # pair = search_flight(o, d)
                # if pair and check_layover_time(flight.arrival, pair.departure):
                #     log(pair)



    # for index, flight in enumerate(flights):
    #     if flight.origin == origin:
    #             pair = search_flight(flight.destination, destination)
    #             if pair and check_layover_time(flight.arrival, pair.departure):
    #                 bin.append(Trip([flight, pair]))
    #                 flights.pop(index)
    #                 continue
    #     elif flight.destination == destination:
    #             pair = search_flight(origin, flight.destination)
    #             if pair and check_layover_time(flight.arrival, pair.departure):
    #                 bin.append(Trip([pair, flight]))
    #                 flights.pop(index)
    #                 continue


    bin = sorted(bin, key=lambda x: x.trip_cost, reverse=False) # sort trips by total price

    for item in bin:
        log(item)

    

    return bin


def construct_airports(flights: List[Flight]) -> Dict:
    # airports codes
    codes = []
    for f in flights:
        codes.append(f.origin)
        codes.append(f.destination)
    codes = sorted(list(set(codes))) # sorted without duplicates

    airports = {}
    for code in codes:
        airports[code] = Airport(code)

    # filling arrivals and departuses into airport objects
    for f in flights:
        airports[f.origin].departures.append(f)
        airports[f.destination].arrivals.append(f)

    # for a in airports:
        # log(airports[a].departures_codes)

    return airports

def make_airports_graph(airports: Dict) -> Dict:
    graph = {}
    for a in airports:
        graph[a] = airports[a].departures_codes
    return graph


def find_all_paths(graph, start, end, path=[]):
        path = path + [start]
        if start == end:
            return [path]
        if start not in  graph:
            return []
        paths = []
        for node in graph[start]:
            if node not in path:
                newpaths = find_all_paths(graph, node, end, path)
                for newpath in newpaths:
                    paths.append(newpath)
        return paths

if __name__ == '__main__':
    flights = read_csv(datafile)
    airports = construct_airports(flights)
    graph = make_airports_graph(airports)
    paths = find_all_paths(graph, origin, destination)

    # log(f"Paths ({len(paths)}): {paths}")

    # filtered = filter_flights(flights, origin, destination, bags)
    combinations = search_combinations(flights, paths, origin, destination)
    log(f"found { len(combinations)} flights combinations")

    if json_output:
        # for trip in combinations:
        print(json.dumps(combinations, default=lambda o: o.isoformat() if (isinstance(o, datetime)) else o.__dict__, indent=4))

    if is_return:
        return_paths = find_all_paths(graph, destination, origin)
        # log(f"Return paths ({len(return_paths)}): {return_paths}")
        return_combinations = search_combinations(flights, return_paths, destination, origin)
        log(f"found { len(return_combinations)} return flights combinations")
