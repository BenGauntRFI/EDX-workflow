#Code copied from HussariX on github

from struct import unpack, calcsize
from io import BytesIO
import os
from datetime import datetime, timedelta

from PyQt5 import QtCore, QtGui
from PyQt5.Qt import QImage, QIcon, QPixmap
from PyQt5.QtCore import QRectF
from pyqtgraph import ImageItem

import numpy as np
import pyqtgraph as pg



# Jeol types (type abbrevations used in python struct):
jTYPE = {1: 'B', 2: 'H', 3: 'i', 4: 'f',
         5: 'd', 6: 'B', 7: 'H', 8: 'i',
         9: 'f', 10: 'd', 11: 's', 12: 's'}
# val 0 means it is dict
# jval jType 11, is most probably boolean... weird it is in between arrays...




class Image:
    """requires that parser would
    initialize self.image_array"""

    def gen_icon(self):
        qimage = QImage(self.image_array,
                        self.image_array.shape[1],
                        self.image_array.shape[0],
                        QImage.Format_Grayscale8)
        self.icon = QIcon(QPixmap(qimage))

    def gen_image_item(self, height, width):
        self.pg_image_item = ImageItem(self.image_array)
        self.pg_image_item.setRect(QRectF(0, height, width, -height))



default_pen = pg.mkPen((255, 255, 75), width=2)
default_hover_pen = pg.mkPen((255, 50, 50), width=2)
default_select_pen = pg.mkPen((255, 255, 255), width=2)

HIGHLIGHT_PEN = pg.mkPen('r', width=2)
HIGHLIGHT_BRUSH = pg.mkBrush((255, 255, 75, 50))
SELECT_BRUSH = pg.mkBrush((255, 255, 75))
NO_BRUSH = pg.mkBrush(None)


