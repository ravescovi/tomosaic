#!/usr/bin/env python# -*- coding: utf-8 -*-# ########################################################################## Copyright (c) 2015, UChicago Argonne, LLC. All rights reserved.         ##                                                                         ## Copyright 2015. UChicago Argonne, LLC. This software was produced       ## under U.S. Government contract DE-AC02-06CH11357 for Argonne National   ## Laboratory (ANL), which is operated by UChicago Argonne, LLC for the    ## U.S. Department of Energy. The U.S. Government has rights to use,       ## reproduce, and distribute this software.  NEITHER THE GOVERNMENT NOR    ## UChicago Argonne, LLC MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR        ## ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  If software is     ## modified to produce derivative works, such modified software should     ## be clearly marked, so as not to confuse it with the version available   ## from ANL.                                                               ##                                                                         ## Additionally, redistribution and use in source and binary forms, with   ## or without modification, are permitted provided that the following      ## conditions are met:                                                     ##                                                                         ##     * Redistributions of source code must retain the above copyright    ##       notice, this list of conditions and the following disclaimer.     ##                                                                         ##     * Redistributions in binary form must reproduce the above copyright ##       notice, this list of conditions and the following disclaimer in   ##       the documentation and/or other materials provided with the        ##       distribution.                                                     ##                                                                         ##     * Neither the name of UChicago Argonne, LLC, Argonne National       ##       Laboratory, ANL, the U.S. Government, nor the names of its        ##       contributors may be used to endorse or promote products derived   ##       from this software without specific prior written permission.     ##                                                                         ## THIS SOFTWARE IS PROVIDED BY UChicago Argonne, LLC AND CONTRIBUTORS     ## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT       ## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS       ## FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UChicago     ## Argonne, LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,        ## INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,    ## BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;        ## LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER        ## CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT      ## LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN       ## ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE         ## POSSIBILITY OF SUCH DAMAGE.                                             ## #########################################################################"""Module for input of tomosaic"""from __future__ import (absolute_import, division, print_function,                        unicode_literals)import logginglogger = logging.getLogger(__name__)__author__ = "Rafael Vescovi"__credits__ = "Doga Gursoy"__copyright__ = "Copyright (c) 2015, UChicago Argonne, LLC."__docformat__ = 'restructuredtext en'__all__ = ['get_files',           'get_index',           'save_partial_frames',           'save_partial_raw',           'build_panorama']import os, glob, reimport h5pyimport numpy as npimport tomopyimport dxchangefrom tomosaic.util.phase import retrieve_phasefrom tomosaic.merge.merge import *import shutilfrom scipy.misc import imread, imsaveimport matplotlib.pyplot as pltimport gcfrom tomopy import downsamplefrom scipy.misc import imresizedef get_files(folder, prefix, type='.h5'):    os.chdir(folder)    file_list = glob.glob(prefix + '*' + type)    return file_listdef get_index(file_list, pattern=0):    if pattern == 0:        regex = re.compile(r".+_x(\d+)_y(\d+).+")        ind_buff = [m.group(1, 2) for l in file_list for m in [regex.search(l)] if m]    elif pattern == 1:        regex = re.compile(r".+_y(\d+)_x(\d+).+")        ind_buff = [m.group(2, 1) for l in file_list for m in [regex.search(l)] if m]    return np.asarray(ind_buff).astype('int')def save_partial_frames(file_grid, save_folder, prefix, frame=0):    for (y, x), value in np.ndenumerate(file_grid):        print(value)        if (value != None):            prj, flt, drk = dxchange.read_aps_32id(value, proj=(frame, frame + 1))            prj = tomopy.normalize(prj, flt, drk)            prj = -np.log(prj).astype('float32')            fname = prefix + 'Y' + str(y).zfill(2) + '_X' + str(x).zfill(2)            dxchange.write_tiff(np.squeeze(prj), fname=os.path.join(save_folder, 'partial_frames', fname))def save_partial_raw(file_grid, save_folder, prefix):    for (y, x), value in np.ndenumerate(file_grid):        if (value != None):            prj, flt, drk = dxchange.read_aps_32id(value, proj=(0, 1))            fname = prefix + 'Y' + str(y).zfill(2) + '_X' + str(x).zfill(2)            flt = flt.mean(axis=0).astype('float32')        dxchange.write_tiff(np.squeeze(flt), fname=os.path.join(save_folder, 'partial_flats', fname))        drk = drk.mean(axis=0).astype('float16')    dxchange.write_tiff(np.squeeze(drk), fname=os.path.join(save_folder, 'partial_darks', fname))    prj = prj.astype('float32')    dxchange.write_tiff(np.squeeze(prj), fname=os.path.join(save_folder, 'partial_frames_raw', fname))g_shapes = lambda fname: h5py.File(fname, "r")['exchange/data'].shapedef build_panorama(file_grid, shift_grid, frame=0, method='max'):    cam_size = g_shapes(file_grid[0, 0])    cam_size = cam_size[1:3]    img_size = shift_grid[-1, -1] + cam_size    buff = np.zeros([1, 1], dtype='float16')    for (y, x), value in np.ndenumerate(file_grid):        if (value != None and frame < g_shapes(value)[0]):            prj, flt, drk = dxchange.read_aps_32id(value, proj=(frame, frame + 1))            prj = tomopy.normalize(prj, flt[10:15, :, :], drk)            prj[np.abs(prj) < 2e-3] = 2e-3            prj[prj > 1] = 1            prj = -np.log(prj).astype('float16')            prj[np.where(np.isnan(prj) == True)] = 0            buff = blend(buff, np.squeeze(prj), shift_grid[y, x, :], method=method)    return buffdef grid2file(grid, file_name):    with file(file_name, 'w') as outfile:        # for data_slice in grid:        ncol = len(grid[0, 0, :])        nval = grid.shape[0] * grid.shape[1]        y_lst = np.zeros(nval)        x_lst = np.zeros(nval)        values = np.zeros([ncol, nval])        ind = 0        for y in range(grid.shape[0]):            for x in range(grid.shape[1]):                y_lst[ind] = y                x_lst[ind] = x                temp = grid[y, x, :]                values[:, ind] = temp                ind += 1        outarr = [y_lst, x_lst]        outarr = np.append(outarr, values, axis=0)        outarr = np.transpose(outarr)        outarr = np.squeeze(outarr)        np.savetxt(outfile, outarr, fmt=str('%4.2f'))    returndef file2grid(file_name):    with file(file_name, 'r') as infile:        grid0 = np.loadtxt(file_name)        grid_shape = [grid0[-1, 0] + 1, grid0[-1, 1] + 1]        grid_shape = map(int, grid_shape)        ncol = len(grid0[0, :]) - 2        grid = np.zeros([grid_shape[0], grid_shape[1], ncol])        for line in grid0:            y, x = map(int, (line[0], line[1]))            grid[y, x, :] = line[2:]    return griddef normalize(img):    img = (img - img.min()) / (img.max() - img.min())    return imgdef reorganize_dir(file_list, raw_ds=[1,2,4], pr_ds=[2], pr='mba', flats=[5,9],darks=[5,9], dtype='uint16', limits=[0, 0.001], **kwargs):    """    Reorganize hdf5 files and reorganize directory as:    ----------------    /raw_1x/1920x1200x4500 x* 12x11                  /shift_matrix                 /center_matrix    /raw_2x/960x600x4500     x* 12x11    /raw_4x/480x300x4500     x* 12x11    /pr_2x/960x600x4500       x* 12x11    ---------------    /recon_gridrec_1x    x* means grid of hdf5 files    Parameters:    -----------    file_list : ndarray        List of h5 files in the directory.    convert : int, optional        Bit of integer the data are to be converted into.    """      dtype = 'uint16'
    display_min, display_max = limits    # downsample    for fname in file_list:        print('Now processing '+str(fname))        # make downsampled subdirectories        for ds in raw_ds:            # create downsample folder if not existing            folder_name = 'data_raw_'+str(ds)+'x'            if not os.path.exists(folder_name):                os.mkdir(folder_name)            # copy file if downsample level is 1            if ds == 1:                if not os.path.isfile(folder_name+'/'+fname):                    shutil.copyfile(fname, folder_name+'/'+fname)                    #h5_cast(folder_name+'/'+fname, display_min, display_max, dtype=dtype)            # otherwise perform downsampling            else:                if not os.path.isfile(folder_name+'/'+fname):                    o = h5py.File(fname)                    f = h5py.File(folder_name+'/'+fname)                    dat_grp = f.create_group('exchange')                    # downsample projection data                    raw = o['exchange/data']                    full_shape = raw.shape                    dat = dat_grp.create_dataset('data', (full_shape[0], np.floor(full_shape[1]/ds), np.floor(full_shape[2]/ds)), dtype=dtype)                    # write downsampled data frame-by-frame                    n_frames = full_shape[0]                    for frame in range(n_frames):                        temp = raw[frame, :, :]                        temp = image_downsample(temp, ds)                        dat[frame, :, :] = temp                        print('\r    DS{:d} : At frame {:d}'.format(ds, frame), end='')                    print(' ')                    # downsample flat field data                    raw = o['exchange/data_white']                    full_shape = raw.shape                    dat = dat_grp.create_dataset('data_white', (full_shape[0], np.floor(full_shape[1]/ds), np.floor(full_shape[2]/ds)), dtype=dtype)                    for frame in range(full_shape[0]):                        temp = raw[frame, :, :]                        temp = image_downsample(temp, ds)                        dat[frame, :, :] = temp                    # downsample dark field data                    raw = o['exchange/data_dark']                    full_shape = raw.shape                    dat = dat_grp.create_dataset('data_dark', (full_shape[0], np.floor(full_shape[1]/ds), np.floor(full_shape[2]/ds)), dtype=dtype)                    for frame in range(full_shape[0]):                        temp = raw[frame, :, :]                        temp = image_downsample(temp, ds)                        dat[frame, :, :] = temp	###########################################        
	# make phase retrieval subdirectories        for ds in pr_ds:            folder_name='data_mba_'+str(ds)+'x'            if not os.path.exists(folder_name):                os.mkdir(folder_name)            o = h5py.File(fname)            f = h5py.File(folder_name+'/'+fname)            dat_grp = f.create_group('exchange')            # downsample projection data            raw = o['exchange/data']            full_shape = raw.shape            dat = dat_grp.create_dataset('data', (full_shape[0], np.floor(full_shape[1]/ds), np.floor(full_shape[2]/ds)), dtype='float16')

            # load flats and darks            _, flt, drk = dxchange.read_aps_32id(fname, proj=(0,1))    
            # write downsampled data frame-by-frame            for frame in range(full_shape[0]):
                print('\r    PR: At frame {:d}'.format(frame), end='')                temp = raw[frame, :, :]
                temp = temp.reshape([1, temp.shape[0], temp.shape[1]])
                temp = tomopy.normalize(temp, flt[flats],drk[darks])
                temp = np.squeeze(temp)                temp = image_downsample(temp, ds)                temp = retrieve_phase(temp, [1, 1], method=pr, **kwargs)                dat[frame, :, :] = temp.astype('float16')
            print(' ')
      

        ##this looks at the wrong level        os.remove(fname)def reorganize_tiffs():    tiff_list = glob.glob('*.tiff')    for fname in tiff_list:        print('Now processing '+str(fname))        # make downsampled subdirectories        for ds in [1, 2, 4]:            # create downsample folder if not existing            folder_name = 'tiff_'+str(ds)+'x'            if not os.path.exists(folder_name):                os.mkdir(folder_name)            # copy file if downsample level is 1            if ds == 1:                shutil.copyfile(fname, folder_name+'/'+fname)            # otherwise perform downsampling            else:                temp = imread(fname, flatten=True)                temp = image_downsample(temp, ds)                imsave(folder_name+'/'+fname, temp, format='tiff')def global_histogram(dmin, dmax, n_bins, plot=True):    tiff_list = glob.glob('*.tiff')    mybins = np.linspace(dmin, dmax, n_bins + 1)    myhist = np.zeros(n_bins, dtype='int32')    bin_width = (dmax - dmin) / n_bins    for fname in tiff_list:        print('Now analyzing'+fname)        temp = imread(fname, flatten=True)        temp = np.ndarray.flatten(temp)        myhist = myhist + np.histogram(temp, bins=mybins)[0]    if plot:        plt.bar(mybins[:-1], myhist, width=bin_width)        plt.show()    return myhist, mybinsdef img_cast(image, display_min, display_max, dtype='uint16'):    bit = int(re.findall(r'\d+', dtype)[0])    divider = 2 ** bit    image.clip(display_min, display_max, out=image)    image -= display_min    image = image / (display_max - display_min + 1) * float(divider)    return image.astype(dtype)def image_downsample(img, ds):    temp = imresize(img, 1. / ds)    return tempdef h5_cast(fname, display_min, display_max, dtype='uint16'):    f = h5py.File(fname)    dset = f['exchange/data']    for i in range(dset.shape[0]):        temp = dset[i, :, :]        temp = img_cast(temp, display_min, display_max, dtype=dtype)        dset[i, :, :] = temp        print('\r    At frame {:d}'.format(i), end='')    print('')    dset = f['exchange/data_white']    for i in range(dset.shape[0]):        temp = dset[i, :, :]        temp = img_cast(temp, display_min, display_max, dtype=dtype)        dset[i, :, :] = temp    dset = f['exchange/data_dark']    for i in range(dset.shape[0]):        temp = dset[i, :, :]        temp = img_cast(temp, display_min, display_max, dtype=dtype)        dset[i, :, :] = temp    return
