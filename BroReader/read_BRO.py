import json
import requests
import pyproj
from pyproj import Transformer
from xml.etree import ElementTree
from lxml import etree
from datetime import date
import logging
from io import StringIO
import numpy as np
import pandas as pd
from xml.dom import minidom

from geolib_plus.bro_xml_cpt import BroXmlCpt
from pathlib import Path
from geolib_plus.robertson_cpt_interpretation import RobertsonCptInterpretation
from geolib_plus.robertson_cpt_interpretation import UnitWeightMethod
from geolib_plus.robertson_cpt_interpretation import OCRMethod
from geolib_plus.robertson_cpt_interpretation import ShearWaveVelocityMethod

ns = "{http://www.broservices.nl/xsd/cptcommon/1.1}"
ns2 = "{http://www.broservices.nl/xsd/dscpt/1.1}"
ns3 = "{http://www.opengis.net/gml/3.2}"
ns4 = "{http://www.broservices.nl/xsd/brocommon/3.0}"
ns5 = "{http://www.opengis.net/om/2.0}"

nodata = -999999
to_epsg = "28992"
to_srs = pyproj.Proj(init='epsg:{}'.format(to_epsg))

columns = ["penetrationLength", "depth", "elapsedTime", "coneResistance", "correctedConeResistance",
           "netConeResistance", "magneticFieldStrengthX", "magneticFieldStrengthY", "magneticFieldStrengthZ",
           "magneticFieldStrengthTotal", "electricalConductivity",
           "inclinationEW", "inclinationNS", "inclinationX", "inclinationY", "inclinationResultant",
           "magneticInclination", "magneticDeclination", "localFriction", "poreRatio", "temperature", "porePressureU1",
           "porePressureU2", "porePressureU3", "frictionRatio"]
req_columns = ["penetrationLength", "coneResistance", "localFriction", "frictionRatio"]


def convert_lat_long_to_rd(x, y):
    """
    Converts RD coordinates to latitude and longitude
    :param x:
    :param y:
    :return: latitude, longitude
    """

    transformer = Transformer.from_crs("epsg:28992", "epsg:4326")
    lat, long = transformer.transform(x, y)

    return lat, long


def parse_xml_location(tdata):
    """Return x y of location.
    TODO Don't user iter
    :param tdata: XML bytes
    :returns: list -- of x y string coordinates

    Will transform coordinates not in EPSG:28992
    """
    root = etree.fromstring(tdata)
    crs = None

    for loc in root.iter(ns2 + "deliveredLocation"):
        for point in loc.iter(ns3 + "Point"):
            srs = point.get("srsName")
            if srs is not None and "EPSG" in srs:
                crs = srs.split("::")[-1]
            break
        for pos in loc.iter(ns3 + "pos"):
            x, y = map(float, pos.text.split(" "))
            break

    if crs is not None and crs != to_epsg:
        # logging.warning("Reprojecting from epsg::{}".format(crs))
        source_srs = pyproj.Proj('+init=epsg:{}'.format(crs))
        x, y = pyproj.transform(source_srs, to_srs, y, x)

    return x, y