class Spectra:
    # required attributes:
    # self.x_offset, self.data, self.x_res
    # produces:
    # self.marker, self.x_scale,
    def __init__(self):
        self.selected = False

    def gen_scale(self):
        max_channel = self.x_res * self.chnl_cnt + self.x_offset
        self.x_scale = np.arange(self.x_offset, max_channel, self.x_res)

    def channel_at_e(self, energy):
        return int((energy - self.x_offset) // self.x_res)

    def e_at_channel(self, channel):
        return channel * self.res + self.x_offset

    def gen_pg_curve(self, starting_pos=0.02, cutoff=15.):
        st_chan = self.channel_at_e(starting_pos)
        if (st_chan < min(self.x_scale)) or (st_chan > max(self.x_scale)):
            st_chan = 0
        end_chan = self.channel_at_e(cutoff)
        if (end_chan < min(self.x_scale)) or (end_chan > max(self.x_scale)):
            end_chan = -1
        self.pg_curve = pg.PlotDataItem(self.x_scale[st_chan:end_chan],
                                        self.data[st_chan:end_chan],
                                        pen=pg.mkPen(255, 255, 125),
                                        fillLevel=0,  # prepare to be filled
                                        fillBrush=pg.mkBrush(None))  # but fill not

    def gen_marker(self, *args, marker_type=None):
        if marker_type == 'translated_marker':
            self.marker = selectablePoint(self, *args)
        elif marker_type == 'rectangle':
            self.marker = selectableRectangle(self, *args)
        elif marker_type == 'ellipse':
            self.marker = selectableEllipse(self, *args)
        elif marker_type == 'free_polygon':
            self.marker = selectablePolygon(self, *args)

    def highlight_spectra(self):
        self.original_pen = self.pg_curve.opts['pen']
        self.pg_curve.setPen(HIGHLIGHT_PEN)
        if not self.selected:
            self.pg_curve.setBrush(HIGHLIGHT_BRUSH)

    def unlight_spectra(self):
        self.pg_curve.setPen(self.original_pen)
        if not self.selected:
            self.pg_curve.setBrush(NO_BRUSH)

    def select_spectra(self):
        if self.selected:
            self.pg_curve.setBrush(NO_BRUSH)
            self.selected = False
        else:
            self.pg_curve.setBrush(SELECT_BRUSH)
            self.selected = True

    def set_curve_color(self, *colors):
        pass

    def change_marker_color(self, color):
        pass



class selectableMarker:

    # sigClicked = QtCore.Signal(object)
    # sigHovered = QtCore.Signal()
    # sigLeft = QtCore.Signal()

    def __init__(self, data, *args, pen=default_pen):
        self.setAcceptHoverEvents(True)
        self.internal_pointer = data
        self.setPen(pen)
        self.original_pen = pen
        self.savedPen = pen
        self.selected = False

    def hoverEnterEvent(self, ev):
        if not self.selected:
            self.savedPen = self.pen()
        self.setPen(default_hover_pen)
        # self.sigHovered.emit()
        self.internal_pointer.highlight_spectra()
        ev.accept()

    def hoverLeaveEvent(self, ev):
        if self.selected:
            self.setPen(default_select_pen)
        else:
            self.setPen(self.savedPen)
        self.internal_pointer.unlight_spectra()
        # self.sigLeft.emit()
        ev.accept()

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            # self.sigClicked.emit(self.internal_pointer)
            if self.selected:
                self.selected = False
            else:
                self.selected = True
                self.setPen(default_select_pen)
                self.internal_pointer.select_spectra()

            ev.accept()
        else:
            ev.ignore()





class selectablePolygon(selectableMarker, QtGui.QGraphicsPolygonItem):
    """requires object for reference and QPolygonF"""

    def __init__(self, data, *args):
        QtGui.QGraphicsPolygonItem.__init__(self, *args)
        selectableMarker.__init__(self, data, *args)


class selectableRectangle(selectableMarker, QtGui.QGraphicsRectItem):
    """requires object for reference and 4 points of bounding Rectangle:
     (left_top: x, y, width, height)"""

    def __init__(self, data, *args):
        self.geometry = QtCore.QRectF(*args)
        QtGui.QGraphicsRectItem.__init__(self, *args)
        selectableMarker.__init__(self, data, *args)

    def boundingRect(self):
        return self.geometry

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRect(self.boundingRect())
        return path


class selectableEllipse(selectableMarker, QtGui.QGraphicsEllipseItem):
    """requires object for reference and 4 points of bounding Rectangle:
     (left_top: x, y, width, height)"""

    def __init__(self, data, *args):
        self.geometry = QtCore.QRectF(*args)
        QtGui.QGraphicsEllipseItem.__init__(self, *args)
        selectableMarker.__init__(self, data, *args)

    def boundingRect(self):
        return self.geometry

    def shape(self):
        path = QtGui.QPainterPath()
        path.addEllipse(self.boundingRect())
        return path


class selectablePoint(selectableMarker, QtGui.QGraphicsPathItem):
    # class selectablePoint(QtGui.QGraphicsPathItem):
    """requires object for reference and path item (the symbol):
     and QtGui.QPainterPath"""

    def __init__(self, data, *args):
        self.geometry = args[0]
        QtGui.QGraphicsPathItem.__init__(self, *args)
        selectableMarker.__init__(self, data, *args)

    def boundingRect(self):
        return self.geometry.boundingRect()

    def shape(self):
        path = QtGui.QPainterPath()
        path.addEllipse(self.boundingRect())
        return path


#All functions/classes above here were orininally imported from separate packages


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
        self.make_image_items()
        self.make_eds_interactive()

    def make_image_items(self):
        for i in self.image_list:
            i.gen_image_item(self.height, self.width)

    def make_eds_interactive(self):
        for i in self.eds_list:
            i.make_marker()
            i.gen_pg_curve()

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

    def create_point_marker(self, scale_down=16):
        """create point marker (cross marke with
        open middle part).
        Parameters:
        scale_down -- (default=16) parameter which
        controls marker size. the value is the fraction of
        image height.
        """
        self.point_marker = QtGui.QPainterPath()
        coords = np.asarray([[[-0.5, 0], [-0.1, 0]],
                             [[0, 0.5], [0, 0.1]],
                             [[0, -0.5], [0, -0.1]],
                             [[0.5, 0], [0.1, 0]]])
        scale = self.height / scale_down
        coords *= scale
        for i in coords:
            self.point_marker.moveTo(*i[0])
            self.point_marker.lineTo(*i[1])

    def set_default_image(self, index=-1):
        self.def_image = self.image_list[index]

    def __repr__(self):
        return 'JeolSampleView, title: {}'.format(self.memo)


class JeolImage(Image):
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
        self.gen_icon()


class JeolEDS(Spectra):
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
        self.gen_scale()
        spectra.Spectra.__init__(self)

    def make_marker(self):
        # for jeol format the marker is produced in Jeol spectra class
        # in meters:
        posx = self.parent.width / 2 - self.positionmm2[0] / 1000
        posy = self.parent.height / 2 - self.positionmm2[3] / 1000
        if self.positionmm2[0] == self.positionmm2[2]:  # point
            if self.parent.point_marker is None:
                self.parent.create_point_marker()
            path = self.parent.point_marker.translated(posx, posy)
            self.gen_marker(path, marker_type='translated_marker')
        else:  # rect
            lenth = (self.positionmm2[0] - self.positionmm2[2]) / 1000
            height = (self.positionmm2[3] - self.positionmm2[1]) / 1000
            self.gen_marker(posx, posy, lenth, height, marker_type='rectangle')


class JeolThingy:
    def __init__(self, dictionary, parent):
        self.parent = parent
        for key in dictionary:
            setattr(self, key.lower(), dictionary[key])
        self.filename = os.path.join(self.parent.parent.parent.proj_dir,
                                     self.filename)
        with open(self.filename, 'rt') as fn:
            self.text_junk = fn.read()


class JeolSampleViewListModel(QtCore.QAbstractListModel):
    def __init__(self, jeol_sample, parent=None):
        QtCore.QAbstractListModel.__init__(self, parent)
        self.sample = jeol_sample

    def rowCount(self, parent):
        try:
            return len(self.sample.views)
        except AttributeError:   # empty sample container
            return 0

    def data(self, index, role):
        if role == QtCore.Qt.ToolTipRole:
            item = self.sample.views[index.row()]
            tooltip = """Mag: ✕{}
WD: {:.2f}
HV: {:.2f}
N of EDS: {}
N of IMG: {}""".format(item.mag, item.workd, item.volt, len(item.eds_list),
                       len(item.image_list))
            return tooltip

        if role == QtCore.Qt.UserRole:
            return self.sample.views[index.row()]

        if role == QtCore.Qt.DecorationRole:

            row = index.row()
            def_img = self.sample.views[row].def_image
            return def_img.icon

        if role == QtCore.Qt.DisplayRole:
            return self.sample.views[index.row()].memo

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable