from datetime import datetime
from typing import Dict, Any

from betterproto.lib.google.protobuf import Struct, Value, NullValue, ListValue


def struct_from_dict(d: Dict[str, Any]) -> "Struct":

    def create_value(value) -> "Value":
        new_value: "Value" = Value(null_value=NullValue(0))
        if isinstance(value, str):
            new_value = Value(string_value=value)
        elif isinstance(value, int) or isinstance(value, float):
            new_value = Value(number_value=float(value))
        elif isinstance(value, bool):
            new_value = Value(bool_value=value)
        elif isinstance(value, datetime):
            new_value = Value(string_value=value.isoformat())
        elif isinstance(value, dict) and len(value.keys()) != 0 and isinstance(list(set(value.keys()))[0], str):
            struct = struct_from_dict(value)
            new_value = Value(struct_value=struct)
        elif isinstance(value, list):
            list_value = list(map(lambda x: create_value(x), value))
            new_value = Value(list_value=ListValue(values=list_value))
        return new_value

    ret = {}
    for key in d:
        ret[key] = create_value(d[key])
    return Struct(fields=ret)
