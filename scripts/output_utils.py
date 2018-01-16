#!/usr/bin/env python

# Tobey Carman
# Dec 2017

# A set of functions for plotting dvmdostem ouputs.

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import netCDF4 as nc
import collections

def sum_monthly_flux_to_yearly(data):
  '''
  Expects `data` to be at least a 1D array, with the first axis being time.
  Also assumes that the time axis starts and stops on Jan 1 and Dec 31. In 
  otherwords, if you had a 2 years of monthly data that ran from Aug 1 thru
  July 31, this function would NOT work!  
  '''
  if (data.shape[0] % 12) != 0:
    raise RuntimeError('data size for dimension 0 (time) must be an even multiple of 12')

  newshape = [data.shape[0]/12]
  for i in data.shape[1:]:
    newshape.append(i)

  yearly_data = np.zeros((newshape)) * np.nan

  for i in range(0, newshape[0]):
    yr_start = (i * 12)
    yr_end = (i * 12) + 12
    yearly_data[i] = np.sum(data[yr_start:yr_end], axis=0)

  return yearly_data


def sum_across_compartments(data):
  '''
  Expects `data` to be a 5D numpy array with dimensions 
  `(time, pftpart, pft, y, x)`.

  Returns a 4D array that has been summed over the `pftpart` dimension,
  effectively creating a new array with totals for a PFT instead of having
  values split by compartment.
  '''
  if len(data.shape) != 5:
    raise RuntimeError('data input parameter must have 5 dimensions')
  return np.sum(data, axis=1)


def sum_across_pfts(data):
  '''
  Expects `data` to be a 4D numpy array with dimensions
  `(time, pft, y, x)`.

  Returns a 3D array that has been summed over the `pft` dimension, effectively
  creating a new array with totals for an entire gridcell/pixel instead of
  having the totals broken out by PFT.
  '''
  if len(data.shape) != 4:
    raise RuntimeError('data input parameter must have 4 dimensions')
  return np.sum(data, axis=1)


def sum_across_layers(data):
  '''
  Expects `data` to be a 4D numpy array with dimensions
  `(time, layers, y, x)`.

  Returns a 3D array that has been summed over the `layer` dimension, 
  effectively creating a new array with totals for an entire gridcell/pixel 
  instead of having the totals broken out by PFT.
  '''
  if len(data.shape) != 4:
    raise RuntimeError('data input parameter must have 4 dimensions')
  return np.sum(data, axis=1)


def stitch_stages(var, timestep, stages, fileprefix=''):
  '''
  Expects `var` to be one the dvmdostem output variable names. `timestep` must
  be one of "yearly" or "monthly", and stages is a (ordered) list containing 
  one or more of "pr","eq","sp","tr","sc". `fileprefix` is an optional path
  that will be pre-pended to the filenames for opening files in a different
  directory.

  Outputs from dvmdostem assume one variable per file and the following 
  file-naming pattern: 
  
      `var`_`timestep`_`stage`.nc
  
  This function makes the following additional assumptions about the files:
    - All files for different timesteps have the same dimensions
    - The file's variable name is the same as the variable name in the filename.
    - There is a units attribute?

  Returns a tuple (`data`, `units`), where `data` is a multi-dimensional numpy 
  array that is the concatenation of the input arrays along the time axis and 
  `units` is the unit string that is found in the input netcdf files.
  '''

  expected_file_names = ["{}_{}_{}.nc".format(var, timestep, stg) for stg in stages]
  expected_file_names = [os.path.join(fileprefix, i) for i in expected_file_names]

  full_ds = np.array([])
  units_str = ''
  for i, exp_file in enumerate(expected_file_names):
    print "Trying to open: ", exp_file
    with nc.Dataset(exp_file, 'r') as f:
      #print f.variables[var].units
      if i == 0:
        full_ds = f.variables[var][:]
        units_str = f.variables[var].units
      else:
        full_ds = np.concatenate( (full_ds, f.variables[var][:]), axis=0 )
        if f.variables[var].units != units_str:
          raise RuntimeError("Something is wrong with your input files! Units don't match!")

  return (full_ds, units_str)


