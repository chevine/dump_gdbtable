#!/usr/bin/env python
# -*- coding: utf-8 -*-
###############################################################################
# $Id$
#
# Project:  GDAL/OGR
# Purpose:  Dump FileGDB .gdbtable content
# Author:   Even Rouault <even dot rouault at mines dash paris dot org>
#
###############################################################################
# Copyright (c) 2013, Even Rouault <even dot rouault at mines dash paris dot org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

# WARNING: proof-of-concept code of the https://github.com/rouault/dump_gdbtable/wiki/FGDB-Spec
# not production ready, not all cases handled, etc...

import struct
import sys

if len(sys.argv) != 2:
    print('Usage: dump_gdbtable.py some_file.gdbtable')
    sys.exit(1)

filename = sys.argv[1]

def read_uint8(f):
    return ord(f.read(1))

def read_int16(f):
    v = f.read(2)
    return struct.unpack('h', v)[0]

def read_int32(f):
    v = f.read(4)
    return struct.unpack('i', v)[0]

def read_float32(f):
    v = f.read(4)
    return struct.unpack('f', v)[0]

def read_float64(f):
    v = f.read(8)
    return struct.unpack('d', v)[0]

def read_uint32(f):
    v = f.read(4)
    return struct.unpack('I', v)[0]

def read_uint40(f):
    v_low = read_uint8(f)
    v_high = read_uint32(f)
    return v_low | (v_high << 8)

def read_uint48(f):
    v_low = read_uint8(f)
    v_high = read_uint40(f)
    return v_low | (v_high << 8)

def read_varint(f):

    b = read_uint8(f)
    ret = (b & 0x3F)
    sign = 1
    if (b & 0x40) != 0:
        sign = -1
    if (b & 0x80) == 0:
        return sign * ret
    shift = 6

    while True:
        b = read_uint8(f)
        ret = ret | ((b & 0x7F) << shift)
        if (b & 0x80) == 0:
            break
        shift = shift + 7
    return sign * ret

def read_varuint(f):
    shift = 0
    ret = 0
    while True:
        b = read_uint8(f)
        ret = ret | ((b & 0x7F) << shift)
        if (b & 0x80) == 0:
            break
        shift = shift + 7
    return ret

def read_bbox(f):
    vi = read_varuint(f)
    minx = vi / xyscale + xorig
    print('minx = %.15f' % minx)
    vi = read_varuint(f)
    miny = vi / xyscale + yorig
    print('miny = %.15f' % miny)
    vi = read_varuint(f)
    maxx = minx + vi / xyscale
    print('maxx = %.15f' % maxx)
    vi = read_varuint(f)
    maxy = miny + vi / xyscale
    print('maxy = %.15f' % maxy)

def read_tab_nbpoints(f, nb_geoms, nb_total_points):
    nb_acc = 0
    tab_nb_points = []
    for i_part in range(nb_geoms - 1):
        nb_points = read_varuint(f)
        nb_acc = nb_acc + nb_points
        print("nb_points[%d] = %d" % (i_part, nb_points))
        tab_nb_points.append(nb_points)
    tab_nb_points.append(nb_total_points - nb_acc)
    print("nb_points[%d] = %d" % (nb_geoms - 1, nb_total_points - nb_acc))
    return tab_nb_points

def read_tab_xy(f, nb_geoms, tab_nb_points):
    dx_int = dy_int = 0
    for i_part in range(nb_geoms):
        nb_points = tab_nb_points[i_part]
        for i_point in range(nb_points):

            vi = read_varint(f)
            dx_int = dx_int + vi
            x = dx_int / xyscale + xorig
            dy_int = dy_int + read_varint(f) 
            y = dy_int / xyscale + yorig
            if i_point < 10 or i_point > nb_points - 10:
                print("[%d] %.15f %.15f" % (i_point+1, x, y))

        print('')

