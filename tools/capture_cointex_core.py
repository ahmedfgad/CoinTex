"""Read the Kivy GL framebuffer into a top-row-first (H, W, 3) uint8 RGB array.

Proven path on this machine (Kivy/SDL2 + Mesa, Linux): glReadPixels with
GL_RGB / GL_UNSIGNED_BYTE returns w*h*3 bytes; OpenGL's origin is bottom-left,
so flip to image convention.
"""

import numpy as np
from kivy.graphics.opengl import glReadPixels, GL_RGB, GL_UNSIGNED_BYTE


def grab_frame(window):
    w, h = window.size
    data = glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE)
    arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)
    return np.flipud(arr).copy()