def check_files(fnames):
  '''
  A work in progress for verifying assumptions about input files, `fnames`.

  Prints messages to stdout.

  Returns `None`.
  '''

  def get_dims(afile):
    '''
    Attempts to open `afile` as a netCDF file and read dimensions.
    
    Prints message for RuntimeErrors resulting from opening and reading file.

    Returns a list of dimensions in the file.
    '''
    try:
      with nc.Dataset(afile, 'r') as f:
        dims = f.variables[var].dimensions
    except RuntimeError as e:
      print "RuntimeError! Problem opening/reading: {} message: {}".format(afile, e.message)
      dims = None

    return dims

  dims_for_each_file = [get_dims(f) for f in fnames]

  if len(set(dims_for_each_file)) > 1:
    print "Warning! Not all files have the same dims!"

  if set(dims_for_each_file).pop() is None:
    print "Warning! At least one file doesn't even have dimensions!"

  if len(set(dims_for_each_file).pop()) > 0:
    first_item = set(dims_for_each_file).pop()
    if first_item[0].lower() != 'time':
      print "Warning! It appears that the first dimension is not time!"  
  else: 
    print "Warning! No dimensions, can't check for time as first dimension!"


def mask_by_cmt(data, cmtnum, vegmap_filepath):
  '''
  Expects `data` to be at least a 2D array with the last two dimensions being
  (y, x). `cmtnum` is the community type number that will remain unmasked
  in the final data. `vegmap_filepath` should be the path to dvmdostem input 
  vegetation map file, which has dimensions (y,x) and an integer specifying 
  the CMT number for each pixel, under the variable 'veg_class'.

  Returns a numpy  masked array with the same dimensions as `data`. In the
  returned array, data for pixels in `vegmap_filepath` equal to `cmtnum` will
  unmasked.

  Example:

    # An nd veg mask
    # Assumed that the shape of data is either 
    # 3D (time, y, x), 
    # 4D (time, pft, y, x) or (time, layer, y, x) or 
    # 5D (time, pftpart, pft, y, x),
    # and that in any case, the last two dimensions are y and x

    # For example:
    In [142]: ba = np.random.randint(0,100,(2,3,4,5,5))

    In [143]: np.broadcast_to(np.random.randint(0,2,(5,5)), ba.shape).shape
    Out[143]: (2, 3, 4, 5, 5)

  '''
  vegmap = nc.Dataset(vegmap_filepath, 'r')

  vegmask = np.ma.masked_not_equal(vegmap.variables['veg_class'][:], cmtnum)

  vmnd_mask = np.broadcast_to(vegmask.mask, data.shape)

  # Full data, masked by veg type
  vmnd_all = np.ma.masked_array(data, vmnd_mask)

  return vmnd_all

def mask_by_failed_run_status(data, run_status_filepath="run_status.nc"):
  '''
  Masks out any data for which the run status is < 0 in the `run_status_filepath`.

  `data`: (numpy.ndarray) must have at least 2 dimensions (y, x) and they must
   be the last dimensions.

  `run_status_file`: (str) path to a dvmdostem run_status.nc file that has
  dimensions (y,x) and single variable run_status(y,x) that has positive values
  for successfully run pixels and negative values for failed pixels.

  Returns a numpy masked array the same shape as `data` with all the data for
  failed pixels masked out.

  Example: see mask_by_cmt(...)
  '''
  runstat = nc.Dataset(run_status_filepath)

  runstatmask = np.ma.masked_less(runstat.variables['run_status'][:], 0)

  rsnd_mask = np.broadcast_to(runstatmask.mask, data.shape)

  rsnd_all = np.ma.masked_array(data, rsnd_mask)

  return rsnd_all

def plot_comp_sst():

  ROWS=4; COLS=4 

  gs = gridspec.GridSpec(ROWS, COLS)

  for i, cmt in enumerate([4,5,6,7]):
    ax = plt.subplot(gs[i,:])
    plot_spatial_summary_timeseries('VEGC', 'yearly', cmt, 'tr sc'.split(' '), "vegetation.nc", "run_status.nc", ax=ax)

  plt.tight_layout()
  plt.show(block=True)