def parse_bro_xml(xml):
    """Parse bro CPT xml.
    Searches for the cpt data, but also
    - location
    - offset z
    - id
    - predrilled_z
    TODO Replace iter by single search
    as iter can give multiple results

    :param xml: XML bytes
    :returns: dict -- parsed CPT data + metadata
    """
    root = etree.fromstring(xml)

    # Initialize data dictionary
    data = {"id": None, "location_x": None, "location_y": None,
            "offset_z": None, "predrilled_z": None, "a": 0.80,
            "vertical_datum": None, "local_reference": None,
            "quality_class": None, "cone_penetrometer_type": None,
            "cpt_standard": None}  # 'result_time': None}

    # Location
    x, y = parse_xml_location(xml)
    data["location_x"] = float(x)
    data["location_y"] = float(y)

    # BRO Id
    for loc in root.iter(ns4 + "broId"):
        data["id"] = loc.text

    # Norm of the cpt
    for loc in root.iter(ns2 + "cptStandard"):
        data["cpt_standard"] = loc.text

    # Offset to reference point
    for loc in root.iter(ns + "offset"):
        z = loc.text
        data["offset_z"] = float(z)

    # Local reference point
    for loc in root.iter(ns + "localVerticalReferencePoint"):
        data["local_reference"] = loc.text

    # Vertical datum
    for loc in root.iter(ns + "verticalDatum"):
        data["vertical_datum"] = loc.text

    # cpt class
    for loc in root.iter(ns + "qualityClass"):
        data["quality_class"] = loc.text

    # cpt type and serial number
    for loc in root.iter(ns + "conePenetrometerType"):
        data["cone_penetrometer_type"] = loc.text

    # # cpt time of result
    # for cpt in root.iter(ns + "conePenetrationTest"):
    #     for loc in cpt.iter(ns5 + "resultTime"):
    #         data["result_time"] = loc.text

    # Pre drilled depth
    for loc in root.iter(ns + "predrilledDepth"):
        z = loc.text
        # if predrill does not exist it is zero
        if not z:
            z = 0.
        data["predrilled_z"] = float(z)

    # Cone coefficient - a
    for loc in root.iter(ns + "coneSurfaceQuotient"):
        a = loc.text
        data["a"] = float(a)

    # Find which columns are not empty
    avail_columns = []
    for parameters in root.iter(ns + "parameters"):
        for parameter in parameters:
            if parameter.text == "ja":
                avail_columns.append(parameter.tag[len(ns):])

    # Determine if all data is available
    meta_usable = all([x is not None for x in data.values()])
    data_usable = all([col in avail_columns for col in req_columns])
    if not (meta_usable and data_usable):
        logging.warning("CPT with id {} misses required data.".format(data["id"]))
        return None

    # Parse data array, replace nodata, filter and sort
    for cpt in root.iter(ns + "conePenetrationTest"):
        for element in cpt.iter(ns + "values"):
            # Load string data and parse as 2d array
            sar = StringIO(element.text.replace(";", "\n"))
            ar = np.loadtxt(sar, delimiter=",", ndmin=2)

            # Check shape of array
            found_rows, found_columns = ar.shape
            if found_columns != len(columns):
                logging.warning("Data has the wrong size! {} columns instead of {}".format(found_columns, len(columns)))
                return None

            # Replace nodata constant with nan
            # Create a DataFrame from array
            # and sort by depth
            ar[ar == nodata] = np.nan
            df = pd.DataFrame(ar, columns=columns)
            df = df[avail_columns]
            df.sort_values(by=['penetrationLength'], inplace=True)

        data["dataframe"] = df

    return data


def read_cpts(coordinate, radius, start_date=date(2015, 1, 1)):
    # latitude, longitude = convert_lat_long_to_rd(150010, 449999)
    latitude, longitude = convert_lat_long_to_rd(float(coordinate[0]), float(coordinate[1]))
    radius = radius  # km
    start_date = start_date
    end_date = date.today()

    Schemas = {
        "registrationPeriod": {
            "beginDate": str(start_date),
            "endDate": str(end_date)
        },
        "area": {
            "enclosingCircle": {
                "center": {
                    "lat": latitude,
                    "lon": longitude
                },
                "radius": radius
            }
        }
    }

    headers = {'accept': 'application/xml',
               'content-type': 'application/json'}

    a = requests.post("https://publiek.broservices.nl/sr/cpt/v1/characteristics/searches", data=json.dumps(Schemas),
                      headers=headers)
    # print(a.status_code)
    # print(a.content)

    # collect all BRO-ID
    root = ElementTree.fromstring(a.content)

    # read CPT IC
    cpt_ID = []
    default = '{http://www.broservices.nl/xsd/brocommon/3.0}'
    cpt_ID.extend(
        child.text for child in root.iter() if child.tag == f'{default}broId'
    )

    print(f"CPTS available: {len(cpt_ID)}")
    cpts = []
    for c in cpt_ID:
        # print(f"{i} of {len(cpt_ID)}")
        cpt = requests.get(f"https://publiek.broservices.nl/sr/cpt/v1/objects/{c}")
        try:
            xml = minidom.parseString(cpt.content)
        except:
            continue
        xml.writexml(open(c + ".xml", 'w'),
                     indent="  ",
                     addindent="  ",
                     newl='\n',
                     encoding='UTF-8',
                     standalone="yes")

        xml.unlink()
        print(f"Wrote {c}.xml")
        try:
            cpt_file_xml = Path(f"{c}.xml")
            cpt_xml = BroXmlCpt()
            cpt_xml.read(cpt_file_xml)
            if cpt_xml.coordinates == None:
                continue
            cpt_xml.pre_process_data()

            # do pre-processing
            interpreter = RobertsonCptInterpretation()
            interpreter.unitweightmethod = UnitWeightMethod.LENGKEEK
            interpreter.shearwavevelocitymethod = ShearWaveVelocityMethod.ZANG
            interpreter.ocrmethod = OCRMethod.MAYNE
            cpt_xml.interpret_cpt(interpreter)
            cpts.append(dict(cpt_xml))
            out_file = open(f"{c}.json", "w")
            cpt_dict = dict(cpt_xml)
            for k, v in cpt_dict.items():
                if "array" in str(type(v)):
                    cpt_dict[k] = v.tolist()
                if "numpy.float32" in str(type(v)) or "numpy.float64" in str(type(v)):
                    cpt_dict[k] = float(v)
            cpt_dict.pop("plot_settings")
            json.dump(cpt_dict, out_file, indent=2)
        except ValueError:
            print(f"{c} is not readable")
        except UnboundLocalError:
            print(f"{c} is not readable")
    return cpts
