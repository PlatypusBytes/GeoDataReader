import pickle
import shutil
import numpy as np
from datetime import date
from geodatareader.BroReader import read_BRO


TOL = 1e-3

def test_len_cpts():
    location = [117769, 439304]
    radius_distance = 0.2
    cpts = read_BRO.read_cpts(location, radius_distance, output_dir="cpts", interpret_cpt=True)
    shutil.rmtree("cpts")
    assert len(cpts) == 4

    radius_distance = 0.4
    cpts = read_BRO.read_cpts(location, radius_distance, output_dir="cpts", interpret_cpt=True)
    shutil.rmtree("cpts")
    assert len(cpts) == 35

    radius_distance = 0.4
    start_date = date(2018, 1, 1)
    cpts = read_BRO.read_cpts(location, radius_distance, start_date=start_date,output_dir="cpts", interpret_cpt=True)
    shutil.rmtree("cpts")
    assert len(cpts) == 10


def test_read_cpts():
    location = [117776, 439124]
    radius_distance = 0.02
    cpts = read_BRO.read_cpts(location, radius_distance, output_dir="cpts", interpret_cpt=True)
    shutil.rmtree("cpts")
    data = cpts[0]

    # load
    with open("./unit_test/data/CPT000000057519.pickle", "rb") as fo:
        data_exact = pickle.load(fo)

    assert compare_dictionaries(data, data_exact)


def compare_dictionaries(dic1, dic2):

    skip_keys = ["E_NEN", "cohesion_NEN", "fr_angle_NEN", "plot_settings"]

    for key in dic1.keys():
        if key in skip_keys:
            continue
        if key not in dic2.keys():
            return False
        else:
            if isinstance(dic1[key], dict):
                if not compare_dictionaries(dic1[key], dic2[key]):
                    return False
            elif isinstance(dic1[key], list):
                for i, k in enumerate(dic1[key]):
                    if k != dic2[key][i]:
                        return False
            elif  isinstance(dic1[key], np.ndarray):
                if (np.abs(dic1[key] - dic2[key]) > TOL).any():
                    return False
            else:
                if dic1[key] != dic2[key]:
                    return False
    return True
