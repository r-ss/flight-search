# Python weekend entry task solution

**Python script for search flights between airports A -> B from raw CSV flights data including meaningful layover options**

Task description is [here](https://github.com/kiwicom/python-weekend-entry-task)

## How to run

Just clone and run:

```bash
python solution.py csv-data-examples/example1.csv DHE NRX --bags=1 --return
```
This request will perform a search for flights from airport DHE -> NRX and back NRX -> DHE for flights which allow at least 1 piece of baggage.

To get a more readable and compact output into a console instead of JSON format, add `--console` parameter:

```bash
python solution.py csv-data-examples/example2.csv GXV YOT --console
```
This request will find flights GXV -> YOT and print results into a console

## Required positional arguments

| Argument name | type    | Description                          |
|---------------|---------|--------------------------------------|
| `datafile`    | string  | Path to SCV file with flights data   |
| `origin`      | string  | Source airport code                  |
| `destination` | string  | Destination airport code             |

## Optional arguments

| Argument name | type    | Description              | Notes                       |
|---------------|---------|--------------------------|-----------------------------|
| `bags`        | integer | Number of requested bags | Optional (default is 0)     |
| `return`      | boolean | Is it a return flight?   | Optional (default is false) |
| `console`     | boolean | Output into a console    | Optional (default is false) |

## Search restrictions
- In case of a combination of A -> B -> C, the layover time in B will be **not less than 1 hour and more than 6 hours**.
- No repeating airports in the same trip.
    - A -> B -> A -> C is not a valid combination for search A -> C.
- Output is sorted by the final price of the trip.

## Approach

Python 3.10, only standard library used, no 3rd party packages
Graph, deep first search