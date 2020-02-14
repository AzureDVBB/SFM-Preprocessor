#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  2 15:23:49 2020

@author: AzureDVBB

A collection of functions to select images from sequences such as video.
"""

# standard library
from typing import List, Optional, Iterable, Union
import timeit
import warnings
import math

# installed library
from dask import compute
import matplotlib.pyplot as plt

# local library
from io_module import test_video_length, read_video
from analysis_module import (image_descriptors, laplace_sharpness_estimate,
                             base_match_descriptors_parallel)


def plot_results(similarity_estimate: Iterable[Union[float, int]],
                 sharpness_estimate: Iterable[Union[float, int]],
                 goodness_estimate: Iterable[Union[float, int]],
                 index_start: int, selected_index: int,
                 avg_sharp: Optional[float] = None, avg_sim: Optional[float] = None,
                 extra_goodness_label: Optional[str] = '') -> None:
    """
    Plots the sharpness and similarity estimates as well as other relevant data
    used during selection, and selected image index is drawn. Useful for debugging
    selection processes during development.

    Parameters
    ----------
    similarity_estimate : Iterable[Union[float, int]]
        List of image silimarity to base.
    sharpness_estimate : Iterable[Union[float, int]]
        List of sharpness estimate of each image.
    goodness_estimate : Iterable[Union[float, int]]
        List of 'goodness' estimate for each image.
    index_start : int
        Starting point of the plot X axis.
    selected_index : int
        Selected frame index in list, vertical bar drawn here.
    avg_sharp : Optional[float], optional
        Average sharpness value, horizontal bar is drawn to indicate.
        The default is None
    avg_sim : Optional[float], optional
        Average similarity value, horizontal bar is drawn to indicate.
        The default is None
    extra_goodness_label : Optional[str], optional
        Extra description added to the goodness graph label in the plot legend.
        The default is ''

    Returns
    -------
    None

    """

    indexes = list(range(index_start, index_start + len(goodness_estimate)))
    norm_goodness = [i * (1/max(goodness_estimate)) for i in goodness_estimate]

    plt.figure(figsize=(20, 10))

    plt.plot(indexes, norm_goodness, color='black',
             label="'Goodness' estimate " + extra_goodness_label)
    norm_sim = [i * (1/max(similarity_estimate)) for i in similarity_estimate]
    plt.plot(indexes, norm_sim, color='blue', label="similarity estimate", linestyle='dotted')

    if not avg_sim is None:
        plt.axhline(y=avg_sim, color='blue', linestyle='dotted', label=' - weighted average')

    norm_sharp = [i * (1/max(sharpness_estimate)) for i in sharpness_estimate]
    plt.plot(indexes, norm_sharp, color='green', label="sharpness estimate", linestyle='dotted')

    if not avg_sharp is None:
        plt.axhline(y=avg_sharp, color='green', linestyle='dotted', label=' - weighted average')

    plt.axvline(x=index_start + selected_index, color='red', label='picked frame')

    plt.legend()
    plt.xlabel('image indexes')
    plt.ylabel("normalized values")
    plt.show()



def simple_select(similarity_estimate: Iterable[Union[float, int]],
                  sharpness_estimate: Iterable[Union[float, int]],
                  debug_plotting: bool = False, debug_plot_index_start: int = 0) -> int:
    """
    Picks the best image index using an extremely simple selection process.
    It calulatesa 'goodness' estimate by Sharpness / Keypoints and then
    returning the index of the maximum value.

    Parameters
    ----------
    similarity_estimate : Iterable[Union[float, int]]
        List containing how similar images are to a base image.
    sharpness_estimate : Iterable[Union[float, int]]
        List containing an estimate of how sharp an image is.
    debug_plotting : bool, optional
        Wether to plot the results using matplotlib.
        The default is False
    debug_plot_index_start : int, optional
        The starting number on the X axis on plotted results.
        The default is 0

    Returns
    -------
    best_fit_index : int
        The list index of maximum 'goodness' estimate value.

    """

    goodness_estimate = [sharp / keyp for keyp, sharp in zip(similarity_estimate,
                                                             sharpness_estimate)]
    best_fit_index = goodness_estimate.index(max(goodness_estimate))

    if debug_plotting:
        plot_results(similarity_estimate, sharpness_estimate, goodness_estimate,
                     debug_plot_index_start, best_fit_index,
                     extra_goodness_label='(higher is better)')

    return best_fit_index



def normalized_mse_select(similarity_estimate: Iterable[Union[float, int]],
                          sharpness_estimate: Iterable[Union[float, int]],
                          similarity_avg_percent: float = 0.2, sharpness_avg_percent: float = 0.15,
                          debug_plotting: bool = False, debug_plot_index_start: int = 0) -> int:
    """
    Picks best image index using the normalized values of Keypoint matches and Sharpness estimate,
    then calculating the average of the top X% of their values. Using that it calculates the
    mean square error of both Keypoint matches and Sharpness estimate and adding them together
    to form the 'goodness' estimate, then returns the index of the lowest value of this metric.

    Parameters
    ----------
    similarity_estimate : Iterable[Union[float, int]]
        List containing how similar images are to a base image.
    sharpness_estimate : Iterable[Union[float, int]]
        List containing an estimate of how sharp each image is.
    similarity_avg_percent : float, optional
        Percentage of the highest values to include in average calculation of similarity estimate.
        The default is 0.2
    sharpness_avg_percent : float, optional
        Percentage of the highest values to include in average calculation of sharpness estimate.
        The default is 0.15
    debug_plotting : bool, optional
        Wether to plot the results using matplotlib. The default is False.
    debug_plot_index_start : int, optional
        The starting number on the X axis on plotted results. The default is 0.

    Returns
    -------
    best_fit_index : int
        The list index of minimum 'goodness' estimate value

    """

    # average
    norm_sim = [i * (1/max(similarity_estimate)) for i in similarity_estimate]
    norm_sharp = [i * (1/max(sharpness_estimate)) for i in sharpness_estimate]

    # average of the X% highest value elements
    sim_percentile_index = math.ceil(len(norm_sim)*similarity_avg_percent)
    sim_avg_highest = sum(sorted(norm_sim, reverse=True)[:sim_percentile_index]) / sim_percentile_index

    # average of the X% highest value elements
    sharpness_percentile_index = math.ceil(len(norm_sharp)*sharpness_avg_percent)
    sharpness_highest = sorted(norm_sharp, reverse=True)[:sharpness_percentile_index]
    sharpness_avg_highest = sum(sharpness_highest) / sharpness_percentile_index
    goodness_estimate = [(sharp - sharpness_avg_highest)**2 +
                         (keyp - sim_avg_highest)**2 for sharp, keyp in zip(norm_sharp, norm_sim)]

    best_fit_index = goodness_estimate.index(min(goodness_estimate))

    if debug_plotting:
        plot_results(similarity_estimate, sharpness_estimate, goodness_estimate,
                     debug_plot_index_start, best_fit_index,
                     avg_sharp=sharpness_avg_highest, avg_sim=sim_avg_highest,
                     extra_goodness_label='(lower is better)')

    return best_fit_index



# IDEA: New video selection algorithm
#     Go through entire video, estimate each frame's sharpness.
#     For each frame sharpness, select the highest X% from around it (like 60 frames ahead and behind).
#     Check similarity of the selected frames and remove too similar ones.
#     Return the now sharpest and not too similar images as list.



def video_selection(fpath: str, n_workers: int = 2, max_keypoints: int = 1000, chunk_size: int = 25,
                    min_distance: int = 5, max_distance: int = 60, image_count: Optional[int] = None,
                    start_index: int = 0, end_index: Optional[int] = None,
                    similarity_percentile: float = 0.2, sharpness_percentile: float = 0.15,
                    debug_msg: bool = True, debug_plots: bool = False) -> List[int]:
    """

    Parameters
    ----------
    fpath : str
        Absolute path to video file
    n_workers : int, optional
        Number of worker processes (only put as many as you have CPU cores, or threads-2).
        The default is 2
    max_keypoints : int, optional
        Maximum number of keypoint descriptors per video frame (image).
        The default is 1000
    chunk_size : int, optional
        Number of video frames (images) to load into memory at once before they are analyzed.
        LOWERing this will mean LESS RAM being used. Try to keep it at n_workers*2 for
        optimal speed.
        The default is 25
    min_distance : int, optional
        Ignores this many video frames (images) from the last selected index each round.
        The default is 5
    max_distance : int, optional
        Check up to this many video frames (images) from the last selected index each round.
        The default is 60
    image_count : Optional[int], optional
        The video file contains this many images (frames). This is mainly used for debug
        messages and if video ends prematurely will cause no errors. If not supplied, video
        will have it's number of frames counted accurately and that will take several seconds
        if not minutes on very large videos.
        The default is None.
    start_index : int, optional
        Begin running from this frame index. Useful when resuming previous run or when only a
        specific portion of the video is required. The default is 0.
    end_index : Optional[int], optional
        Stop running at this frame index. Useful when only a portion if the video is required.
        The default is None
    similarity_percentile : float, optional
        Only average this percentage of the highest values of similarity estimate during selection.
        Where 1 is 100% and 0 is 0% (please keep it in range of 0,1 like 1>X>0 ).
        The default is 0.2
    sharpness_percentile : float, optional
        Only average this percentage of the highest values of sharpness estimate during selection.
        Where 1 is 100% and 0 is 0% (please keep it in range of 0,1 like 1>X>0 ).
        The default is 0.15
    debug_msg : bool, optional
        Print out debug messages during function run, very useful to not go insane waiting.
        The default is True
    debug_plots : bool, optional
        Use matplotlib to plot out graphs each time a new video frame (image) is selected.
        The plots show normalized values, sharpness and similarity estimate, their used averages,
        the 'goodness' estimate of each video frame (image) and the picked index.
        Useful for developing new selection functions and evaluating them.
        The default is False

    Raises
    ------
    StopIteration
        Premature end of video file. Program will continue to run and not fail.

    Returns
    -------
    List[int]
        List of (integer) indexes where the function has selected 'good' video frames (images).

    """

    # critical error checking and warnings
    if end_index is not None:
        assert start_index < end_index, "start index is greater then the end index"
    assert min_distance < max_distance, "min distance greater then max distance"

    if chunk_size <= n_workers*2:
        warnings.warn(f"Chunk size is less then twice the worker process count. "
                      f"Performace will suffer.")

    if max_distance - min_distance > 400:
        warnings.warn(f"The frames to select from is set via min/max distance over [400] "
                      f"and this might affect results as this will only pick the single best "
                      f"from them.")

    if debug_msg:
        start_time = timeit.default_timer()
        print(f'Starting simple selection from video frames.')

    # count frames in video if no count supplied
    if image_count is None:
        if debug_msg:
            print(f'No image count supplied, starting accurate image count.')
        tmp_start_time = timeit.default_timer()
        image_count = test_video_length(fpath, debug=debug_msg)
        if debug_msg:
            print(f'[{image_count}] images counted in '
                  f'({round(timeit.default_timer() - tmp_start_time, 2)} s)')

    if debug_msg:
        print(f'Starting analysis and selection of [{image_count}] images')

    reader_end = False

    reader = read_video(fpath, dask_array=True)
    reader_index = 0
    if debug_msg:
        print(f'**** Seeking to start index [{start_index}]')
    # seek to start index
    for _ in range(start_index - 1):
        next(reader)
        reader_index += 1
    # set up base image descriptors to match to
    base_descriptor = image_descriptors(next(reader))
    base_index = reader_index
    reader_index += 1

    if debug_msg:
        print(f'#### Seeking finished')
    # init global vars in function
    img_buffer = []
    desc_buffer = []
    sharp_buffer = []
    selected_indexes = []

    # run untill out of frames or at end index
    while not reader_end:

        if debug_msg:
            print(f'>><< Starting to fill image buffer with a maximum of [{chunk_size}] images')
            tmp_start_time = timeit.default_timer()
        # try and fill Frame buffer from video
        while len(img_buffer) < chunk_size and (len(img_buffer) + len(desc_buffer) <
                                                max_distance - min_distance):
            try:
                if reader_index <= base_index + min_distance:
                    next(reader)
                else:
                    img_buffer.append(next(reader))
                reader_index += 1
                if end_index is not None and reader_index >= end_index:
                    raise StopIteration
            except StopIteration:
                reader_end = True
                break
            except:
                raise

        if debug_msg:
            print(f'<<>> Buffered [{len(img_buffer)}] images in '
                  f'({round(timeit.default_timer() - tmp_start_time, 3)} s)')
            print(f'++++ Starting keypoint descriptor extraction and sharpness estimation of '
                  f'[{len(img_buffer)}] images in buffer')
            tmp_start_time = timeit.default_timer()

        # calculate sharpness and descriptors for the buffer images with dask, purge buffer
        desc = [image_descriptors(img, max_keypoints, delay=True) for img in img_buffer]
        sharp = [laplace_sharpness_estimate(img, delay=True) for img in img_buffer]

        del img_buffer
        img_buffer = []

        desc = compute(desc, scheduler='processes', num_workers=n_workers)[0]
        desc_buffer.extend(desc)
        del desc

        sharp = compute(sharp, scheduler='processes', num_workers=n_workers)[0]
        sharp_buffer.extend(sharp)
        del sharp

        if debug_msg:
            print(f'---- Finished extraction, sharpness estimate and purged image buffer in'
                  f' ({round(timeit.default_timer() - tmp_start_time, 3)} s)')

        if len(desc_buffer) >= max_distance - min_distance or reader_end:
            if debug_msg:
                print(f'>>>> Selecting best fit from [{len(desc_buffer)}] images '
                      f'with base index [{base_index}]')
                tmp_start_time = timeit.default_timer()
                print(f"++++ Matching [{len(desc_buffer)}] image's descriptors to base...")

            # calculate similarity to base image
            matches = base_match_descriptors_parallel(base_descriptor, desc_buffer,
                                                      workers=n_workers)
            if debug_msg:
                print(f'---- Matching finished in '
                      f'({round(timeit.default_timer() - tmp_start_time, 3)} s)')

            # select best fit index
            selected_idx_rel = normalized_mse_select(matches, sharp_buffer,
                                                     debug_plotting=debug_msg,
                                                     debug_plot_index_start=base_index)
            selected_idx = selected_idx_rel + base_index + min_distance
            if debug_msg:
                print(f'<<<< Found best fit image at index [{selected_idx}] of '
                      f'[{image_count if end_index is None else end_index}] total images')
            selected_indexes.append(selected_idx)

            # set new base, remove unneeded data (sharpness and descriptors bellow base index)
            base_index = selected_idx
            base_descriptor = desc_buffer[selected_idx_rel]

            deletion_end = selected_idx_rel + 1 + min_distance
            deletion_end = deletion_end if deletion_end <= len(desc_buffer) else len(desc_buffer)
            del matches
            del desc_buffer[:deletion_end]
            del sharp_buffer[:deletion_end]

        elif debug_msg:
            print(f'<><> [{len(desc_buffer)}/{max_distance - min_distance}] '
                  f'images ready for selection, continuing....')

    if debug_msg:
        print(f'!!!! End of file, successfully picked {len(selected_indexes)} images'
              f' out of [{image_count}] in ({round(timeit.default_timer() - start_time, 3)} s)')

    return selected_indexes
