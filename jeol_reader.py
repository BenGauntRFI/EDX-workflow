#Code copied from HussariX on github

from struct import unpack, calcsize
from io import BytesIO
import os
from datetime import datetime, timedelta

import numpy as np



# Jeol types (type abbrevations used in python struct):
jTYPE = {1: 'B', 2: 'H', 3: 'i', 4: 'f',
         5: 'd', 6: 'B', 7: 'H', 8: 'i',
         9: 'f', 10: 'd', 11: 's', 12: 's'}
# val 0 means it is dict
# jval jType 11, is most probably boolean... weird it is in between arrays...



def aggregate(stream_obj):
    final_dict = {}
    mark = unpack('b', stream_obj.read(1))[0]
    while mark == 1:
        final_dict.update(read_attrib(stream_obj))
        mark = unpack('b', stream_obj.read(1))[0]

    return final_dict


def read_attrib(stream_obj):
    str_len = unpack('<i', stream_obj.read(4))[0]
    kwrd, val_type, val_len = unpack('<{}sii'.format(str_len),
                                     stream_obj.read(str_len+8))
    kwrd = kwrd[:-1].decode("utf-8")
    if val_type <= 5 and val_type != 0:
        value = unpack('<{}'.format(jTYPE[val_type]),
                       stream_obj.read(val_len))[0]
        if kwrd == 'Created':
            value = mstimestamp_to_datetime(value)
        mark = unpack('b', stream_obj.read(1))[0]
    elif val_type > 5:
        try:
            c_type = jTYPE[val_type]
        except:
            print('address', stream_obj.tell())
            raise KeyError

        arr_len = val_len // calcsize(c_type)
        if (arr_len <= 256) or (c_type == 's'):
            value = unpack('<{0}{1}'.format(arr_len, c_type),
                           stream_obj.read(val_len))
        else:
            value = np.fromstring(stream_obj.read(val_len),
                                  dtype=c_type)
        if c_type == 's':
            value = value[0][:-1].decode("utf-8")
        if kwrd == 'Filename':
            # this way works on ms_win and *nix:
            value = value.replace('\\', '/')
            value = os.path.normpath(value)
        mark = unpack('b', stream_obj.read(1))[0]
    elif val_type == 0:
        value = aggregate(stream_obj)
        mark = -1
    if mark == -1:
        return {kwrd: value}


def filetime_to_datetime(filetime):
    """Return recalculated windows filetime to unix time."""
    return datetime(1601, 1, 1) + timedelta(microseconds=filetime / 10)


def mstimestamp_to_datetime(msstamp):
    """Return recalculated windows timestamp to unix time."""
    return datetime(1899, 12, 31) + timedelta(days=msstamp)

def get_data_dict(filename):
    """Temporary function to store the metadata in the .asw file so I can look through it"""
    ram_stream = BytesIO()
    with open(filename, 'br') as fn:
        ram_stream.write(fn.read())
    # skipp leading zeros 12 bytes:
    ram_stream.seek(12)
    data = aggregate(ram_stream)

    return data


class JeolProject:
    def __init__(self, filename):
        ram_stream = BytesIO()
        self.proj_dir = os.path.dirname(filename)
        with open(filename, 'br') as fn:
            ram_stream.write(fn.read())
        # skipp leading zeros 12 bytes:
        ram_stream.seek(12)
        data = aggregate(ram_stream)
        self.version = data['Version']
        self.file_type = data['FileType']
        self.memo = data['Memo']
        self.samples = [JeolSample(i, data['SampleInfo'][i], self)
                        for i in data['SampleInfo']]


class JeolSample:
    def __init__(self, name, dictionary, parent):
        self.parent = parent
        self.name = name
        for key in dictionary:
            if key != 'ViewInfo':
                setattr(self, key.lower(), dictionary[key])
            else:
                _list = [int(i) for i in dictionary['ViewInfo']]
                _list.sort()
                self.views = [JeolSampleView(dictionary['ViewInfo'][str(view)],
                                             self) for view in _list]

    def __repr__(self):
        return 'JeolSample {}; title: {}'.format(self.name, self.memo)


