# -*- coding: utf-8 -*-

import os

import PySimpleGUI as sg


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


if __name__ == "__main__":

    # Create Selction GUI layouts and elements #################################################################
    input_types = ("Video File", "Sequential Images")
    input_video_file_types = (("Mpeg 4", "*.mp4"),)
    input_image_file_types = (("JPEG", "*.jpg"), ("PNG", "*.png"), ("BPM", "*.bmp"))

    input_layout = [[sg.Text("ERROR: No file selected", key="__input_error__", size=(100,1))
                     ],
                    [sg.Combo(input_types, key="__input_type__", size=(20,1),
                              readonly=True, default_value="Video File", enable_events=True),
                     sg.Input(key="__input_source__", enable_events=True, disabled=True, size=(64,1)),
                     sg.FileBrowse(button_text="Browse", key="__input_browse__",
                                   target="__input_source__", file_types=input_video_file_types)
                     ]
                    ]

    output_types = ("CSV File", "Image Files")
    output_file_types = (("CSV File", "*.csv"),)

    output_layout = [[sg.Text("ERROR: No file selected", key="__output_error__", size=(100,1))
                      ],
                     [sg.Combo(output_types, key="__output_type__", size=(20,1),
                               readonly=True, default_value=output_types[0], enable_events=True),
                      sg.Input(key="__output_source__", enable_events=True, disabled=True, size=(64,1)),
                      sg.SaveAs(button_text="Browse", key="__output_browse__",
                                target="__output_source__", file_types=output_file_types)
                      ]
                     ]

    options_layout = [[sg.Text("Worker Processes", size=(21,1)),
                       sg.Input(key="__worker_processes__", size=(4,1),
                                default_text="1", enable_events=True),
                       sg.Text("", key="__worker_processes_warning__", size=(71,1))
                       ]
                      ]

    advanced_options_layout = [[sg.Text("Max Distance (frames)", size=(21,1)),
                                sg.Input(key="__max_distance__", size=(4,1),
                                         default_text="100", enable_events=True),
                                sg.Text("", key="__max_distance_warning__", size=(71,1))
                                ],
                               [sg.Text("Chunk Size", size=(21,1)),
                                sg.Input(key="__chunk_size__", size=(4,1),
                                         default_text="25", enable_events=True),
                                sg.Text("", key="__chunk_size_warning__", size=(71,1))
                                ],
                               [sg.Text("Start Index", size=(21,1)),
                                sg.Input(key="__start_index__", size=(8,1),
                                         default_text="0", enable_events=True),
                                sg.Text("", key="__start_index_warning__", size=(67,1))
                                ],
                               [sg.Text("End Index", size=(21,1)),
                                sg.Input(key="__end_index__", size=(8,1),
                                         default_text="0", enable_events=True),
                                sg.Text("", key="__end_index_warning__", size=(67,1))
                                ],
                               [sg.Text("Max Features", size=(21,1)),
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

    start_cancel_layout = [[sg.Button("Start Selection", key="__start_selection__",
                                      button_color=("black","red"), pad=((0,0),(40,0))),
                            sg.Button("Cancel", key="__cancel_selection__",
                                      button_color=("black","gray"), pad=((440,0),(40,0)))
                            ]
                           ]

    selection_layout = [[sg.Frame("Input Data", input_layout)],
                        [sg.Frame("Output Data", output_layout)],
                        [sg.Frame("Options", options_layout)],
                        [sg.Frame("Advanced Options", advanced_options_layout)],
                        [sg.Frame("", start_cancel_layout)]
                        ]

    # CSV Frames Writeout ###################################################################################
    csv_writeout_input = [
                          # CSV file input
                          [sg.Text("ERROR: No CSV File selected", key="__csv_input_warning__", size=(100,1))],

                          [sg.Text("CSV File", size=(10,1)),
                           sg.Input(key="__csv_input__", size=(74,1), disabled=True),
                           sg.FileBrowse(button_text="Browse", key="__csv_browse__",
                                         target="__csv_input__", file_types=output_file_types)
                           ],
                          # Frames input
                          [sg.Text("ERROR: No Video File selected", key="__csv_frames_input_warning__",
                                   size=(100,1))
                           ],
                          [sg.Combo(values=input_types, default_value=input_types[0], size=(20,1),
                                    readonly=True, enable_events=True),
                           sg.Input(key="__csv_frames_input__", size=(62,1), disabled=True),
                           sg.FileBrowse(button_text="Browse", key="__csv_frames_input_browse__",
                                         target="__csv_frames_input__", file_types=input_video_file_types)
                           ]
                          ]

    csv_writeout_output = [[sg.Text("ERROR: No Folder selected", key="__csv_frames_output_warning__",
                                   size=(100,1))
                            ],
                           [sg.Text("Output Folder", size=(15,1)),
                            sg.Input(key="__csv_frames_output__", size=(69,1), disabled=True),
                            sg.FileBrowse(button_text="Browse", key="__csv_frames_output_browse__",
                                          target="__csv_frames_output__", file_types=input_video_file_types)
                            ]
                           ]

    csv_to_frames_layout = [[sg.Frame("input", csv_writeout_input)],
                            [sg.Frame("output", csv_writeout_output)]]

    # Monitoring Layout #####################################################################################
    monitoring_layout = [[sg.Output(size=(100,18))]]

    # tabs and tab group layout #############################################################################
    tabs = [[sg.Tab("Frame Selection", selection_layout, key="__frame_selection_tab__")],
            [sg.Tab("Frames & CSV to Images", csv_to_frames_layout, key="__csv_to_images_tab__")],
            [sg.Tab("Monitoring CLI output", monitoring_layout, key="__monitoring_tab__")],
            ]

    tab_groups_layout = [[sg.TabGroup(tabs,key="__tab_group_container__",
                                      enable_events=True, tab_location="topleft")
                          ]]

    # construct GUI window ##################################################################################
    ########################################################################################################
    window = sg.Window("SFM Preprocessor", tab_groups_layout)
    try:
        # Window event loop
        while True:
            event, values = window.read()

            if event in (None, "Exit"): # Event on exiting program
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

                window["__input_source__"]("")

            elif event == "__output_type__": # Change the browse button to reflect selected type ############
                if values["__output_type__"] == output_types[0]:
                    window['__output_browse__'].BType = sg.BUTTON_TYPE_SAVEAS_FILE
                    window['__output_error__']('ERROR: No file selected')

                elif values["__output_type__"] == output_types[1]:
                    window['__output_browse__'].BType = sg.BUTTON_TYPE_BROWSE_FOLDER
                    window['__output_error__']('ERROR: No folder selected')
                window["__output_source__"]("")


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


            elif event == "__output_source__": # Output path events #######################################
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


            elif event == "__chunk_size__": # chunk size changed (int) ###################################
                sanitized_input = integer_input_sanitizer(values["__chunk_size__"], 10,
                                                          int(values["__max_distance__"]))
                if sanitized_input != values["__chunk_size__"]:
                    window["__chunk_size__"](sanitized_input)

                error_message = ""
                if sanitized_input == values["__max_distance__"]:
                    error_message = "INFO: Cannot go above Max Distance"

                elif int(sanitized_input) > 100:
                    error_message = "WARN: Increasing this increases RAM usage"

                elif int(sanitized_input) < 25:
                    error_message = "WARN: Reducing this increases file accessing"

                window["__chunk_size_warning__"](error_message)


            elif event == "__start_index__": # start selection from index ################################
                sanitized_input = integer_input_sanitizer(values["__start_index__"], 0, 99999999)
                if sanitized_input != values["__start_index__"]:
                    window["__start_index__"](sanitized_input)

                error_message = ""
                if sanitized_input == "0":
                    error_message = "INFO: Will start at the first frame"

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


    finally: # always close window if crashing or exited
        window.close()