def read_tab_z(f, nb_geoms, tab_nb_points):
    dz_int = 0
    for i_part in range(nb_geoms):
        nb_points = tab_nb_points[i_part]
        for i_point in range(nb_points):

            dz_int = dz_int + read_varint(f) 
            z = dz_int / zscale + zorig
            if i_point < 10 or i_point > nb_points - 10:
                print("[%d] z=%.15f" % (i_point+1,  z))

        print('')

def read_tab_m(f, nb_geoms, tab_nb_points):

    # 0x42 seems to be a special value to indicate absence of m array !
    if read_uint8(f) == 0x42:
        return
    f.seek(-1, 1)

    for i_part in range(nb_geoms):
        nb_points = tab_nb_points[i_part]
        for i_point in range(nb_points):

            if i_point == 0 and i_part == 0:
                vi = read_varint(f)
                m0 = vi / mscale + morig
                dm_int = 0
                print("[%d] m=%.15f" % (i_point+1, m0))
            else:
                dm_int = dm_int + read_varint(f) 
                m = m0 + dm_int / mscale
                print("[%d] m=%.15f" % (i_point+1,  m))

        print('')

filenamex = filename[0:-1] + 'x'
fx = open(filenamex, 'rb')
fx.seek(4, 0)
n1024Blocks = read_uint32(fx)
print('n1024Blocks = %d' % n1024Blocks)
nfeaturesx = read_uint32(fx)
print('nfeaturesx = %d' % nfeaturesx)
if n1024Blocks == 0:
    assert nfeaturesx == 0
else:
    assert nfeaturesx >= 0
size_tablx_offsets = read_uint32(fx)
print('size_tablx_offsets = %d' % size_tablx_offsets)
assert size_tablx_offsets >= 4 and size_tablx_offsets <= 6

