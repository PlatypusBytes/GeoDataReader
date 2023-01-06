from BroReader import read_BRO
import pickle
from datetime import date

if __name__ == "__main__":
    location = [117769, 439304]
    radius_distance = 1
    start_date = date(2015, 1, 1)
    c = read_BRO.read_cpts(location, radius_distance, output_dir="cpts")
    # open a file, where you ant to store the data
    file = open('cpts/cpts', 'wb')
    # dump information to that file
    pickle.dump(c, file)
    file.close()
