import argparse
import csv
from datetime import datetime, timedelta
from typing import Optional, List, Dict



# 2021-09-01T21:15:00

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
args = parser.parse_args()

datafile = args.datafile
origin = args.origin
destination = args.destination
bags = 0
is_return = False

if args.bags:
    bags = int(args.bags)

if args.is_return:
    is_return = args.is_return

print(f"Requested {'return' if is_return else 'one-way'} flight from {origin} to {destination} with {bags} bags, datafile={datafile}")

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
    def duration(self):
        return self.arrival - self.departure

    def __repr__(self) -> str:
        return f"Flight {self.flight_no} {self.origin} > {self.destination}, dep: {self.departure.strftime(DT_FORMAT_PRINT)}, duration: {self.duration}"


class Trip:
    def __init__(self, flights: List[Flight] = []) -> None:
        self.flights = flights

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

    def __repr__(self) -> str:
        return f"- {'Layover' if len(self.flights) > 1 else 'Direct'} Trip {self.trip_origin} > {self.trip_destination} - {self.flights} - trip_duration: {self.trip_duration}, trip_cost: {self.trip_cost}"


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
    print(f"filtered { len(ls)} flights")
    return ls




def search_combinations(flights: List[Flight], origin, destination):
    bin = [] # to store found combinations

    def compare_origin_destination(flights, origin, destination) -> Optional[Dict]:
        for flight in flights:
            if flight.origin == origin and flight.destination == destination:
                return flight
        return None

    def check_layover_time(arr, dep) -> bool:
        if dep < arr or dep - arr < MIN_LAYOVER or dep - arr > MAX_LAYOVER:
            return False
        return True

    # search direct flights:
    for index, flight in enumerate(flights):
        if flight.origin == origin and flight.destination == destination:
            bin.append(Trip([flight]))
            flights.pop(index)

    # search layover flights:
    for index, flight in enumerate(flights):
        if flight.origin == origin:
                pair = compare_origin_destination(flights, flight.destination, destination)
                if pair and check_layover_time(flight.arrival, pair.departure):
                    bin.append(Trip([flight, pair]))
                    flights.pop(index)
                    continue
        elif flight.destination == destination:
                pair = compare_origin_destination(flights, origin, flight.destination)
                if pair and check_layover_time(flight.arrival, pair.departure):
                    bin.append(Trip([pair, flight]))
                    flights.pop(index)
                    continue

    for item in bin:
        print(item)

    print(f"found { len(bin)} combinations")

    return bin


if __name__ == '__main__':
    flights = read_csv(datafile)

    filtered = filter_flights(flights, origin, destination, bags)
    combinations = search_combinations(filtered, origin, destination)
