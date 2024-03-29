""" Finds and converts measurements in the Nanomine knowledge graph."""

import pkg_resources
import warnings
from contextlib import closing
from io import StringIO
from numbers import Real
import os

from .convert_values import convert_to_other_units, load_user_definitions
from .read_dictionary import read_dictionary
from .kg_parser import *

# dictionaries for conversion between units
unit_type_dict = {}
translations = {}
resource_package = __name__

directory = os.fsencode(pkg_resources.resource_filename(resource_package, "dicts"))
for f in os.listdir(directory):
    file_name = "dicts/" + os.fsdecode(f)
    new_dict, f_type = read_dictionary(file_name)
    if f_type == "translation_file":
        translations.update(new_dict)
    elif f_type == "mapping_file":
        unit_type_dict.update(new_dict)
    elif f_type == "definitions_file":
        try:
            with closing(pkg_resources.resource_stream(__name__, file_name)) as f:
                rbytes = f.read()
                load_user_definitions(StringIO(rbytes.decode('utf-8')))
        except Exception as e:
            msg = getattr(e, 'message', '') or str(e)
            raise ValueError("While opening {}\n{}".format(f, msg))

def convert_attr_to_units(attr):
    """ Calculate unit conversions if passed a convertible attribute."""
    # get all preferred units that have not yet been derived from this attribute
    to_units_URIs = attr_incomplete_preferred_units(attr)
    if not to_units_URIs:
        return None
    # pull important values off attribute
    meas_type = attr_type_URI(attr)
    unit_URI = attr_unit(attr)
    meas_value = attr_value(attr)
    if (not (meas_type
             and unit_URI
             and meas_value
             and isinstance(meas_value, Real))):
        return None

    if not to_units_URIs:
        # get unit names from user-supplied dictionary if it exists
        if unit_type_dict:
            try:
                to_units_URIs = [un for un in unit_type_dict[str(meas_type)]]
            except KeyError:
                warnings.warn("The unit type URI {} has not been translated. See README.md for instructions on how to translate unit types for the Whyis Unit Converter.".format(str(meas_type)))
        # if there are no preferred units, don't convert
        else:
            return None

    # translate to pint-friendly unit names
    to_units = []
    for uri in to_units_URIs:
        if str(uri) in translations:
            to_units.append(translations[str(uri)][0])
        else:
            warnings.warn("The unit URI {} has not been translated. See README.md for instructions on how to translate units for the Whyis Unit Converter.".format(str(uri)))

    # if no units could be translated, don't convert
    if not to_units:
        return None

    # translate measurement unit to pint-friendly name
    if str(unit_URI) in translations:
        meas_unit = translations[str(unit_URI)][0]
    else:
        # if measurement unit couldn't be translated
        warnings.warn("The unit URI {} has not been translated. See README.md for instructions on how to translate units for the Whyis Unit Converter.".format(str(unit_URI)))
        return None

    # do all unit conversion, return list of attributes
    converted_meas_tuples = convert_to_other_units(meas_unit, meas_value, to_units)
    converted = []
    converted_tuples = zip(to_units_URIs, converted_meas_tuples)
    for new_unit, (pint_unit, new_val) in converted_tuples:
        # if the conversion returned everything it was supposed to
        if new_unit and new_val and pint_unit:
            converted.append(measurement_attribute(new_unit, new_val, meas_type, attr.identifier))
    return converted
