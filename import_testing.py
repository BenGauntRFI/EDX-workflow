
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

img_fname = path + view_four_data['0']['Filename']
pts_fname = path + view_four_data['5']['Filename']


"""
streamy = BytesIO()
with open(pts_fname, 'br') as fn:
    streamy.write(fn.read())
streamy.seek(0)
fm_bytes = streamy.read(4)
print(fm_bytes)
print(calcsize('<I'))
file_magic_arr = unpack('<I', fm_bytes)
print(file_magic_arr)
file_magic = file_magic_arr[0]
print(file_magic)
print('reading PTS')


ff_bytes = streamy.read(8)
print(ff_bytes)

streamy.seek(164)
#more_hex = streamy.read(800)
#print(more_hex)

dict_of_hex = aggregate(streamy)
print(dict_of_hex)
"""



streamy = BytesIO()
with open(img_fname, 'br') as fn:
    streamy.write(fn.read())
streamy.seek(0)
file_magic = unpack('<I', streamy.read(4))[0]
print('reading IMG')

img_fileformat = streamy.read(32).rstrip(b'\x00').decode("utf-8")
header, header_len, data = unpack('<III', streamy.read(12))
print(header, header_len, data)
streamy.seek(header)
print(streamy.read(12))
header = aggregate(streamy)
streamy.seek(data)
print(streamy.read(12))
metadata = aggregate(streamy)
s = metadata['Image']['Size']
metadata['Image']['Bits'].resize((s[1], s[0]))
image_array = metadata['Image']['Bits']

print(header)


