# -*- coding: utf-8 -*-

import selection_module
import time
import multiprocessing as mp

# import io_module, analysis_module

# reader = io_module.read_video("/home/reevi/tmp/vid/1.mp4", as_gray=True)
# img1 = next(reader)
# for i, img in enumerate(reader):
#     analysis_module.match_images(img1, img)
#     img1 = img
#     print(i)

# selection_module.video_selection("/home/reevi/tmp/vid/1.mp4", # positional args
                                     # n_workers=10, buffer_size=100) # key word arguments


def tqr(queue):
    s = selection_module.video_selection("/home/reevi/tmp/vid/1.mp4", # positional args
                                     n_workers=10, buffer_size=100, as_generator = True) # key word arguments
    for i in s:
        queue.put(i)
    queue.put(None)

if __name__ == "__main__":
    # que = mp.SimpleQueue()'
    # p = mp.Process(target=tqr, args=("#1", que))
    # print(p)
    # print(p.is_alive())
    # p.start()

    # while True:
    #     time.sleep(1)
    #     if not p.is_alive():
    #         print(que.get())
    #         p.terminate()
    #         del que, p
    #         break
    #     else:
    #         print("still waiting")'

    que = mp.Queue()
    p = mp.Process(target=tqr, args=(que,))
    print("maybe works?")
    refs = {"process" : p, "queue" : que}
    p.start()

    while True:
        if refs["queue"].empty():
            print("waiting")
        else:
            res = refs["queue"].get()
            if res is None:
                break
            else:
                print(res)
        time.sleep(1)