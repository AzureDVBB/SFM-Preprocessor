# -*- coding: utf-8 -*-

import os
import time
import multiprocessing as mp

import PySimpleGUI as sg

from using_skimage.io_module import test_video_length, save_video_frames
from selection_module import video_selection


def integer_input_sanitizer(input_string : str, min_value : int, max_value : int) -> str:
    assert min_value <= max_value, "min value MUST be less then max value"

    # weed out invalid integer characters
    valid_character_pool = ""
    for c in input_string[:len(str(max_value)) + 1]: # ensure we don't go through the works of shakespear
        if c in "0123456789": valid_character_pool += c

    if valid_character_pool == "":
        sanitized = "0"

    else:
        sanitized = valid_character_pool

    sanitized_int = int(sanitized)

    # make sure value is between max/min values
    if sanitized_int < min_value:
        sanitized_int = min_value
    elif sanitized_int > max_value:
        sanitized_int = max_value

    return str(sanitized_int)


def float_input_sanitizer(input_string : str, min_value : float, max_value : float,
                          max_characters : int) -> str:
    assert min_value <= max_value, "min value MUST be less then max value"

    # weed out any rubbish
    valid_character_pool = ""
    for c in input_string[:max_characters + 1]: # ensure we don't have to go through the entire history of bagel
        if c in ".0123456789":
            valid_character_pool += c

    # create float from input string
    if valid_character_pool == '.' or valid_character_pool == '': # special case handling of bad input
        sanitized_input_float = min_value

    elif valid_character_pool.count('.') > 1: # handle multiple dots by excluding excess ones
        split_input = valid_character_pool.split('.', 2)
        sanitized_input_float = float(split_input[0] + '.' + split_input[1])

    else: # general accepted case
        sanitized_input_float = float(valid_character_pool)

    # ensure value is between minimum and maximum
    if sanitized_input_float > max_value:
        sanitized_input = str(max_value)

    elif sanitized_input_float < min_value:
        sanitized_input = str(min_value)

    else: sanitized_input = str(sanitized_input_float)

    # remove excess characters from sanitized_input and return the result
    if len(sanitized_input) > max_characters:
        sanitized_input = sanitized_input[:max_characters]

    return sanitized_input


def update_button_colors(window_object):
    # count frames button //////////////////////
    if window_object["__input_error__"].Get().startswith("ERROR"): # not working state due to error
        window_object["__count_frames__"](button_color = button_colors["bad"])
    elif window_object["__count_frames__"].get_text() == "Cancel": # currently running state
        window_object["__count_frames__"](button_color = button_colors["enabled"])
    else: # ready to start, no errors
        window_object["__count_frames__"](button_color = button_colors["good"])

    # start frame selection button /////////////
    if (window_object["__input_error__"].Get().startswith("ERROR") or
        window_object["__output_error__"].Get().startswith("ERROR")):

        window_object["__start_selection__"](button_color = button_colors["bad"])
    elif window_object["__start_selection__"].get_text() == "Cancel": # currently running state
        window_object["__start_selection__"](button_color = button_colors["enabled"])
    else:
        window_object["__start_selection__"](button_color = button_colors["good"])


def toggle_buttons_disabling_during_selection(window_object, disabled : bool):
    # frame selection tab
    window_object["__input_browse__"](disabled=disabled)
    window_object["__output_browse__"](disabled=disabled)
    window_object["__count_frames__"](disabled=disabled)
    # frame writeout tab
    window_object["__csv_browse__"](disabled=disabled)
    window_object["__csv_frames_input_browse__"](disabled=disabled)
    window_object["__csv_frames_output_browse__"](disabled=disabled)
    window_object["__start_writeout__"](disabled=disabled)


def toggle_buttons_disabling_during_writeout(window_object, disabled : bool):
    # frame selection tab
    window_object["__input_browse__"](disabled=disabled)
    window_object["__output_browse__"](disabled=disabled)
    window_object["__count_frames__"](disabled=disabled)
    window_object["__start_selection__"](disabled=disabled)
    # frame writeout tab
    window_object["__csv_browse__"](disabled=disabled)
    window_object["__csv_frames_input_browse__"](disabled=disabled)
    window_object["__csv_frames_output_browse__"](disabled=disabled)