class JeolSampleView:
    def __init__(self, dictionary, parent):
        self.parent = parent
        self.point_marker = None
        self.eds_list = []
        self.image_list = []
        self.etc_list = []
        for key in dictionary:
            if key != 'ViewData':
                setattr(self, key.lower(), dictionary[key])
            else:
                _list = [int(i) for i in dictionary['ViewData']]
                _list.sort()
                for view in _list:
                    self.classify_item(dictionary['ViewData'][str(view)])
        self.make_hw()
        self.set_default_image()

    def classify_item(self, item):
        if 'IMG' in item['Keyword']:
            self.image_list.append(JeolImage(item, self))
        elif 'ETC' in item['Keyword']:
            self.etc_list.append(JeolThingy(item, self))
        elif 'EDS' in item['Keyword']:
            self.eds_list.append(JeolEDS(item, self))

    def make_hw(self):
        """calculate height and width in m"""
        self.height = self.positionmm2[3] / 1000
        self.width = -self.positionmm2[2] / 1000

    def set_default_image(self, index=-1):
        self.def_image = self.image_list[index]

    def __repr__(self):
        return 'JeolSampleView, title: {}'.format(self.memo)


class JeolImage:
    def __init__(self, dictionary, parent):
        self.parent = parent
        for key in dictionary:
            setattr(self, key.lower(), dictionary[key])
        streamy = BytesIO()
        self.filename = os.path.join(self.parent.parent.parent.proj_dir,
                                     self.filename)
        with open(self.filename, 'br') as fn:
            streamy.write(fn.read())
        streamy.seek(0)
        file_magic = unpack('<I', streamy.read(4))[0]
        print('reading Image', self.filename)
        if file_magic != 52:
            raise IOError(
                'Jeol image file {} have not expected magic number {}'.format(
                    self.filename, file_magic))
        self.fileformat = streamy.read(32).rstrip(b'\x00').decode("utf-8")
        header, header_len, data = unpack('<III', streamy.read(12))
        streamy.seek(header+12)
        self.header = aggregate(streamy)
        streamy.seek(data+12)
        self.metadata = aggregate(streamy)
        s = self.metadata['Image']['Size']
        self.metadata['Image']['Bits'].resize((s[1], s[0]))
        self.image_array = self.metadata['Image']['Bits']


class JeolEDS:
    def __init__(self, dictionary, parent):
        self.spectra_type = 'eds'
        self.parent = parent
        for key in dictionary:
            setattr(self, key.lower(), dictionary[key])
        self.filename = os.path.join(self.parent.parent.parent.proj_dir,
                                     self.filename)
        with open(self.filename, 'br') as fn:
            fn.seek(0x102)
            self.live_time, self.real_time = unpack('<2d', fn.read(16))
            fn.seek(0x16A)
            self.x_res, self.x_offset = unpack('<2d', fn.read(16))
            fn.seek(454)
            array_size = unpack('<I', fn.read(4))[0]
            self.data = np.fromstring(fn.read(array_size*4), dtype=np.uint32)
            self.chnl_cnt = array_size

class JeolPts:
    def __init__(self, dictionary, parent):
        self.spectra_type = 'eds'
        self.parent = parent
        for key in dictionary:
            setattr(self, key.lower(), dictionary[key])
        self.filename = os.path.join(self.parent.parent.parent.proj_dir,
                                     self.filename)
        with open(self.filename, 'br') as fn:
            fn.seek(0x102)



class JeolThingy:
    def __init__(self, dictionary, parent):
        self.parent = parent
        for key in dictionary:
            setattr(self, key.lower(), dictionary[key])
        self.filename = os.path.join(self.parent.parent.parent.proj_dir,
                                     self.filename)
        with open(self.filename, 'rt') as fn:
            self.text_junk = fn.read()

