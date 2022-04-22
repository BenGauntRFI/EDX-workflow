
from jeol_reader import *

path = "data/2022-03-03/20220301_test/"

project = JeolProject(path + "20220301_test.ASW")
datadict = get_data_dict(path + "20220301_test.ASW")
print(datadict.keys())

sample_info = datadict['SampleInfo']
print(sample_info.keys())

sample_zero = sample_info['0']
print(sample_zero.keys())

view_info = sample_zero['ViewInfo']
print(view_info.keys())

view_four = view_info['4']
print(view_four.keys())

view_four_data = view_four['ViewData']
print(view_four_data.keys())

intkeys = [int(key) for key in view_four_data.keys()]
intkeys.sort()
for intkey in intkeys:
    data_i = view_four_data[str(intkey)]
    print(str(intkey), data_i['Keyword'], data_i['Filename'])

pts_fname = path + view_four_data['5']['Filename']

with open(pts_fname, 'br') as fn:
    text_junk = fn.read()

print(text_junk)
