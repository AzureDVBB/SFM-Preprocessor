#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan 26 11:40:13 2020

@author: AzureDVBB

A collection of functions to analyze image data.
"""

# standard library
from typing import Union, List, Iterable
import warnings

# installed library
from skimage.feature import ORB, match_descriptors as match, canny
from skimage.color import rgb2gray
from skimage.metrics import structural_similarity as ssim
from skimage.filters import laplace, gaussian
from dask import delayed, compute
from dask.delayed import Delayed # for typing only
from numpy import ndarray # for typing only
import numpy as np




def blur_image(image: ndarray, strength: float = 1) -> ndarray:
    """
    Applies gaussian blur to an image with a set strength

    Parameters
    ----------
    image : ndarray
        Input image array to be blurred.
    strength : float, optional
        The strength of the applied gaussian blur.
        The default is 1

    Returns
    -------
    ndarray
        Blurred input image.

    """

    return gaussian(image, multichannel=not test_image_grayness(image), sigma=strength)


def test_image_grayness(image: ndarray) -> bool:
    """
    Tests if an image is grayscale.

    Parameters
    ----------
    image : ndarray
        Input image array.

    Returns
    -------
    bool
        True if grayscale and False if not.

    """

    return bool(np.shape(image)[2] == 1)


def gray(image: ndarray) -> ndarray:
    """
    Converts RGB images to grayscale if it's not allready.

    Parameters
    ----------
    image : ndarray
        Input image array, must be either RGB or grayscale.

    Raises
    ------
    Exception
        Image can only be grayscale or RGB, having more or less color channels then 1 or 3
        is unsupported.

    Returns
    -------
    ndarray
        Grayscale input image.

    """

    if test_image_grayness(image):
        return image
    elif np.shape(image)[2] == 3:
        return rgb2gray(image)
    else:
        raise Exception("Image was not grayscale, neither did it have 3 color channels. "
                        "This only supports rgb conversion.")


def image_descriptors(image: ndarray, num_keypoints: int = 500,
                      delay: bool = False) -> Union[ndarray, Delayed]:
    """
    Calculates and image's keypoint descriptors.

    Parameters
    ----------
    image : ndarray
        Input image ndarray. Can be either grayscale or RGB.
    num_keypoints : int, optional
        Maximum number of keypoints and descriptors to calculate.
        The default is 500
    delay : bool, optional
        If set will returned a Dask Delayed object of the computation.
        The default is False

    Returns
    -------
    Union[ndarray, Delayed]
        Image keypoint descriptors.

    """

    if delay:
        orb = ORB(n_keypoints=num_keypoints)
        orb.detect_and_extract(gray(image))
        return orb.descriptors

    orb = ORB(n_keypoints=num_keypoints)
    orb.detect_and_extract(gray(image))
    return orb.descriptors


def match_descriptors(desc1: ndarray, desc2: ndarray, delay: bool = False) -> Union[int, Delayed]:

    """
    Matches two image descriptors and returns the number of matches.

    Parameters
    ----------
    desc1 : ndarray
        Image keypoint descriptors.
    desc2 : ndarray
        Image keypoint descriptors.
    delay : bool, optional
        Wrap the function into dask Delayed object for later computation.
        The defailt is False

    Returns
    -------
    Union[int, Delayed]
        Number of matches between the two image keypoint descriptors.

    """

    if delay:
        return delayed(len)(delayed(match)(desc1, desc2))
    else:
        return len(match(desc1, desc2))


def match_images(image1: ndarray, image2: ndarray,
                 max_keypoints: int = 500, delay: bool = False) -> Union[int, Delayed]:
    """
    Extracts and matches two images' keypoint descriptors, returning the number of matches.

    Parameters
    ----------
    image1 : ndarray
        Input Image array.
    image2 : ndarray
        Input Image array.
    max_keypoints : int, optional
        Maximum number of image keypoints to use.
        The default is 500
    delay : bool, optional
        Wrap the internal computation into a dask Delayed object for later computation.
        The default is False

    Returns
    -------
    int
        Number of keypoint descriptor matches.

    """
    if delay:
        desc1 = delayed(image_descriptors)(image1, max_keypoints)
        desc2 = delayed(image_descriptors)(image2, max_keypoints)
        matches = delayed(match_descriptors)(desc1, desc2)
        return delayed(len)(matches)

    else:
        desc1 = image_descriptors(image1, max_keypoints)
        desc2 = image_descriptors(image2, max_keypoints)
        matches = match_descriptors(desc1, desc2)
        return len(matches)


def ssim_images(image1: ndarray, image2: ndarray) -> float:
    """
    Calculates two image's structural similarity.

    Parameters
    ----------
    image1 : ndarray
        Input Image array.
    image2 : ndarray
        Input Image array.

    Raises
    ------
    Warning
        One image is color the other is GRAYSCALE, converting color to grayscale and continuing.
    Exception
        Images have different number of color channels, this is unsupported.

    Returns
    -------
    float
        The similarity of the two images.

    """

    is_gray1 = test_image_grayness(image1)
    is_gray2 = test_image_grayness(image2)
    if is_gray1 is not is_gray2:
        warnings.warn(f'IMAGE1 input is {"gray scale" if is_gray1 else "multichannel"} '
                      f'while IMAGE2 input is {"gray scale" if is_gray2 else "multichannel"}. '
                      f'This is unsupported, converting both to grayscale, '
                      f'there may be some precision loss.')
        if not is_gray1:
            image1 = gray(image1)
            is_gray1 = True
        if not is_gray2:
            image2 = gray(image2)
            is_gray2 = True

    elif np.shape(image1)[2] != np.shape(image2)[2]:
        raise Exception(f'Input images are multichannel and have different amount of color channels'
                        f', this is unsupported')

    return ssim(image1, image2, multichannel=is_gray1)


def pivot_match_descriptors(descriptors: Iterable[ndarray],
                            pivot_index: int = 0) -> List[Union[int, None]]:
    """
    Matches each element in the input list of keypoint descriptors to the one at its pivot index.
    Returning a list containing the number of matches to the pivot.

    Parameters
    ----------
    descriptors : Iterable[ndarray]
        List of keypoint descriptors.
    pivot_index : int, optional
        Index in the descriptor list to match each other element to.
        The default is 0

    Returns
    -------
    List[Union[int, None]]
        Number of keypoint descriptor matches to each other element in the list.

    """

    matches = []
    base = descriptors[pivot_index]
    for i, desc in enumerate(descriptors):
        if i != pivot_index:
            matches.append(len(match_descriptors(base, desc)))
        else:
            matches.append(None)

    return matches


def base_match_descriptors_parallel(base_desc: ndarray, descriptors: Iterable[ndarray],
                                    workers: int = 2) -> List[int]:
    """
    Matches a single base keypoint descriptors to a list of them, returning the number of matches.
    This variant is using dask library to parallelize it with many worker processes.

    Parameters
    ----------
    base_desc : ndarray
        Base keypoint descriptors to match to.
    descriptors : Iterable[ndarray]
        The list of image keypoint descriptors to match against.
    workers : int, optional
        Number of dask worker processes.
        The default is 2

    Returns
    -------
    List[int]
        Keypoint descriptor matches number.

    """

    matches_delayed = [match_descriptors(base_desc, desc, delay=True) for desc in descriptors]
    return compute(matches_delayed, scheduler='processes', num_workers=workers)[0]


def pivot_match_images_parallel(images: Iterable[ndarray], pivot_index: int = 0,
                                max_keypoints: int = 500, workers: int = 2) -> List[int]:
    """
    Matches an entire list of input image arrays against the image at a specific index and returns
    the number of keypoint matches. This is a parralellized version.

    Parameters
    ----------
    images : Iterable[ndarray]
        List of input image arrays, that was loaded into memory.
    pivot_index : int, optional
        Image list index to match every other image to.
        The default is 0
    max_keypoints : int, optional
        Max number of keypoints for each image to be used.
        The default is 500
    workers : int, optional
        Number of dask worker processes to use in parallel.
        The default is 2

    Returns
    -------
    List[int]
        Number of keypoint matches.

    """

    matches = []
    base = images[pivot_index]
    for i, img in enumerate(images):
        if i != pivot_index:
            matches.append(match_images(base, img, max_keypoints, delay=True))
        else:
            matches.append(None)
    return compute(matches, scheduler='processes', num_workers=workers)[0]


def pivot_match_images(images: Iterable[ndarray], pivot_index: int = 0,
                       max_keypoints: int = 500) -> List[int]:
    """
    Matches an entire list of input image arrays against the image at a specific index and returns
    the number of keypoint matches.

    Parameters
    ----------
    images : Iterable[ndarray]
        List of input image arrays, that was loaded into memory.
    pivot_index : int, optional
        Image list index to match every other image to.
        The default is 0
    max_keypoints : int, optional
        Max number of keypoints for each image to be used.
        The default is 500

    Returns
    -------
    List[int]
        Number of keypoint matches for each image.

    """

    matches = []
    base = images[pivot_index]
    for i, img in enumerate(images):
        if i != pivot_index:
            matches.append(match_images(base, img, max_keypoints))
        else:
            matches.append(None)
    return matches


def pivot_structural_similarity_parallel(images: Iterable[ndarray], pivot_index: int = 0,
                                         workers: int = 2) -> List[float]:
    """
    Calculates the the structural similarity of each image in the list to a single
    image at a given base index of the list. This one uses dask to run in parallel on
    several worker processes.

    Parameters
    ----------
    images : Iterable[ndarray]
        List of image arrays loaded into memory.
    pivot_index : int, optional
        List index to match each other element to.
        The default is 0
    workers : int, optional
        Number of worker processes to use.
        The default is 2

    Returns
    -------
    List[float]
        How similar each image is to the base image.

    """

    is_gray = [test_image_grayness(i) for i in images]
    if True in is_gray and False in is_gray:
        warnings.warn(f'There are grayscale and multicolor images in list, converting'
                      f' all to grayscale to avoid errors.')
        images = [gray(i) for i in images]
        is_gray = True

    sim = []
    base = images[pivot_index]
    for i, img in enumerate(images):
        if i != pivot_index:
            sim.append(delayed(ssim)(base, img, multichannel=not is_gray))
        else:
            sim.append(None)

    return compute(sim, scheduler='processes', num_workers=workers)[0]


def laplace_sharpness_estimate(image: ndarray, delay: bool = False) -> Union[float, Delayed]:
    """
    Runs a laplacian filter on the input image (edge detector) and returns its variance.
    This is used to estimate sharpness. (higher is sharper)

    Parameters
    ----------
    image : ndarray
        Image array loaded into memory.
    delay : bool, optional
        Wraps the function computations into a dask Delayed object for later computation.
        The default is False

    Returns
    -------
    Union[float, Delayed]
        Laplacian variance of the input image, used to estimate image sharpness.

    """
    # NOTE:
    # There is an article using Support-Vector-Machine using both variance
    # and maxximum of the laplacian, might be worth looking into

    if not delay:
        return laplace(gray(image)).var()
    elif delay:
        return laplace(delayed(gray)(image)).var()


def canny_sharpness_estimate(image: ndarray) -> float:
    """
    Runs Canny edge detection on the input image and returns its variance.
    This is a rough estimate of image sharpness. (higher is sharper)

    Parameters
    ----------
    image : ndarray
        Input image array loaded into memory.

    Returns
    -------
    float
        Variance of the canny edge detectiion, sharpness estimate.

    """

    return canny(gray(image)).var()