def TEST_BIT(ar, bit):
    return 1 if (ar[(bit) // 8] & (1 << ((bit) % 8))) else 0

def BIT_ARRAY_SIZE_IN_BYTES(bitsize):
    return (((bitsize)+7)//8)

pabyTablXBlockMap = None
if n1024Blocks != 0:
    fx.seek(size_tablx_offsets * 1024 * n1024Blocks + 16, 0)
    nMagic = read_uint32(fx)
    nBitsForBlockMap = read_uint32(fx)
    n1024BlocksBis = read_uint32(fx)
    assert n1024Blocks == n1024BlocksBis
    read_uint32(fx) # skip
    if nMagic == 0:
        assert nBitsForBlockMap == n1024Blocks
    else:
        assert nfeaturesx <= nBitsForBlockMap * 1024
        #Allocate a bit mask array for blocks of 1024 features.
        nSizeInBytes = BIT_ARRAY_SIZE_IN_BYTES(nBitsForBlockMap)
        pabyTablXBlockMap = fx.read(nSizeInBytes)
        pabyTablXBlockMap = struct.unpack('B' * nSizeInBytes, pabyTablXBlockMap)
        nCountBlocks = 0
        for i in range(nBitsForBlockMap):
            nCountBlocks += TEST_BIT(pabyTablXBlockMap, i)
        assert nCountBlocks == n1024Blocks, (nCountBlocks, n1024Blocks)

f = open(filename, 'rb')
f.seek(4, 0)
nfeatures = read_uint32(f)
print('nfeatures = %d' % nfeatures)


f.seek(32, 0)
header_offset_low = read_uint32(f)
header_offset_high = read_uint32(f)
header_offset = header_offset_low | (header_offset_high << 32)
print('header_offset = %d' % header_offset)

f.seek(header_offset, 0)
header_length = read_uint32(f)
print('header_length = %d' % header_length)

f.read(4)

layer_geom_type = read_uint8(f)
print('layer_geom_type = %d' % layer_geom_type)
if layer_geom_type == 1:
    print('point')
if layer_geom_type == 2:
    print('multipoint')
if layer_geom_type == 3:
    print('polyline')
if layer_geom_type == 4:
    print('polygon')
if layer_geom_type == 9:
    print('multipatch')

# skip 3 bytes
f.seek(3, 1)
nfields = read_uint8(f)
nfields += read_uint8(f) * 256
print('nfields = %d' % nfields)

xyscale = None

class FieldDesc:
    pass

fields = []
has_flags = False
nullable_fields = 0

TYPE_INT16 = 0
TYPE_INT32 = 1
TYPE_FLOAT32 = 2
TYPE_FLOAT64 = 3
TYPE_STRING = 4
TYPE_DATETIME = 5
TYPE_OBJECTID = 6
TYPE_GEOMETRY = 7
TYPE_BINARY = 8
TYPE_RASTER = 9
TYPE_UUID_1 = 10
TYPE_UUID_2 = 11
TYPE_XML = 12

def field_type_to_str(type):
    if type == TYPE_INT16:
        return 'int16'
    if type == TYPE_INT32:
        return 'int32'
    if type == TYPE_FLOAT32:
        return 'float32'
    if type == TYPE_FLOAT64:
        return 'float64'
    if type == TYPE_STRING:
        return 'string'
    if type == TYPE_DATETIME:
        return 'datetime'
    if type == TYPE_OBJECTID:
        return 'objectid'
    if type == TYPE_GEOMETRY:
        return 'geometry'
    if type == TYPE_BINARY:
        return 'binary'
    if type == TYPE_RASTER:
        return 'raster'
    if type == TYPE_UUID_1:
        return 'UUID'
    if type == TYPE_UUID_2:
        return 'UUID'
    if type == TYPE_XML:
        return 'XML'
    return 'unknown'
    
def multipatch_part_type_to_str(type):
    if type == 0:
        return "triangle strip"
    if type == 1:
        return "triangle fan"
    if type == 2:
        return "outer ring"
    if type == 3:
        return "inner ring"
    if type == 4:
        return "first ring"
    if type == 5:
        return "ring"
    if type == 6:
        return "triangles"
    return "unknown"

def read_curves(f):
    print('curves:')
    for i in range(nb_curves):
        print('curve %d:' % i)
        start_index = read_varuint(f)
        curve_type =  read_varuint(f)
        print('start_index = %d' % start_index)
        print('curve_type = %d' % curve_type)
        if curve_type == 1:
            print(' --> circular arc')
            print('d1 = %f' % read_float64(f))
            print('d2 = %f' % read_float64(f))
            bits = read_uint32(f)
            print('bits = %d' % bits)
            if (bits & 0x1):  print(' IsEmpty')
            if (bits & 0x8):  print(' IsCCW')
            if (bits & 0x10): print(' IsMinor')
            if (bits & 0x20): print(' IsLine')
            if (bits & 0x40): print(' IsPoint')
            if (bits & 0x80): print(' DefinedIP')
        elif curve_type == 2:
            print(' --> line arc')
            print('should not happen')
        elif curve_type == 3:
            print(' --> spiral arc')
            print('undocumented')
        elif curve_type == 4:
            print(' --> bezier arc')
            print('p0.x = %f' % read_float64(f))
            print('p0.y = %f' % read_float64(f))
            print('p1.x = %f' % read_float64(f))
            print('p1.y = %f' % read_float64(f))
        elif curve_type == 5:
            print(' --> elliptic arc')
            print('vs0 = %f' % read_float64(f))
            print('vs1 = %f' % read_float64(f))
            print('rotation or fromv = %f' % read_float64(f))
            print('semimajor = %f' % read_float64(f))
            print('minormajorratio or deltav = %f' % read_float64(f))
            bits = read_uint32(f)
            print('bits = %d' % bits)
            if (bits & 0x1):    print(' IsEmpty')
            if (bits & 0x40):   print(' IsLine')
            if (bits & 0x80):   print(' IsPoint')
            if (bits & 0x100):  print(' IsCircular')
            if (bits & 0x200):  print(' CenterTo')
            if (bits & 0x400):  print(' CenterFrom')
            if (bits & 0x800):  print(' IsCCW')
            if (bits & 0x1000): print(' IsMinor')
            if (bits & 0x2000): print(' IsComplete')
        else:
            print('unexpected value')


for i in range(nfields):
    
    fd = FieldDesc()
    #print(f.tell())
    
    print('')
    nbcar =  read_uint8(f)
    
    if False:
        # obsolete logic since we have discovered default values
        # PreNIS.gdb/a00000009.gdbtable has 0's after some fields !
        while nbcar == 0:
            print('skipping zero byte')
            nbcar =  read_uint8(f)
    
    print('nbcar = %d' % nbcar)
    name = ''
    for j in range(nbcar):
        name = name + '%c' % read_uint8(f)
        f.read(1)
    print('name = %s' % name)
    fd.name = name
    
    nbcar = read_uint8(f)
    print('nbcar_alias = %d' % nbcar)
    alias = ''
    for j in range(nbcar):
        alias = alias + '%c' % read_uint8(f)
        f.read(1)
    print('alias = %s' % alias)
    fd.alias = alias
    
    type = read_uint8(f)
    fd.type = type
    fd.nullable = True

    print('type = %d (%s)' % (type, field_type_to_str(type)))
    # objectid
    if type == TYPE_OBJECTID:
        print('magic1 = %d' % read_uint8(f))
        print('magic2 = %d' % read_uint8(f))
        fd.nullable = False

    # shape
    elif type == TYPE_GEOMETRY:
        magic1 = read_uint8(f) # 0
        flag = read_uint8(f) # 6 or 7
        if (flag & 1) == 0:
            fd.nullable = False
        
        print('magic1 = %d' % magic1)
        print('flag = %d' % flag)
        wkt_len = read_uint8(f)
        wkt_len += read_uint8(f) * 256
        
        wkt = ''
        for j in range(wkt_len // 2):
            wkt = wkt + '%c' % read_uint8(f)
            f.read(1)
        print('wkt = %s' % wkt)
        
        magic3 = read_uint8(f)
        print('magic3 = %d' % magic3)
        
        has_m = False
        has_z = False
        if magic3 == 5:
            has_z = True
        if magic3 == 7:
            has_m = True
            has_z = True

        xorig = read_float64(f)
        print('xorigin = %.15f' % xorig)
        yorig = read_float64(f)
        print('yorigin = %.15f' % yorig)
        xyscale = read_float64(f)
        print('xyscale = %.15f' % xyscale)
        if has_m:
            morig = read_float64(f)
            print('morigin = %.15f' % morig)
            mscale = read_float64(f)
            print('mscale = %.15f' % mscale)
        if has_z:
            zorig = read_float64(f)
            print('zorigin = %.15f' % zorig)
            zscale = read_float64(f)
            print('zscale = %.15f' % zscale)
        xytolerance = read_float64(f)
        print('xytolerance = %.15f' % xytolerance)
        if has_m:
            mtolerance = read_float64(f)
            print('mtolerance = %.15f' % mtolerance)
        if has_z:
            ztolerance = read_float64(f)
            print('ztolerance = %.15f' % ztolerance)

        xmin = read_float64(f)
        print('xmin = %.15f' % xmin)
        ymin = read_float64(f)
        print('ymin = %.15f' % ymin)
        xmax = read_float64(f)
        print('xmax = %.15f' % xmax)
        ymax = read_float64(f)
        print('ymax = %.15f' % ymax)
        
        cur_pos = f.tell()
        print('cur_pos = %d' % cur_pos)
        while True:
            read5 = struct.unpack('B' * 5, f.read(5))
            if read5[0] != 0 or (read5[1] != 1 and read5[1] != 2 and read5[1] != 3) or read5[2] != 0 or read5[3] != 0 or read5[4] != 0:
                f.seek(-5,1)
                print(read_float64(f))
            else:
                for i in range(read5[1]):
                    print(read_float64(f))
                break

    # string
    elif type == TYPE_STRING:
        width = read_uint32(f)
        fd.width = width
        print('width = %d' % width)
        flag = read_uint8(f)
        if (flag & 1) == 0:
            fd.nullable = False
        print('flag = %d' % flag)
        default_value_length = read_varuint(f)
        print('default_value_length = %d' % default_value_length)
        if (flag & 4) != 0 and default_value_length > 0:
            print('default value: %s' % f.read(default_value_length))

    # binary
    elif type == TYPE_BINARY:
        f.read(1)
        flag = read_uint8(f)
        if (flag & 1) == 0:
            fd.nullable = False
        print('flag = %d' % flag)

    # raster
    elif type == TYPE_RASTER:
        f.read(1)
        flag = read_uint8(f)
        if (flag & 1) == 0:
            fd.nullable = False
        print('flag = %d' % flag)
        
        nbcar = read_uint8(f)
        print('nbcar = %d' % nbcar)
        raster_column = ''
        for j in range(nbcar):
            raster_column = raster_column + '%c' % f.read(1)
            f.read(1)
        print('raster_column = %s' % raster_column)

        wkt_len = read_uint8(f)
        wkt_len += read_uint8(f) * 256
        
        wkt = ''
        for j in range(wkt_len // 2):
            wkt = wkt + '%c' % read_uint8(f)
            f.read(1)
        print('wkt = %s' % wkt)
        
        #f.read(82)
        
        magic3 = read_uint8(f)
        print('magic3 = %d' % magic3)
        
        if magic3 > 0:
            raster_has_m = False
            raster_has_z = False
            if magic3 == 5:
                raster_has_z = True
            if magic3 == 7:
                raster_has_m = True
                raster_has_z = True

            raster_xorig = read_float64(f)
            print('xorigin = %.15f' % raster_xorig)
            raster_yorig = read_float64(f)
            print('yorigin = %.15f' % raster_yorig)
            raster_xyscale = read_float64(f)
            print('xyscale = %.15f' % raster_xyscale)
            if raster_has_m:
                raster_morig = read_float64(f)
                print('morigin = %.15f' % raster_morig)
                raster_mscale = read_float64(f)
                print('mscale = %.15f' % raster_mscale)
            if raster_has_z:
                raster_zorig = read_float64(f)
                print('zorigin = %.15f' % raster_zorig)
                raster_zscale = read_float64(f)
                print('zscale = %.15f' % raster_zscale)
            raster_xytolerance = read_float64(f)
            print('xytolerance = %.15f' % raster_xytolerance)
            if raster_has_m:
                raster_mtolerance = read_float64(f)
                print('mtolerance = %.15f' % raster_mtolerance)
            if raster_has_z:
                raster_ztolerance = read_float64(f)
                print('ztolerance = %.15f' % raster_ztolerance)

        print(read_uint8(f))
        

    # UUID or XML
    elif type in (TYPE_UUID_1, TYPE_UUID_2, TYPE_XML):
        width = read_uint8(f)
        print('width = %d' % width)
        flag = read_uint8(f)
        if (flag & 1) == 0:
            fd.nullable = False
        print('flag = %d' % flag)

    else:
        width = read_uint8(f)
        print('width = %d' % width)
        flag = read_uint8(f)
        if (flag & 1) == 0:
            fd.nullable = False
        print('flag = %d' % flag)
        default_value_length = read_uint8(f)
        print('default_value_length = %d' % default_value_length)
        if (flag & 4) != 0:
            if type == 0 and default_value_length == 2:
                print('default_value = %d' % read_int16(f))
            elif type == 1 and default_value_length == 4:
                print('default_value = %d' % read_int32(f))
            elif type == 2 and default_value_length == 4:
                print('default_value = %f' % read_float32(f))
            elif type == 3 and default_value_length == 8:
                print('default_value = %f' % read_float64(f))
            elif type == 5 and default_value_length == 8:
                print('default_value = %f' % read_float64(f))
            else:
                f.read(default_value_length)
    
    if fd.nullable:
        has_flags = True
        nullable_fields = nullable_fields + 1
    print('nullable = %d ' % fd.nullable)
    
    if type != 6:
        fields.append(fd)

print('')

nCountBlocksBeforeIBlockIdx = 0
nCountBlocksBeforeIBlockValue = 0

for fid in range(nfeaturesx):

    if pabyTablXBlockMap:
        iBlock = fid // 1024
        # Check if the block is not empty
        if TEST_BIT(pabyTablXBlockMap, iBlock) == 0:
            continue

        # As we do sequential reading, optimization to avoid recomputing
        # the number of blocks since the beginning of the map
        assert iBlock >= nCountBlocksBeforeIBlockIdx
        nCountBlocksBefore = nCountBlocksBeforeIBlockValue
        for i in range(nCountBlocksBeforeIBlockIdx, iBlock):
            nCountBlocksBefore += TEST_BIT(pabyTablXBlockMap, i)

        nCountBlocksBeforeIBlockIdx = iBlock
        nCountBlocksBeforeIBlockValue = nCountBlocksBefore
        iCorrectedRow = nCountBlocksBefore * 1024 + (fid % 1024)
        fx.seek(16 + size_tablx_offsets * iCorrectedRow)
    else:
        fx.seek(16 + fid * size_tablx_offsets, 0)

    if size_tablx_offsets == 4:
        feature_offset = read_uint32(fx)
    elif size_tablx_offsets == 5:
        feature_offset = read_uint40(fx)
    elif size_tablx_offsets == 6:
        feature_offset = read_uint48(fx)
    else:
        assert False

    if feature_offset == 0:
        continue

    print('')
    print('FID = %d' % (fid + 1))
    print('feature_offset = %d' % feature_offset)

    f.seek(feature_offset, 0)

    blob_len = read_uint32(f)
    print('blob_len = %d' % blob_len)

    if has_flags:
        flags = []
        nremainingflags = nullable_fields
        while nremainingflags > 0:
            flags.append(read_uint8(f))
            nremainingflags -= 8
        print('flags = %s' % flags)

    ifield_for_flag_test = 0
    for ifield in range(len(fields)):

        if has_flags:
            if fields[ifield].nullable:
                test = (flags[ifield_for_flag_test >> 3] & (1 << (ifield_for_flag_test % 8)))
                ifield_for_flag_test = ifield_for_flag_test + 1
                if test != 0:
                    print('Field %s : NULL' % fields[ifield].name)
                    continue

        if fields[ifield].type == TYPE_INT16:
            val = read_int16(f)
            print('Field %s : %d' % (fields[ifield].name, val))

        elif fields[ifield].type == TYPE_INT32:
            val = read_int32(f)
            print('Field %s : %d' % (fields[ifield].name, val))

        elif fields[ifield].type == TYPE_FLOAT32:
            val = read_float32(f)
            print('Field %s : %f' % (fields[ifield].name, val))

        elif fields[ifield].type == TYPE_FLOAT64:
            val = read_float64(f)
            print('Field %s : %f' % (fields[ifield].name, val))

        elif fields[ifield].type in (TYPE_STRING, TYPE_XML):
            length = read_varuint(f)
            val = f.read(length)
            print('Field %s : "%s"' % (fields[ifield].name, val))

        elif fields[ifield].type == TYPE_DATETIME:
            val = read_float64(f)
            print('Field %s : %f days since 1899/12/30' % (fields[ifield].name, val))

        elif fields[ifield].type == TYPE_BINARY:
            length = read_varuint(f)
            val = f.read(length)
            print('Field %s : "%s" (len=%d)' % (fields[ifield].name, val, length))

        elif fields[ifield].type == TYPE_RASTER:
            length = read_int32(f)
            #length = read_varuint(f)
            #val = f.read(length)
            val = ''
            print('Field %s : "%s" (len=%d)' % (fields[ifield].name, val, length))

        elif fields[ifield].type in (TYPE_UUID_1, TYPE_UUID_2):
            val = f.read(16)
            print('Field %s : "%s"' % (fields[ifield].name, ''.join(x.encode('hex') for x in val)))

        elif fields[ifield].type == TYPE_GEOMETRY:
            geom_len = read_varuint(f)
            print('geom_len = %d' % geom_len)

            saved_offset = f.tell()

            geom_type = read_varuint(f)
            print('geom_type = %d --> %d' % (geom_type, geom_type & 0xff))
            if geom_type == 1:
                print('point')
            elif geom_type == 9:
                print('pointz')
            elif geom_type == 8:
                print('multipoint')
            elif geom_type == 18:
                print('multipoint zm')
            elif geom_type == 20:
                print('multipoint z')
            elif geom_type == 3:
                print('polyline')
            elif geom_type == 10:
                print('polyline z')
            elif geom_type == 13:
                print('polyline zm')
            elif geom_type == 23:
                print('polyline m')
            elif geom_type == 5:
                print('polygon')
            elif geom_type == 15:
                print('polygon zm')
            elif geom_type == 19:
                print('polygon z')
            elif geom_type == 25:
                print('polygon m')
            # BikeInventory.gdb/a00000009.gdbtable, FID = 29864
            elif geom_type & 0xff == 50:
                print('generalpolyline');
                if (geom_type & 0x80000000) != 0:
                    print(' has z')
                if (geom_type & 0x40000000) != 0:
                    print(' has m')
                if (geom_type & 0x20000000) != 0:
                    print(' has curves')
            # http://frap.cdf.ca.gov/data/frapgisdata-sw-cdfadmin13_1_download.php
            elif geom_type & 0xff == 51:
                print('generalpolygon');
                if (geom_type & 0x80000000) != 0:
                    print(' has z')
                if (geom_type & 0x40000000) != 0:
                    print(' has m')
                if (geom_type & 0x20000000) != 0:
                    print(' has curves')
            # /home/even/FileGDB_API/samples/data/Shapes.gdb/a00000027.gdbtable
            elif geom_type & 0xff == 54:
                print('multipatch');
                if (geom_type & 0x80000000) != 0:
                    print(' has z')
                if (geom_type & 0x40000000) != 0:
                    print(' has m')
            else:
                print('unhandled geom_type')


            if geom_type & 0xff == 50:

                nb_total_points = read_varuint(f)
                print("nb_total_points: %d" % nb_total_points)
                if nb_total_points == 0:
                    f.seek(saved_offset + geom_len, 0)
                    continue

                nb_geoms = read_varuint(f)
                print('nb_geoms = %d' % nb_geoms)

                # TODO ? Conditionnally or unconditionnally present ?
                if (geom_type & 0x20000000) != 0:
                    nb_curves = read_varuint(f)
                    print("nb_curves: %d" % nb_curves)

                read_bbox(f)
                tab_nb_points = read_tab_nbpoints(f, nb_geoms, nb_total_points)
                read_tab_xy(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x80000000) != 0:
                    read_tab_z(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x40000000) != 0:
                    read_tab_m(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x20000000) != 0:
                    read_curves(f)

            if geom_type & 0xff == 51:

                nb_total_points = read_varuint(f)
                print("nb_total_points: %d" % nb_total_points)
                if nb_total_points == 0:
                    f.seek(saved_offset + geom_len, 0)
                    continue

                nb_geoms = read_varuint(f)
                print("nb_geoms: %d" % nb_geoms)

                # TODO ? Conditionnally or unconditionnally present ?
                if (geom_type & 0x20000000) != 0:
                    nb_curves = read_varuint(f)
                    print("nb_curves: %d" % nb_curves)

                read_bbox(f)
                tab_nb_points = read_tab_nbpoints(f, nb_geoms, nb_total_points)
                read_tab_xy(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x80000000) != 0:
                    read_tab_z(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x40000000) != 0:
                    read_tab_m(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x20000000) != 0:
                    read_curves(f)

                #print("actual_length = %d vs %d" % (f.tell() - saved_offset, geom_len))

            if geom_type & 0xff == 54:

                nb_total_points = read_varuint(f)
                print("nb_total_points: %d" % nb_total_points)
                if nb_total_points == 0:
                    f.seek(saved_offset + geom_len, 0)
                    continue

                # what's that ???
                magic = read_varuint(f)
                print('magic = %d' % magic)

                nb_geoms = read_varuint(f)
                print("nb_geoms: %d" % nb_geoms)

                read_bbox(f)
                tab_nb_points = read_tab_nbpoints(f, nb_geoms, nb_total_points)

                subgeomtype = []
                for i_part in range(nb_geoms):
                    type = read_varuint(f)
                    # only keep lower 4 bits. See extended-shapefile-format.pdf
                    # page 8. Above bits are for priority, material index
                    type = type & 0xf
                    print("type[%d] = %d (%s)" % (i_part, type, multipatch_part_type_to_str(type)))
                    subgeomtype.append(type)

                read_tab_xy(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x80000000) != 0:
                    read_tab_z(f, nb_geoms, tab_nb_points)

                if (geom_type & 0x40000000) != 0:
                    read_tab_m(f, nb_geoms, tab_nb_points)

                #print("actual_length = %d vs %d" % (f.tell() - saved_offset, geom_len))

            if geom_type in (8, 18, 20):
                nb_total_points = read_varuint(f)
                print("nb_total_points: %d" % nb_total_points)
                if nb_total_points == 0:
                    f.seek(saved_offset + geom_len, 0)
                    continue

                read_bbox(f)

                dx_int = dy_int = 0
                for i in range(nb_total_points):
                    vi = read_varint(f)
                    dx_int = dx_int + vi
                    x = dx_int / xyscale + xorig
                    vi = read_varint(f) 
                    dy_int = dy_int + vi
                    y = dy_int / xyscale + yorig
                    print("[%d] x=%.15f y=%.15f" % (i, x, y))

                if geom_type in (18, 20):
                    dz_int = 0
                    for i in range(nb_total_points):
                        vi = read_varint(f) 
                        dz_int = dz_int + vi
                        z = dz_int / zscale + zorig
                        print("[%d] z=%.15f" % (i, z))

            if geom_type == 1:
                vi = read_varuint(f) - 1
                x0 = vi / xyscale + xorig
                vi = read_varuint(f) - 1
                y0 = vi / xyscale + yorig
                print("%.15f %.15f" % (x0, y0))

            if geom_type == 9:
                vi = read_varuint(f) - 1
                x0 = vi / xyscale + xorig
                vi = read_varuint(f) - 1
                y0 = vi / xyscale + yorig
                vi = read_varuint(f) - 1
                z0 = vi / zscale + zorig
                print("%.15f %.15f %.15f" % (x0, y0, z0))

            if geom_type in (3, 5, 10, 13, 15, 19, 23, 25):

                nb_total_points = read_varuint(f)
                print("nb_total_points: %d" % nb_total_points)
                if nb_total_points == 0:
                    f.seek(saved_offset + geom_len, 0)
                    continue
                nb_geoms = read_varuint(f)
                print("nb_geoms: %d" % nb_geoms)

                read_bbox(f)
                tab_nb_points = read_tab_nbpoints(f, nb_geoms, nb_total_points)
                read_tab_xy(f, nb_geoms, tab_nb_points)

                # z
                if geom_type in (10, 13, 15, 19):
                    read_tab_z(f, nb_geoms, tab_nb_points)

                # m
                if geom_type in (13, 15, 23, 25):
                    read_tab_m(f, nb_geoms, tab_nb_points)

                print('cur_offset = %d' % f.tell())

            f.seek(saved_offset + geom_len, 0)

        else:
            print('unhandled type : %d' % fields[ifield].type)