def plot_spatial_summary_timeseries(var, timestep, cmtnum, stages, ref_veg_map, ref_run_status, ax=None):
  '''
  Plots a single line with min/max shading representing the `var` averaged over
  the spatial dimension, considering only pixels for `cmtnum`. Stitches together
  data for the specified `stages`.

  `var`: (string) must be one of the dvmdostem output variables (upper case).

  `timesteps`: (string) must be one of "monthly" or "yearly".

  `cmtnum`: (int) must be a number found in the veg map, see `mask_by_cmt(..)`.

  `stages`: (list) must contain one or more of "pr","eq","sp","tr","sc".

  `ref_veg_map`: (str) must be a file path to a dvmdostem vegetation input map
  with dimensions (y, x) and a single variable veg_class(y,x) with a number for
  representing the community type for that pixel.
  
  `ref_run_status`: (str) must be a file path to a dvmdostem run_status.nc map
  with dimensions (y,x) and a single variable run_status(y, with a number for 
  how the pixel completed its run.

  `ax`: (matplotlib.axes._subplots.AxesSubplot instance) will plot line(s) on
  this axes instance. If ax in None, then will create (and show) a new figure
  and plot.

  Attempts to find the requsite files for `var`, `timestep` and `stages`.
  Plots a timeseries of variable `var` after averaging over the spatial
  dimensions. If the data found in the input files is higher dimensionality
  than (time, y, x), for example (time, pft, y, x), then the data is 
  summed across PFTs before plotting.

  Returns `None`
  '''
  data, units = stitch_stages(var, timestep, stages)
  print "data size:", data.size

  data = mask_by_cmt(data, cmtnum, ref_veg_map)
  print "data count after masking cmt:", data.count()

  data = mask_by_failed_run_status(data, ref_run_status)
  print "data count after masking run status:", data.count()

  if len(data.shape) == 5: # assume (time, pftpart, pft, y, x)
    data = sum_across_compartments(data)

  if len(data.shape) == 4: # assume (time, pft, y, x) or (time, layer, y, x)
    data = sum_across_pfts(data) # alternatively, use sum_across_layers(..)

  if len(data.shape) == 3: # assume (time, y, x)
    pass # all set...

  workhorse_spatial_summary_plot(data, cmtnum, units, var, stages, ax=ax)


def workhorse_spatial_summary_plot(data, cmtnum, yunits, varname, stages, ax=None):
  '''
  Worker function, plots a line for average along time axis (axis 0), 
  with shading for min and max.

  `data`: (numpy.ndarray) must have dimensions (time, y, x).

  `cmtnum`: (int)  used for the plot title.

  `varname`: (str) used for the plot title

  `stages`: (list) used for the plot title, must contain one or 
            more of "pr","eq","sp","tr","sc".

  `ax`: (matplotlib.axes._subplots.AxesSubplot instance) will plot line(s) on
  this axes instance. If ax in None, then will create (and show) a new figure
  and plot.

  Returns `None`
  '''
  if ax is not None:
    print "Plotting on existing ax instance..."
    ax.plot(np.ma.average(data, axis=(1,2)), linewidth=0.5, label="CMT {}".format(cmtnum))
    ax.fill_between(
        np.arange(0, len(data)),
        np.ma.min(data, axis=(1,2)), 
        np.ma.max(data, axis=(1,2)), 
        color='gray', alpha=0.25
    )
    ax.set_ylabel(yunits)
    ax.set_title("{} for CMT {} averaged spatially for stages {}".format(varname, cmtnum, stages))
    #plt.show(block=True)

  else:
    print "Plotting on new ax, figure..."
    plt.plot(np.ma.average(data, axis=(1,2)), linewidth=0.5, label="CMT {}".format(cmtnum))
    plt.fill_between(
        np.arange(0, len(data)),
        np.ma.min(data, axis=(1,2)), 
        np.ma.max(data, axis=(1,2)), 
        color='gray', alpha=0.25
    )
    plt.ylabel(yunits)
    plt.title("{} for CMT {} averaged spatially for stages {}".format(varname, cmtnum, stages))
    plt.show(block=True)


