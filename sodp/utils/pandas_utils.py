import pandas as pd
import json

def convert_excel_to_json(table):
    results = table.to_dict('records')
    return results