#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 18 12:28:03 2020

@author: AzureDVBB

A collection of fuctions to read and write image data.
"""



# standard library
from typing import Generator, List, Tuple
import os
from os import path
import timeit

# installed library
from skimage.io import imread, imread_collection as read_collection, imsave, ImageCollection
from dask import array as da
import imageio
from numpy import ndarray



def read_image(fpath: str, as_gray: bool = False, dask_array: bool = False) -> ndarray:
    """
    Reads an image from disk into memory and returns it.

    Parameters
    ----------
    fpath : str
        Absolute file path.
    as_gray : bool, optional
        Load image as grayscale (luminance only).
        The default is False
    dask_array : bool, optional
        Return the loaded image as a dask array, instead of a numpy array.
        The default is False

    Returns
    -------
    ndarray
        Array of the image loaded into memory.

    """

    if dask_array:
        return da.from_array(imread(fpath, as_gray))
    return imread(fpath, as_gray)


def read_folder(fpath: str, ftypes: Tuple[str, ...] = None,
                conserve_memory: bool = True) -> ImageCollection:
    """
    Reads the images in a specific folder.

    Parameters
    ----------
    fpath : str
        Path of folder containing the images.
    ftypes : Tuple[str, ...], optional
        Only read files of this type. e.g.: '.jpg', '.png', ...
        The default is None
    conserve_memory : bool, optional
        Load as needed and not destroy your RAM?
        The default is True

    Raises
    ------
    path
        Exception is raised when the read directory does not exist

    Returns
    -------
    ImageCollection
        A list like structure where accessing each element causes a file read
        operation.

    """

    if not path.isdir(fpath):
        raise NotADirectoryError(f'{path} does not exist')

    folder_contents = os.listdir(fpath)
    if ftypes is not None:
        folder_images = []

        for content in folder_contents:
            if content.endswith(ftypes):
                folder_images.append(content)

        images_path = []
        for _fi in folder_images:
            images_path.append(path.join(fpath, _fi))

        return read_collection(images_path, conserve_memory)

    else:
        files_path = []
        for _f in os.listdir(fpath):
            files_path.append(path.join(fpath, _f))

        return read_collection(files_path, conserve_memory)


def save_image(image: ndarray, fpath: str, fname: str, overwrite: bool = True) -> None:
    """
    Saves an image to a file.

    Parameters
    ----------
    image : ndarray
        Raw ndarray of an image loaded into memory by read_image().
    fpath : str
        Path of the folder to save the file to.
    fname : str
        Name of the file.
    overwrite : bool, optional
        To overwrite a file with that name, if it exists already.
        The default is True

    Raises
    ------
    FileExistsError
        Only if overwrite is set to FALSE and file already exists.

    Returns
    -------
    None.

    """

    if not os.path.isdir:
        os.mkdir(fpath)
    file_path = os.path.join(fpath, fname)
    if os.path.isfile(file_path + '.png') and not overwrite:
        raise FileExistsError(file_path + '.png')
    imsave(file_path + '.png', image)


def read_video(fpath: str, uint16: bool = False,
               dask_array: bool = False) -> Generator[ndarray, None, None]:
    """
    Reads a video file and returns a generator object to load each video frame into memory lazily.

    Parameters
    ----------
    fpath : str
        Absolute path of video file.
    uint16 : bool, optional
        Request video frames to be loaded in as uint16 array instead of uint8 if able.
        The default is False
    dask_array : bool, optional
        Return dask array object instead of a numpy array.
        The default is False

    Yields
    ------
    Generator
        Yields image ndarrays sequentially as the video file is read.

    """

    reader = imageio.get_reader(fpath, 'ffmpeg', dtype='uint16' if uint16 else 'uint8')
    for frame in reader:
        if dask_array:
            yield da.from_array(frame)
        else:
            yield frame


def test_video_length(fpath: str, accurate: bool = True, debug: bool = True) -> int:
    """
    Tests the video file length in video frames, returning it's count. It may take a minute or more.

    Parameters
    ----------
    fpath : str
        Absolute path of video file.
    accurate : bool, optional
        Decode and count each video frame,
        instead of reading it via library which is +- 1s worth of frames.
        The default is True
    debug : bool, optional
        Print debug messages onto the console.
        The default is True

    Returns
    -------
    int
        Total count of video frames.

    """

    if not accurate:
        count = imageio.get_reader(fpath, 'ffmpeg').count_frames()
        return int(count)

    elif accurate:
        index = 0
        for _ in read_video(fpath):
            index += 1
            if debug and index%500 == 0:
                print(f'{index} frames counted')
        return index


def save_video_frames(fpath: str, output_folder_path: str, frame_indexes: List[int],
                      debug_msg: bool = True, overwrite: bool = False,
                      padding_zeros: bool = True) -> None:
    """
    Saves select frames of a video file by index onto disk.

    Parameters
    ----------
    vpath : str
        Path of the video to save frames from.
    output_folder_path : str
        Path to the folder to save the images to.
    frame_indexes : List[int]
        List of integers, frame indexes to save.
    debug_msg : bool, optional
        Allow debug message printing.
        The default is True
    overwrite : bool, optional
        Overwrite files of the same name in target folder?.
        The default is False
    padding_zeros : bool, optional
        Pad out the file name beginning with 0's or just use indexes as names.
        The default is True

    Returns
    -------
    None.

    """

    if debug_msg:
        print(f'>>>> Saving {len(frame_indexes)} images to disk at "{output_folder_path}"')
        start_time = timeit.default_timer()

    curr_index = 0
    max_index = max(frame_indexes)
    for frame in read_video(fpath):
        if curr_index in frame_indexes:
            if debug_msg:
                temp_start_time = timeit.default_timer()

            name = str(curr_index).zfill(len(str(max_index))) if padding_zeros else str(curr_index)
            save_image(frame, output_folder_path, name, overwrite)

            if debug_msg:
                timed = str(round(timeit.default_timer() - temp_start_time, 3))
                while len(timed) < 5:
                    timed += "0"
                print(f'><>< Finished saving "{name}.png" in ({timed}s) '
                      f' ...  [{frame_indexes.index(curr_index) + 1} / {len(frame_indexes)}] done')

        curr_index += 1
        if curr_index > max_index:
            break

    if debug_msg:
        print(f'<<<< Images saved successfully at "{output_folder_path}" in '
              f'({round(timeit.default_timer() - start_time, 3)}s)')