def toggle_input_enable(window_object, disabled: bool = False):
    # frame selection tab
    # window_object["__input_type__"](disabled=disabled) # NOTE: functionality not implemented
    # window_object["__output_type__"](disabled=disabled) # NOTE: functionality not implemented
    window_object["__worker_processes__"](disabled=disabled)
    window_object["__max_distance__"](disabled=disabled)
    window_object["__buffer_size__"](disabled=disabled)
    window_object["__start_index__"](disabled=disabled)
    if not disabled and window_object["__count_frames_info__"].Get().startswith("COUNT"):
        window_object["__end_index__"](disabled=False)
        window_object["__max_features__"](disabled=False)
    else:
        window_object["__end_index__"](disabled=True)
        window_object["__max_features__"](disabled=True)
    window_object["__similarity_percentile__"](disabled=disabled)
    window_object["__sharpness_percentile__"](disabled=disabled)
    # writeout tab
    # window_object["__frames_type__"](disabled=disabled) # NOTE: functionality not implemented


def reset_frame_count(window_object):
    window_object["__count_frames_info__"]("")
    window_object["__start_index__"]("0")
    window_object["__start_index_warning__"]("INFO: Please count frames to enable")
    window_object["__end_index__"]("0")
    window_object["__end_index_warning__"]("INFO: Please count frames to enable")


def write_results_to_csv_file(fpath: str, results: list):
    assert fpath.endswith(".csv"), "Non CSV file recieved. Files must have a '.csv' extension at the end"

    with open(fpath, 'a') as file:
        text_to_write = ''
        for r in results:
            if not r is None:
                text_to_write += f'{r};'
        file.write(text_to_write)
    print(f"written {results} to {fpath}")


def read_results_from_csv_file(fpath: str):
    assert fpath.endswith(".csv"), "Non CSV file recieved. Files must have a '.csv' extension at the end"

    res = []
    with open(fpath, 'r') as file:
        text = file.readline()
        if not all([(c in '0123456789;') for c in text]):
            print("WARNING: invalid characters in CSV file, ignoring those")
        res = [int(n) for n in text.split(';') if (all([(c in '0123456789') for c in n]) and n != '')]
    return res


# Co-Process functions ###########################################################################################

def count_frames(video_path):

    length = test_video_length(video_path)
    return length


def select_frames(values_object, output_q):

    end_index = int(values_object["__end_index__"])

    import signal

    try:
        for frame_idx in video_selection(values_object["__input_source__"],
                                         n_workers=int(values_object["__worker_processes__"]),
                                         max_distance=int(values_object["__max_distance__"]),
                                         buffer_size=int(values_object["__buffer_size__"]),
                                         start_index=int(values_object["__start_index__"]),
                                         end_index=end_index if end_index > 0 else None,
                                         max_keypoints=int(values_object["__max_features__"]),
                                         similarity_percentile=float(values_object["__sharpness_percentile__"]),
                                         sharpness_percentile=float(values_object["__similarity_percentile__"]),
                                         as_generator=True):
            # break out of loop if termination occours
            if signal == signal.SIGTERM:
                break
            output_q.put(frame_idx)
    finally:
        output_q.put(None)


def csv_video_writeout(values_object, output_q):

    for res in save_video_frames(values_object["__csv_frames_input__"],
                                 values_object["__csv_frames_output__"],
                                 read_results_from_csv_file(values_object["__csv_input__"]),
                                 as_generator=True
                                 ):
        output_q.put(res)
    output_q.put(None)


def terminate_coprocess(process_reference):

    process_reference.terminate()
    process_reference.join()
    process_reference.close()


