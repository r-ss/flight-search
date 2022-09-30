import argparse
import csv
from typing import Optional, List, Dict


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

def read_csv(file) -> List[Dict]:
    list = []
    with open (file, 'r') as csv_file:
        for line in csv.DictReader(csv_file):
            list.append(line)
        csv_file.close()
    return list

def filter_flights(data, origin, destination, bags) -> List[Dict]:
    filtered = filter(lambda item: item["origin"] == origin or item["destination"] == destination, data)
    filtered = filter(lambda item: int(item["bags_allowed"]) >= bags, filtered)
    return list(filtered)

def search_combinations(flights, origin, destination):
    bin = []

    for flight in flights:
        print(flight)
        if flight["origin"] == origin and flight["destination"] == destination:
            bin.append(f"{origin} > {destination}")
        else:
            if flight["origin"] == origin:
                bin.append(f"{origin} > {flight['destination']}")

    for item in bin:
        print(item)

    return bin


if __name__ == '__main__':
    # main()
    data = read_csv(datafile)

    filtered = filter_flights(data, origin, destination, bags)
    # print(filtered)
    print(len(filtered))
    zzz = search_combinations(filtered, origin, destination)

# print(args.datafile)
# print(args.code_from)
# print(args.code_to)