def plot_inputs(cmtnum, hist_fname, proj_fname, ref_veg_map):
  '''
  Plots the historic and projected climate inputs, averaging over the spatial
  dimensions and with shading for min/max.

  `cmtnum`: (int) CMT to work with, must be in the veg map, see mask_by_cmt(..).

  `hist_fname`: (str) path to a dvmdostem historic input file.

  `proj_fname`: (str) path to a dvmdostem projected input file.

  The historic and projected input files are assumed to be have the variables
  tair, precip, vapor_press, and nirr all with the dimensions (time, y, x). 
  The files are assumed to be monthly resolution.

  Returns `None`.
  '''
  with nc.Dataset(hist_fname) as f:
    htair = f.variables['tair'][:]
    hprecip = f.variables['precip'][:]
    hvp = f.variables['vapor_press'][:]
    hnirr = f.variables['nirr'][:]

  with nc.Dataset(proj_fname) as f:
    ptair = f.variables['tair'][:]
    pprecip = f.variables['precip'][:]
    pvp = f.variables['vapor_press'][:]
    pnirr = f.variables['nirr'][:]

  tair = np.concatenate((htair, ptair), axis=0)
  precip = np.concatenate((hprecip, pprecip), axis=0)
  vp = np.concatenate((hvp, pvp), axis=0)
  nirr = np.concatenate((hnirr, pnirr), axis=0)

  tair = mask_by_cmt(tair, cmtnum, ref_veg_map)
  precip = mask_by_cmt(precip, cmtnum, ref_veg_map)
  vp = mask_by_cmt(vp, cmtnum, ref_veg_map)
  nirr = mask_by_cmt(nirr, cmtnum, ref_veg_map)

  #fig, (tair_ax, precip_ax, vp_ax, nirr_ax) = plt.subplots()

  tair_ax = plt.subplot(411)
  precip_ax = plt.subplot(412, sharex=tair_ax)
  vp_ax = plt.subplot(413, sharex=tair_ax)
  nirr_ax = plt.subplot(414, sharex=tair_ax)

  for pax, data, vname in zip([tair_ax, precip_ax, vp_ax, nirr_ax], [tair, precip, vp, nirr], ['tair','precip','vapor_press','nirr']):

    pax.plot(np.ma.average(data, axis=(1,2)), linewidth=0.5, label="{}".format(vname))
    pax.fill_between(
        np.arange(0, len(data)),
        np.ma.min(data, axis=(1,2)), 
        np.ma.max(data, axis=(1,2)), 
        color='gray', alpha=0.25
    )

    # add a line marking the transition from historic to projected
    pax.vlines(htair.shape[0], *pax.yaxis.get_view_interval(), color='red')

    pax.set_title("{} averaged spatially for historic and projected masked to cmt{}".format(vname, cmtnum))

  plt.tight_layout()
  plt.show(block=True)
  

def boxplot_monthlies(var, stages, cmtnum, ref_veg_map, ref_run_status, facecolor='blue'):
  '''
  Makes a boxplot showing distribution of values for `var` for each month,
  averaged over spatial dimensions, and only considering `cmtnum`. If multiple
  stages are specified, the stages will be stitched together along the time 
  dimension before the distributions are calculated.

  `var`: (str) one of the dvmdostem output variables.
  `stages`: (list) must contain one or more of "pr","eq","sp","tr","sc".
  `cmtnum`: (int) which CMT to work with.
  `ref_veg_map`: (str) path to a vegetation map to use for masking cmts
  `ref_run_status`: (str) path to run status map to use for masking failed cells
  `facecolor`: (str) color to use for the box.

  Returns `None`
  '''

  data, units = stitch_stages(var, 'monthly', stages)
  print "data size:", data.size

  data = mask_by_cmt(data, cmtnum, ref_veg_map)
  print "data count after masking cmt:", data.count()

  data = mask_by_failed_run_status(data, ref_run_status)
  print "data count after masking run status:", data.count()


  # list of months
  months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(' ')
  
  # empty dictionary
  monthstr2data = collections.OrderedDict()

  # fill dict with data for each month
  for i, m in enumerate(months):
      b0 = data[i::12,:,:]
      monthstr2data[m] = data[i::12,:,:]

  data2 = [np.ma.average(i, axis=(1,2)) for i in monthstr2data.values()]

  bp = plt.boxplot(
      data2,
      labels=monthstr2data.keys(),
      #notch=True,
      whis='range', # force whiskers to min/max range instead of quartiles
      showfliers=False,
      patch_artist=True,
      boxprops=dict(facecolor=facecolor, alpha=.25),
      whiskerprops=dict(color=facecolor),
      capprops=dict(color=facecolor)
  )
  plt.ylabel(units)
  plt.title("{} for CMT {}, averaged spatially ".format(var, cmtnum))
  plt.show(block=True)