# Main program #################################################################################################
if __name__ == "__main__":

    # definitions ##############################################################################################

    input_types = ("Video File", "Sequential Images")
    input_video_file_types = (("Mpeg 4", "*.mp4"),)
    input_image_file_types = (("JPEG", "*.jpg"), ("PNG", "*.png"), ("BPM", "*.bmp"),)

    output_types = ("CSV File", "Image Files")
    output_file_types = (("CSV File", "*.csv"),)

    csv_file_type = (("CSV File", "*.csv"),)

    button_colors = {"bad" : ("black", "crimson"), "good" : ("black", "limegreen"),
                     "enabled" :  ("black", "white"), "disabled" : ("gray", "lightgray")}

    process_references = {}
    process_results = {}
    process_infos = {}

    # Create Selction GUI layouts and elements #################################################################

    input_layout = [[sg.Text("ERROR: No file selected", key="__input_error__", size=(100,1))
                     ],
                    [sg.Combo(input_types, key="__input_type__", size=(20,1),
                              readonly=True, default_value="Video File", enable_events=True,
                              disabled=True), # TODO: IMPLEMENT THE Image Sequence input type
                     sg.Input(key="__input_source__", enable_events=True, disabled=True, size=(64,1)),
                     sg.FileBrowse(button_text="Browse", key="__input_browse__",
                                   target="__input_source__", file_types=input_video_file_types)
                     ],
                    [sg.Button("Count Frames", key="__count_frames__", button_color=button_colors["bad"],
                               size=(15,1)),
                     sg.Text("", size=(80,1), key="__count_frames_info__")
                     ]
                    ]

    output_layout = [[sg.Text("ERROR: No file selected", key="__output_error__", size=(100,1))
                      ],
                     [sg.Combo(output_types, key="__output_type__", size=(20,1),
                               readonly=True, default_value=output_types[0], enable_events=True,
                               disabled=True), # TODO: IMPLEMENT THE OUTPUT FORMAT OF IMAGES!
                      sg.Input(key="__output_source__", enable_events=True, disabled=True, size=(64,1)),
                      sg.SaveAs(button_text="Browse", key="__output_browse__",
                                target="__output_source__", file_types=output_file_types)
                      ],
                     ]

    options_layout = [[sg.Text("Worker Processes", size=(21,1)),
                       sg.Input(key="__worker_processes__", size=(4,1), default_text="1",
                                enable_events=True),
                       sg.Text("", key="__worker_processes_warning__", size=(71,1))
                       ],
                      [sg.Text("Max Distance (frames)", size=(21,1)),
                       sg.Input(key="__max_distance__", size=(4,1), default_text="100",
                                enable_events=True),
                       sg.Text("", key="__max_distance_warning__", size=(71,1))
                       ],
                      [sg.Text("Buffer Size", size=(21,1)),
                       sg.Input(key="__buffer_size__", size=(4,1), default_text="25",
                                enable_events=True),
                       sg.Text("", key="__chunk_size_warning__", size=(71,1))
                       ],
                      [sg.Text("Start Index", size=(21,1)),
                       sg.Input(key="__start_index__", size=(8,1), default_text="0",
                                enable_events=True, disabled=True),
                       sg.Text("INFO: Please count frames to enable", key="__start_index_warning__", size=(67,1))
                       ],
                      [sg.Text("End Index", size=(21,1)),
                       sg.Input(key="__end_index__", size=(8,1), default_text="0",
                                enable_events=True, disabled=True),
                       sg.Text("INFO: Please count frames to enable", key="__end_index_warning__", size=(67,1))
                       ],
                      ]

    advanced_options_layout = [[sg.Text("Max Features", size=(21,1)),
                                sg.Input(key="__max_features__", size=(4,1),
                                         default_text="400", enable_events=True),
                                sg.Text("", key="__max_features_warning__", size=(71,1))
                                ],
                               [sg.Text("Similarity Percentile", size=(21,1)),
                                sg.Input(key="__similarity_percentile__", size=(4,1),
                                         default_text="0.25", enable_events=True),
                                sg.Text("", key="__similarity_percentile_warning__", size=(71,1))
                                ],
                               [sg.Text("Sharpness Percentile", size=(21,1)),
                                sg.Input(key="__sharpness_percentile__", size=(4,1),
                                         default_text="0.15", enable_events=True),
                                sg.Text("", key="__sharpness_percentile_warning__", size=(71,1))
                                ]
                               ]

    start_selection_layout = [[sg.Button("Start Selection", key="__start_selection__",
                                      button_color=button_colors["bad"], size=(15,1)),
                               sg.Text("", key="__selection_info__", size=(80,1))
                               ],
                              [sg.ProgressBar(100, key="__selection_progress__", size=(101,10))]
                              ]

    selection_layout = [[sg.Frame("Input Data", input_layout)],
                        [sg.Frame("Output Data", output_layout)],
                        [sg.Frame("Options", options_layout)],
                        [sg.Frame("Advanced Options", advanced_options_layout)],
                        [sg.Frame("", start_selection_layout)]
                        ]

    # CSV Frames Writeout ###################################################################################
    csv_writeout_input = [
                          # CSV file input
                          [sg.Text("ERROR: No CSV File selected", key="__csv_input_warning__", size=(100,1))],

                          [sg.Text("CSV File", size=(10,1)),
                           sg.Input(key="__csv_input__", size=(74,1), disabled=True, enable_events=True),
                           sg.FileBrowse(button_text="Browse", key="__csv_browse__",
                                         target="__csv_input__", file_types=csv_file_type)
                           ],
                          # Frames input
                          [sg.Text("ERROR: No Video File selected", key="__csv_frames_input_warning__",
                                   size=(100,1))
                           ],
                          [sg.Combo(values=input_types, default_value=input_types[0], size=(20,1),
                                    readonly=True, enable_events=True, disabled=True,
                                    key="__frames_type__"), #TODO: Implement frames input
                           sg.Input(key="__csv_frames_input__", size=(62,1), disabled=True, enable_events = True),
                           sg.FileBrowse(button_text="Browse", key="__csv_frames_input_browse__",
                                         target="__csv_frames_input__", file_types=input_video_file_types)
                           ]
                          ]

    csv_writeout_output = [[sg.Text("ERROR: No Folder selected", key="__csv_frames_output_warning__",
                                   size=(100,1))
                            ],
                           [sg.Text("Output Folder", size=(15,1)),
                            sg.Input(key="__csv_frames_output__", size=(69,1), disabled=True,
                                     enable_events=True),
                            sg.FolderBrowse(button_text="Browse", key="__csv_frames_output_browse__",
                                            target="__csv_frames_output__")
                            ],
                           ]

    csv_writeout_progress = [[sg.Button("Start Frame Writing", key="__start_writeout__", size=(16,1),
                                        enable_events=True),
                              sg.Text(size=(70,1), key="__writeout_info__")
                              ],
                             [sg.ProgressBar(1, key="__writeout_progress__", size=(101,10))
                              ],
                             ]

    csv_to_frames_layout = [[sg.Frame("input", csv_writeout_input)],
                            [sg.Frame("output", csv_writeout_output)],
                            [sg.Frame("", csv_writeout_progress)]]

    # Monitoring Layout #####################################################################################
    cli_output_layout = [[sg.Output(size=(100,18))]]

    # tabs and tab group layout #############################################################################
    tabs = [[sg.Tab("Frame Selection", selection_layout, key="__frame_selection_tab__")],
            [sg.Tab("Frames & CSV to Images", csv_to_frames_layout, key="__csv_to_images_tab__")],
            [sg.Tab("CLI output", cli_output_layout, key="__cli_output_tab__")],
            ]

    tab_groups_layout = [[sg.TabGroup(tabs,key="__tab_group_container__",
                                      enable_events=True, tab_location="topleft")
                          ]]

    # construct GUI window ##################################################################################
    #########################################################################################################
    window = sg.Window("SFM Preprocessor", tab_groups_layout)
    try:
        # Window event loop
        while True:
            event, values = window.read(timeout = 100)

            # Periodic (timeout) events/GUI checking ########################################################
            if event == sg.TIMEOUT_KEY:

                # check for ongoing frame counting process and handle finishing it
                if "__count_frames__" in process_references.keys():
                    if process_results["__count_frames__"].ready():
                        # display frame count
                        result = process_results["__count_frames__"].get()
                        window["__count_frames_info__"]("COUNT: " + str(result))
                        # close process and delete references
                        terminate_coprocess(process_references["__count_frames__"])
                        del process_references["__count_frames__"], process_results["__count_frames__"]
                        # enable editing of start/end indexes
                        window["__start_index__"](disabled=False)
                        window["__end_index__"](disabled=False)
                        # reset button
                        window["__count_frames__"](text="Count Frames")
                        update_button_colors(window)
                        # update progress bar maximum based on count
                        window["__selection_progress__"].update_bar(0, max=result)
                        del result

                # check for ongoing frame selection process
                if "__frame_selection__" in process_references.keys():
                    if not process_results["__frame_selection__"].empty():
                        # get all results
                        res = []
                        while not process_results["__frame_selection__"].empty():
                            res.append(process_results["__frame_selection__"].get())

                        if res[-1] is None: # check if selection finished
                            # end slection co-process
                            terminate_coprocess(process_references["__frame_selection__"])
                            del process_references["__frame_selection__"]
                            del process_results["__frame_selection__"]
                            time_total = time.time() - process_infos["__frame_selection__"]["start time"]
                            # display finishing
                            maximum = int(window["__count_frames_info__"].Get().split()[1])
                            window["__selection_progress__"].update_bar(maximum)
                            window["__selection_info__"](f'DONE: Frame selection successful! Selected '
                                                         f'{process_infos["__frame_selection__"]["selected count"]}'
                                                         f' in {round(time_total)}s')
                            toggle_buttons_disabling_during_selection(window, False)
                            toggle_input_enable(window, disabled=False)
                            del maximum, time_total

                        else: # update the progress bar and estimates
                            window["__selection_progress__"].update_bar(res[-1])
                            process_infos["__frame_selection__"]["selected count"] += 1
                            elapsed = time.time() - process_infos["__frame_selection__"]["start time"]
                            eta = (elapsed / (res[-1])) * (int(window["__count_frames_info__"].Get().split()[1]) - res[-1])
                            window["__selection_info__"](f'PROC: {res[-1]} / '
                                                         f'{window["__count_frames_info__"].Get().split()[1]} '
                                                         f'frames analyzed | selected '
                                                         f'{process_infos["__frame_selection__"]["selected count"]} '
                                                         f' | estimated time left '
                                                         f'{round(eta)}s')
                            del elapsed, eta

                        # write results
                        if values["__output_type__"] == output_types[0]: # CSV type output
                            write_results_to_csv_file(values["__output_source__"], res)

                        del res # free up the variable name

                if "__frame_writeout__" in process_references.keys():
                    if not process_results["__frame_writeout__"].empty():
                        res = []
                        while not process_results["__frame_writeout__"].empty():
                            res.append(process_results["__frame_writeout__"].get())

                        if res[-1] is None: # writeout finished
                            # end co-process
                            terminate_coprocess(process_references["__frame_writeout__"])
                            del process_references["__frame_writeout__"]
                            del process_results["__frame_writeout__"]
                            # display finishing
                            text__ = (f"Successfully written {process_infos['__frame_writeout__']['frame count']}"
                                      f" frames to disk in "
                                      f"{round(time.time() - process_infos['__frame_writeout__']['start time'])} s")
                            window["__writeout_info__"](text__)
                            window["__writeout_progress__"].update_bar(process_infos["__frame_writeout__"]["frame count"])
                            del text__
                            window["__start_writeout__"](text = "Start Frame Writing")
                            toggle_buttons_disabling_during_writeout(window, False)
                            toggle_input_enable(window, False)

                        else: # writeout still running, merely update the progressbar and message
                            last_frame_idx = process_infos["__frame_writeout__"]["frames list"].index(res[-1])
                            window["__writeout_progress__"].update_bar(last_frame_idx)
                            text__ = (f"PROC: {last_frame_idx + 1}"
                                      f" / {process_infos['__frame_writeout__']['frame count']} "
                                      f"done. Last written frame: '{res[-1]}.png'")
                            window["__writeout_info__"](text__)
                            del text__, last_frame_idx

            if event in (None, "Exit"): # Event on exiting program ##########################################
                break

            # Button Type changes ###########################################################################
            elif event == "__input_type__": # Change the browse button to reflect selected type #############
                if values["__input_type__"] == input_types[0]:
                    window['__input_browse__'].BType = sg.BUTTON_TYPE_BROWSE_FILE
                    window['__input_browse__'].file_types = input_video_file_types
                    window['__input_error__']('ERROR: No file selected')

                elif values["__input_type__"] == input_types[1]:
                    window['__input_browse__'].BType = sg.BUTTON_TYPE_BROWSE_FOLDER
                    window['__input_browse__'].file_types = input_image_file_types
                    window['__input_error__']('ERROR: No folder selected')

                # terminate running process and reset button and message text
                if "__count_frames__" in process_references.keys():
                    terminate_coprocess(process_references["__count_frames__"])
                    del process_references["__count__frames__"], process_results["__count_frames"]

                window["__input_source__"]("")
                update_button_colors(window)
                reset_frame_count(window)

            elif event == "__output_type__": # Change the browse button to reflect selected type ############
                if values["__output_type__"] == output_types[0]:
                    window['__output_browse__'].BType = sg.BUTTON_TYPE_SAVEAS_FILE
                    window['__output_error__']('ERROR: No file selected')

                elif values["__output_type__"] == output_types[1]:
                    window['__output_browse__'].BType = sg.BUTTON_TYPE_BROWSE_FOLDER
                    window['__output_error__']('ERROR: No folder selected')

                window["__output_source__"]("")
                update_button_colors(window)


            # Frame Selection Layout Events #################################################################
            elif event == "__input_source__": # Input path events ###########################################
                error_message = ""

                # input as a video file
                if values["__input_type__"] == input_types[0]:
                    if not os.path.isfile(values["__input_source__"]):
                        error_message = "ERROR: Input file path does not exist"

                    elif any([values["__input_source__"].endswith(ftype[1:]) for
                              _, ftype in input_video_file_types]):
                        error_message = "OK"

                    else:
                        error_message = "ERROR: Video File type is unsupported"

                # input as image files (sequence)
                elif values["__input_type__"] == input_types[1]:
                    if not os.path.isdir(values["__input_source__"]):
                        error_message = "ERROR: Input folder path does not exist"

                    elif not os.listdir(values["__input_source__"]):
                        error_message = "ERROR: Input folder is empty"

                    else:
                        # check all files in folder if they are a filetype that is supported
                        files_supported_in_path = []
                        for fname in os.listdir(values["__input_source__"]):
                            checked_types = [fname.endswith(ftype[1:]) for _, ftype in input_image_file_types]
                            files_supported_in_path.append(True if any(checked_types) else False)

                        if not any(files_supported_in_path):
                            # folder contains no files types that are supported
                            error_message = (f"ERROR: Input folder does not "
                                             f"contain any files with supported types")

                        elif all(files_supported_in_path):
                            # folder contains only files that are supported
                            error_message = "OK"

                        else:
                            # folder contains some files that aren't supported
                            error_message = (f"WARN: Input folder contains "
                                             f"{files_supported_in_path.count(False)} "
                                             f"files with unsupported types.")

                window["__input_error__"](error_message)
                update_button_colors(window)
                reset_frame_count(window)
                if "__count_frames__" in process_references.keys():
                    terminate_coprocess(process_references["__count_frames__"])
                    del process_references["__count_frames__"], process_results["__count_frames__"]


            elif event == "__output_source__": # Output path events ########################################
                error_message = ""

                # output as a CSV file, listing selected frame numbers
                if values["__output_type__"] == output_types[0]:
                    if os.path.isfile(values["__output_source__"]):
                        error_message = "ERROR: Output file allready exists"

                    elif values["__output_source__"] == "":
                        error_message = "ERROR: No file selected"

                    elif not values["__output_source__"].endswith(".csv"):
                        error_message = "ERROR: Output file is not CSV type for some reason"

                    else:
                        error_message = "OK"

                # output as a sequence of image files
                elif values["__output_type__"] == output_types[1]:

                    if not os.path.isdir(values["__output_source__"]):
                        error_message = "ERROR: Output folder path does not exist"

                    elif os.listdir(values["__output_source__"]):
                        error_message = "ERROR: Output folder is not empty"

                    else:
                        error_message = "OK"

                window["__output_error__"](error_message)
                update_button_colors(window)


            elif event == "__worker_processes__": # Worker process count changed events (int only) ########
                sanitized_input = integer_input_sanitizer(values["__worker_processes__"], 1, 512)
                if sanitized_input != values["__worker_processes__"]:
                    window["__worker_processes__"](sanitized_input)

                error_message = ""
                # warn user if they are overzelous with the worker process count
                # TODO: Change if threads are a thing and OPENCV is used
                if int(sanitized_input) > 6:
                    error_message = "WARN: Ensure you have enough RAM and/or CPU cores"

                window["__worker_processes_warning__"](error_message)


            elif event == "__max_distance__": # max disntance (int) changed ###############################
                sanitized_input = integer_input_sanitizer(values["__max_distance__"], 1, 9999)
                if sanitized_input != values["__max_distance__"]:
                    window["__max_distance__"](sanitized_input)

                error_message = ""
                if int(sanitized_input) > 150:
                    error_message = "WARN: Increasing this increases processing time"

                elif int(sanitized_input) < 75:
                    error_message = "WARN: Reducing this can give worse results"

                window["__max_distance_warning__"](error_message)


            elif event == "__buffer_size__": # Buffer Size changed (int) ###################################
                sanitized_input = integer_input_sanitizer(values["__buffer_size__"], 10,
                                                          int(values["__max_distance__"]))
                if sanitized_input != values["__buffer_size__"]:
                    window["__buffer_size__"](sanitized_input)

                error_message = ""
                if sanitized_input == values["__max_distance__"]:
                    error_message = "INFO: Cannot go above Max Distance"

                elif int(sanitized_input) > 100:
                    error_message = "WARN: Increasing this increases RAM usage"

                elif int(sanitized_input) < 25:
                    error_message = "WARN: Reducing this increases file accessing frequency"

                window["__chunk_size_warning__"](error_message)


            elif event == "__start_index__": # start selection from index ################################
                _tmp = window["__count_frames_info__"].Get()
                sanitized_input = integer_input_sanitizer(values["__start_index__"], 0,
                                                          99999999999 if not _tmp.startswith("COUNT") else
                                                          int(_tmp.split(" ")[1]))
                if sanitized_input != values["__start_index__"]:
                    window["__start_index__"](sanitized_input)

                error_message = ""
                if sanitized_input == "0":
                    error_message = "INFO: Will start at the first frame"

                elif _tmp.startswith("COUNT"):
                    error_message = ""

                else:
                    error_message = "WARN: Ensure the video file is long enough"

                window["__start_index_warning__"](error_message)


            elif event == "__end_index__": # end selection to index ######################################
                sanitized_input = integer_input_sanitizer(values["__end_index__"],
                                                          int(values["__start_index__"]), 99999999)
                if sanitized_input != values["__end_index__"]:
                    window["__end_index__"](sanitized_input)

                error_message = ""
                if sanitized_input == "0":
                    error_message = "INFO: Will stop at the last frame"

                else:
                    error_message = "WARN: Ensure the video file is long enough"

                window["__end_index_warning__"](error_message)


            elif event == "__max_features__": ###########################################################
                sanitized_input = integer_input_sanitizer(values["__max_features__"], 50, 9999)
                if sanitized_input != values["__max_features__"]:
                    window["__max_features__"](sanitized_input)

                error_message = ""
                if int(sanitized_input) < 700:
                    error_message = "WARN: Lowering this value increases performance at the cost of accuracy"

                elif int(sanitized_input) > 1500:
                    error_message = (f"WARN: Increasing this value reduces "
                                     f"performance, gaining little accuracy")

                window["__max_features_warning__"](error_message)


            elif event == "__similarity_percentile__": ##################################################
                sanitized_input = float_input_sanitizer(values["__similarity_percentile__"],
                                                        0.05, 0.80, 4)

                if sanitized_input != values["__similarity_percentile__"]:
                    window["__similarity_percentile__"](sanitized_input)

                error_message = ""
                if float(sanitized_input) < 0.2: # use the tens digit as that is always there
                    error_message = "WARN: Lowering this value reduces the number of frames to pick from"

                elif float(sanitized_input) > 0.3:
                    error_message = "WARN: Increasing this value increases the number of frames to pick from"

                window["__similarity_percentile_warning__"](error_message)


            elif event == "__sharpness_percentile__": ####################################################
                sanitized_input = float_input_sanitizer(values["__sharpness_percentile__"],
                                                        0.05, 0.80, 4)

                if sanitized_input != values["__sharpness_percentile__"]:
                    window["__sharpness_percentile__"](sanitized_input)

                error_message = ""
                if float(sanitized_input) < 0.2:
                    error_message = "WARN: Lowering this will reduce the amount of frames to select from"

                elif float(sanitized_input) > 0.3:
                    error_message = "WARN: Increasing this may reduce the sharpness of selected image"

                window["__sharpness_percentile_warning__"](error_message)

            # frame selection button events ##############################################################
            ##############################################################################################
            elif event == "__count_frames__":

                # if is running, cancelling it
                if window["__count_frames__"].get_text() == "Cancel":
                    window["__count_frames_info__"]("ERROR: Cancelled counting frames")
                    window["__count_frames__"](text="Count Frames")
                    update_button_colors(window)
                    terminate_coprocess(process_references["__count_frames__"])
                    del process_references["__count_frames__"], process_results["__count_frames__"]

                # start running it
                else:
                    reset_frame_count(window)
                    if window["__input_error__"].Get().startswith("ERROR"):
                        window["__count_frames_info__"]("ERROR: No input source selected")
                    else:
                        window["__count_frames_info__"](f"PROC: Counting frames... "
                                                        f"see CLI output tab for information")
                        pool = mp.Pool(1)
                        ret = pool.apply_async(count_frames, args=(values["__input_source__"],))
                        process_references["__count_frames__"] = pool
                        process_results["__count_frames__"] = ret
                        del pool, ret
                        window["__count_frames__"](text="Cancel", button_color=button_colors["enabled"])


            elif event == "__start_selection__": ########################################################

                if window["__start_selection__"].get_text() == "Cancel": # cancel running selection.. duh
                    # change GUI
                    toggle_buttons_disabling_during_selection(window, False)
                    toggle_input_enable(window, disabled=False)
                    window["__start_selection__"](text = "Start Selection")
                    window["__selection_info__"]("INFO: Selection cancelled before it completed")
                    update_button_colors(window)
                    # close subprocesses
                    terminate_coprocess(process_references["__frame_selection__"])
                    del process_references["__frame_selection__"], process_results["__frame_selection__"]

                else:
                    # check input/output validity
                    if (window["__input_error__"].Get().startswith("ERROR") or
                        window["__output_error__"].Get().startswith("ERROR")):

                        window["__selection_info__"]("ERROR: input or output is invalid")
                    # check for running frame count subprocess
                    elif window["__count_frames_info__"].Get().startswith("PROC"):
                        window["__selection_info__"]("ERROR: Wait for the frame counting to finish")
                    # require frame count, only because progressbar and estimates
                    elif not window["__count_frames_info__"].Get().startswith("COUNT"):
                        window["__selection_info__"]("ERROR: Counting frames required due to bad coding")
                    # start selection subprocess
                    else:
                        # update button statuses
                        toggle_buttons_disabling_during_selection(window, True)
                        toggle_input_enable(window, disabled=True)
                        window["__start_selection__"](text = "Cancel")
                        window["__selection_info__"]("PROC: Started selection... see CLI tab for more info")
                        update_button_colors(window)
                        # begin subprocess
                        process_results["__frame_selection__"] = mp.Queue()
                        process_references["__frame_selection__"] = mp.Process(target=select_frames,
                                                                               args=(values,
                                                                                     process_results["__frame_selection__"]))
                        process_references["__frame_selection__"].start()
                        process_infos["__frame_selection__"] = {"start time" : time.time(),
                                                                "last done time" : time.time()}
                        process_infos["__frame_selection__"]["selected count"] = 0


            # Frame writeout events #########################################################################
            #################################################################################################

            elif event in "__csv_input__":
                error_message = ""

                if not os.path.isfile(values["__csv_input__"]):
                    error_message = "ERROR: File does not exist."

                # check if CSV format is correct
                else:
                    filetext = ""
                    with open(values["__csv_input__"], 'r') as f:
                        filetext = f.read()
                    validchars = [(c in "0123456789;") for c in filetext.strip('\n')]
                    if not all(validchars):
                        error_message = "ERROR: file contains invalid characters, only numbers and ';' allowed"
                    else:
                        error_message = "OK"

                window["__csv_input_warning__"](error_message)

            elif event == "__csv_frames_input__": ##############################################################
                error_message = ""

                if not os.path.isfile(values["__csv_frames_input__"]):
                    error_message = "ERROR: File does not exist."
                else:
                    error_message = "OK"

                window["__csv_frames_input_warning__"](error_message)

            elif event == "__csv_frames_output__": #############################################################
                error_message = ""

                if not os.path.isdir(values["__csv_frames_output__"]):
                    error_message = "ERROR: Folder does not exist."
                elif len(os.listdir(values["__csv_frames_output__"])) != 0:
                    error_message = "WARN: Folder is not empty, will not override files with the same name."
                else:
                    error_message = "OK"

                window["__csv_frames_output_warning__"](error_message)

            elif event == "__start_writeout__":

                if window["__start_writeout__"].GetText() == "Cancel":
                    window["__start_writeout__"](text = "Start Frame Writing")
                    window["__writeout_info__"]("Writeout has been cancelled before it was finished.")
                    terminate_coprocess(process_references["__frame_writeout__"])
                    del process_references["__frame_writeout__"], process_results["__frame_writeout__"]
                    toggle_buttons_disabling_during_writeout(window, False)
                    toggle_input_enable(window, False)

                elif (window["__csv_input_warning__"].Get().startswith("ERROR") or
                      window["__csv_frames_output_warning__"].Get().startswith("ERROR")):
                    window["__writeout_info__"]("ERROR: input or output is invalid")

                else: # start writeout
                    process_results["__frame_writeout__"] = mp.Queue()
                    process_references["__frame_writeout__"] = mp.Process(target=csv_video_writeout,
                                                                          args=(values,
                                                                                process_results["__frame_writeout__"]))
                    window["__start_writeout__"](text = "Cancel")
                    frames_list = read_results_from_csv_file(values["__csv_input__"])
                    window["__writeout_progress__"].update_bar(0, max=len(frames_list))
                    window["__writeout_info__"]("PROC: Writeout started.. see CLI tab for info.")
                    process_references["__frame_writeout__"].start()
                    process_infos["__frame_writeout__"] = {"start time": time.time(),
                                                           "frame count" : len(frames_list),
                                                           "frames list" : frames_list,
                                                           "last done time": time.time()}
                    toggle_buttons_disabling_during_writeout(window, True)
                    toggle_input_enable(window, True)
                    del frames_list


    finally: # always close window if crashing or exited
        window.close()
        # close and de-reference all subprocesses
        for key in process_references.keys():
            process_references[key].terminate()
            process_references[key].join()
            process_references[key].close()
        del process_references, process_results