def boxplot_by_pft(var, timestep, cmtnum, stages, ref_veg_map, ref_run_status):
  '''
  Work in progress...
  '''

  data, units = stitch_stages(var, timestep, stages)
  print "data size:", data.size
  print data.shape

  d2 = data
  # d2 = sum_across_compartments(data)
  # print "data size after summing compartments:", d2.size

  d3 = mask_by_cmt(d2, cmtnum, ref_veg_map)
  print "data size after masking cmt:", d3.count()

  d3 = mask_by_failed_run_status(d3, ref_run_status)
  print "data count after masking run status:", d3.count()

  pft0avg = np.ma.average(d3, axis=(2,3))
  #plt.plot(pft0avg) # Line plot
  plt.boxplot(
      pft0avg,
      labels = ["PFT {}".format(i) for i in range(0, 10)],
      whis='range',
      showfliers=False,
      patch_artist=True,
      boxprops=dict(color='blue', alpha=0.25),
      whiskerprops=dict(color='red'),
      capprops=dict(color='blue'),
  )
  plt.ylabel(units)
  plt.show(block=True)






'''
a = np.zeros((3,2,2))
b = np.ones((2,2,2))
np.concatenate((a,b), axis=0)
'''




'''
# Make a 3x3 array of random data (2D)
>>> m = np.random.randint(0, 100, (3,3))
array([[90, 49, 44],
       [99, 43, 28],
       [65, 50, 26]])


# Mask off some arbitrary part of it
>>> m2 = np.ma.masked_inside(m, 40,60)
masked_array(data =
 [[90 -- --]
 [99 -- 28]
 [65 -- 26]],
             mask =
 [[False  True  True]
 [False  True False]
 [False  True False]],
       fill_value = 999999)

# Make a 3D array of random data
>>> d = np.random.randint(2, 100, (4,3,3,))
array([[[44, 79, 17],
        [36, 91, 68],
        [95, 41, 28]],

       [[97, 35, 41],
        [39, 28, 19],
        [60, 61,  5]],

       [[62, 64, 59],
        [81, 33, 79],
        [45, 76, 85]],

       [[18,  6, 30],
        [23, 81, 46],
        [28, 56, 27]]])

# Broadcast my 2D mask out to the 3rd dimension
>>> m3 = np.broadcast_to(m2.mask, d.shape)
array([[[False,  True,  True],
        [False,  True, False],
        [False,  True, False]],

       [[False,  True,  True],
        [False,  True, False],
        [False,  True, False]],

       [[False,  True,  True],
        [False,  True, False],
        [False,  True, False]],

       [[False,  True,  True],
        [False,  True, False],
        [False,  True, False]]], dtype=bool)

# Make a big 'ol masked array
>>> dm3 = np.ma.masked_array(d, m3)
masked_array(data =
 [[[44 -- --]
  [36 -- 68]
  [95 -- 28]]

 [[97 -- --]
  [39 -- 19]
  [60 -- 5]]

 [[62 -- --]
  [81 -- 79]
  [45 -- 85]]

 [[18 -- --]
  [23 -- 46]
  [28 -- 27]]],
             mask =
 [[[False  True  True]
  [False  True False]
  [False  True False]]

 [[False  True  True]
  [False  True False]
  [False  True False]]

 [[False  True  True]
  [False  True False]
  [False  True False]]

 [[False  True  True]
  [False  True False]
  [False  True False]]],
       fill_value = 999999)

'''
